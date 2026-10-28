import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from well_ops.ingestion.manifest import write_manifest
from well_ops.ingestion.volve_files import (
    LICENCE,
    SOURCE,
    VOLUME,
    CliError,
    RemoteFile,
    Target,
    copy_all,
    copy_file,
    list_target,
    manifest_entries,
)


def _file(name: str, size: int) -> dict[str, Any]:
    return {"name": name, "is_directory": False, "size": size}


def _dir(name: str) -> dict[str, Any]:
    return {"name": name, "is_directory": True, "size": 0}


class FakeCli:
    """Answers `fs ls` from a dict of listings and `fs cp` by writing `size` bytes."""

    def __init__(self, listings: dict[str, list[dict[str, Any]]], fail_cp: int = 0) -> None:
        self.listings = listings
        self.fail_cp = fail_cp
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        self.calls.append(list(args))
        if args[:2] == ["fs", "ls"]:
            return json.dumps(self.listings[args[2]])
        if args[:2] == ["fs", "cp"]:
            if self.fail_cp > 0:
                self.fail_cp -= 1
                raise CliError("network error")
            source, dest = args[-2], args[-1]
            parent, _, name = source.rpartition("/")
            size = next(e["size"] for e in self.listings[parent] if e["name"] == name)
            Path(dest).write_bytes(b"x" * size)
            return ""
        raise AssertionError(args)


DDR = "Well_technical_data/Daily Drilling Report - XML Version"
LISTINGS = {
    f"{VOLUME}/{DDR}": [_file("a b.xml", 3), _dir("sub dir")],
    f"{VOLUME}/{DDR}/sub dir": [_file("c.xml", 5)],
    f"{VOLUME}/Production_data": [_file("Volve production data.xlsx", 7), _file("other", 1)],
}


def test_list_target_recurses_and_keeps_spaces() -> None:
    cli = FakeCli(LISTINGS)

    files = list_target(Target(f"{DDR}/"), run=cli, workers=2)

    assert files == [RemoteFile(f"{DDR}/a b.xml", 3), RemoteFile(f"{DDR}/sub dir/c.xml", 5)]
    assert ["fs", "ls", f"{VOLUME}/{DDR}/sub dir", "-o", "json"] in cli.calls


def test_list_target_single_file_lists_parent() -> None:
    files = list_target(Target("Production_data/Volve production data.xlsx"), run=FakeCli(LISTINGS))

    assert files == [RemoteFile("Production_data/Volve production data.xlsx", 7)]


def test_list_target_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        list_target(Target("Production_data/missing.xlsx"), run=FakeCli(LISTINGS))


def test_copy_file_skips_present_file_with_same_size(tmp_path: Path) -> None:
    remote = RemoteFile(f"{DDR}/a b.xml", 3)
    cli = FakeCli(LISTINGS)

    assert copy_file(remote, tmp_path, run=cli) is True
    assert copy_file(remote, tmp_path, run=cli) is False
    assert (tmp_path / DDR / "a b.xml").stat().st_size == 3
    assert sum(c[:2] == ["fs", "cp"] for c in cli.calls) == 1


def test_copy_file_retries_then_succeeds(tmp_path: Path) -> None:
    sleeps: list[float] = []

    copied = copy_file(
        RemoteFile(f"{DDR}/a b.xml", 3), tmp_path, FakeCli(LISTINGS, fail_cp=3), 3, sleeps.append
    )

    assert copied is True
    assert sleeps == [2.0, 4.0, 8.0]


def test_copy_all_reports_failure_after_retries(tmp_path: Path) -> None:
    files = [RemoteFile(f"{DDR}/a b.xml", 3)]

    result = copy_all(files, tmp_path, FakeCli(LISTINGS, fail_cp=4), 1, lambda _: None)

    assert result.expected == 1
    assert result.copied == []
    assert len(result.failures) == 1
    assert not (tmp_path / DDR / "a b.xml").exists()
    assert not (tmp_path / DDR / "a b.xml.part").exists()


def test_manifest_entries_cover_present_files_and_reuse_previous(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw" / "volve"
    files = [RemoteFile(f"{DDR}/a b.xml", 3), RemoteFile(f"{DDR}/sub dir/c.xml", 5)]
    copy_file(files[0], raw_dir, run=FakeCli(LISTINGS))
    manifest_path = tmp_path / "manifest.json"

    first = manifest_entries(files, raw_dir, tmp_path, manifest_path)

    assert [e.file for e in first] == [f"raw/volve/{DDR}/a b.xml"]
    assert first[0].source == SOURCE
    assert first[0].licence == LICENCE
    assert first[0].source_url == f"{VOLUME}/{DDR}/a b.xml"
    assert first[0].retrieved_at.endswith("Z")

    write_manifest(manifest_path, first)
    assert manifest_entries(files, raw_dir, tmp_path, manifest_path) == first
