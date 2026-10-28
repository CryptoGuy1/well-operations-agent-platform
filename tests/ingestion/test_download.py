from pathlib import Path

import pytest

from well_ops.ingestion._download import fetch


def _reject(path: Path) -> None:
    raise ValueError("bad file")


def test_fetch_replaces_file_when_valid(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("new", encoding="utf-8")
    dest = tmp_path / "out" / "a.csv"

    fetch(source.as_uri(), dest, lambda _: None)

    assert dest.read_text(encoding="utf-8") == "new"


def test_fetch_keeps_previous_copy_when_validation_fails(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("new", encoding="utf-8")
    dest = tmp_path / "a.csv"
    dest.write_text("old", encoding="utf-8")

    with pytest.raises(ValueError, match="bad file"):
        fetch(source.as_uri(), dest, _reject)

    assert dest.read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "a.csv.part").exists()


def test_fetch_keeps_previous_copy_when_download_fails(tmp_path: Path) -> None:
    dest = tmp_path / "a.csv"
    dest.write_text("old", encoding="utf-8")

    with pytest.raises(OSError):
        fetch((tmp_path / "missing.csv").as_uri(), dest, lambda _: None)

    assert dest.read_text(encoding="utf-8") == "old"
