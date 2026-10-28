"""Manifest of downloaded raw files: source, size, checksum, retrieval time and licence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class ManifestEntry:
    file: str
    source: str
    source_url: str
    bytes: int
    sha256: str
    retrieved_at: str
    licence: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_entry(
    path: Path, data_dir: Path, source: str, source_url: str, licence: str, retrieved_at: str
) -> ManifestEntry:
    return ManifestEntry(
        file=path.relative_to(data_dir).as_posix(),
        source=source,
        source_url=source_url,
        bytes=path.stat().st_size,
        sha256=sha256_file(path),
        retrieved_at=retrieved_at,
        licence=licence,
    )


def load_manifest(path: Path) -> list[ManifestEntry]:
    if not path.exists():
        return []
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return [ManifestEntry(**{"source": "", **item}) for item in raw["files"]]


def write_manifest(path: Path, entries: list[ManifestEntry]) -> list[ManifestEntry]:
    """Merge entries into the manifest at path, replacing any entry for the same file.

    Entries for files not in this run (for example a failed download whose previous copy was
    kept) are preserved unchanged. Returns the merged entries, sorted by file.
    """
    merged = {entry.file: entry for entry in load_manifest(path)}
    merged.update({entry.file: entry for entry in entries})
    ordered = [merged[name] for name in sorted(merged)]
    payload = {"files": [asdict(entry) for entry in ordered]}
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return ordered
