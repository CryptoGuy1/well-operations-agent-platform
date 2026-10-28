import hashlib
import json
from pathlib import Path

from well_ops.ingestion.manifest import ManifestEntry, build_entry, load_manifest, write_manifest


def _entry(file: str, sha256: str = "0" * 64) -> ManifestEntry:
    return ManifestEntry(
        file=file,
        source="Test source",
        source_url=f"https://example.org/{file}",
        bytes=1,
        sha256=sha256,
        retrieved_at="2026-01-01T00:00:00Z",
        licence="CC BY 4.0",
    )


def test_build_entry_records_size_hash_and_relative_path(tmp_path: Path) -> None:
    path = tmp_path / "raw" / "cira" / "a.csv"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x,y\n1,2\n")

    entry = build_entry(
        path, tmp_path, "Test", "https://example.org/a", "CC BY 4.0", "2026-01-01T00:00:00Z"
    )

    assert entry.file == "raw/cira/a.csv"
    assert entry.bytes == 8
    assert entry.sha256 == hashlib.sha256(b"x,y\n1,2\n").hexdigest()


def test_write_manifest_round_trips_sorted(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"

    write_manifest(path, [_entry("raw/sodir/b.csv"), _entry("raw/cira/a.csv")])

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert [item["file"] for item in raw["files"]] == ["raw/cira/a.csv", "raw/sodir/b.csv"]
    assert set(raw["files"][0]) == {
        "file",
        "source",
        "source_url",
        "bytes",
        "sha256",
        "retrieved_at",
        "licence",
    }
    assert load_manifest(path) == [_entry("raw/cira/a.csv"), _entry("raw/sodir/b.csv")]


def test_write_manifest_keeps_entries_not_in_this_run(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(path, [_entry("raw/cira/a.csv"), _entry("raw/sodir/b.csv")])

    merged = write_manifest(path, [_entry("raw/cira/a.csv", sha256="1" * 64)])

    assert merged == [_entry("raw/cira/a.csv", sha256="1" * 64), _entry("raw/sodir/b.csv")]
    assert not (tmp_path / "manifest.json.part").exists()


def test_load_manifest_accepts_entries_without_source(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    old = {k: v for k, v in _entry("raw/cira/a.csv").__dict__.items() if k != "source"}
    path.write_text(json.dumps({"files": [old]}), encoding="utf-8")

    assert load_manifest(path)[0].source == ""
