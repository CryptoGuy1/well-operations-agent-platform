"""Atomic HTTP download shared by the ingestion modules."""

from __future__ import annotations

import shutil
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from well_ops.ingestion.manifest import ManifestEntry

USER_AGENT = "well-ops-ingestion/0.0"
TIMEOUT_S = 120


@dataclass
class DownloadResult:
    entries: list[ManifestEntry] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def read_url(url: str) -> bytes:
    with urllib.request.urlopen(_request(url), timeout=TIMEOUT_S) as response:
        body: bytes = response.read()
    return body


def fetch(url: str, dest: Path, validate: Callable[[Path], None]) -> None:
    """Download url to dest. The previous copy of dest is kept unless the new file validates."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with (
            urllib.request.urlopen(_request(url), timeout=TIMEOUT_S) as response,
            tmp.open("wb") as out,
        ):
            shutil.copyfileobj(response, out)
        validate(tmp)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
