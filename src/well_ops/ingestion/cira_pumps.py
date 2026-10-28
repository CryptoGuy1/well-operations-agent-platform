"""CIRA Centrifugal Pump Dataset: download from Zenodo and verify the published MD5 checksums."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from well_ops.ingestion._download import DownloadResult, fetch, read_url
from well_ops.ingestion.manifest import build_entry, utc_now

RECORD_ID = "18479728"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
LICENCE = "CC BY 4.0"
EXPECTED_CSV_COUNT = 8
README_NAME = "README.md"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RemoteFile:
    name: str
    url: str
    md5: str
    size: int


class ChecksumError(ValueError):
    pass


def parse_record(record: dict[str, Any]) -> list[RemoteFile]:
    """Extract the file list from a Zenodo record and check it has the expected shape."""
    files = []
    for item in record["files"]:
        algorithm, _, digest = item["checksum"].partition(":")
        if algorithm != "md5":
            raise ValueError(f"{item['key']}: unsupported checksum algorithm {algorithm!r}")
        files.append(
            RemoteFile(name=item["key"], url=item["links"]["self"], md5=digest, size=item["size"])
        )
    names = {f.name for f in files}
    csv_count = sum(name.endswith(".csv") for name in names)
    if README_NAME not in names or csv_count != EXPECTED_CSV_COUNT:
        raise ValueError(
            f"Zenodo record {RECORD_ID} changed: expected {EXPECTED_CSV_COUNT} CSV files and "
            f"{README_NAME}, found {sorted(names)}"
        )
    return sorted(files, key=lambda f: f.name)


def verify_md5(path: Path, expected: str) -> None:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ChecksumError(f"{path.name}: MD5 {digest.hexdigest()} != expected {expected}")


def download(data_dir: Path) -> DownloadResult:
    raw_dir = data_dir / "raw" / "cira"
    result = DownloadResult()
    record = json.loads(read_url(API_URL))
    for remote in parse_record(record):
        dest = raw_dir / remote.name
        try:
            fetch(remote.url, dest, partial(verify_md5, expected=remote.md5))
        except Exception as exc:
            log.error("CIRA %s failed, previous copy kept: %s", remote.name, exc)
            result.failures.append(f"cira/{remote.name}: {exc}")
            continue
        result.entries.append(build_entry(dest, data_dir, remote.url, LICENCE, utc_now()))
        log.info("CIRA %s ok (MD5 verified)", remote.name)
    return result
