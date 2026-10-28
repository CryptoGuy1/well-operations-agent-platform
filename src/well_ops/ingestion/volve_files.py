"""Volve Data Village files: list and copy them from a Databricks volume through the CLI."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from well_ops.ingestion.manifest import ManifestEntry, build_entry, load_manifest

VOLUME = "dbfs:/Volumes/equinor_asa_volve_data_village/public/volve"
SOURCE = "Equinor Volve Data Village"
LICENCE = "Equinor Open Data Licence"
RETRIES = 3

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Target:
    """A path relative to VOLUME. A trailing slash marks a directory, listed recursively."""

    path: str
    expected_files: int | None = None

    @property
    def is_directory(self) -> bool:
        return self.path.endswith("/")


TARGETS: tuple[Target, ...] = (
    Target("HRS and Terms and conditions for license to data - Volve.pdf", 1),
    Target("Well_technical_data/Daily Drilling Report - XML Version/", 1759),
    Target("WITSML Realtime drilling data/", 11894),  # approximate
    Target("Production_data/Volve production data.xlsx", 1),
    Target("Geophysical_Interpretations/Wells/Well_picks_Volve_v1.dat", 1),
    Target("Geophysical_Interpretations/Wells/Well_perforations_Volve.dat", 1),
    Target("Well_technical_data/EDM.XML/Volve F.edm.xml", 1),
)


@dataclass(frozen=True)
class RemoteFile:
    path: str  # relative to VOLUME, "/"-separated
    size: int


@dataclass(frozen=True)
class TargetSummary:
    target: Target
    files: int
    bytes: int


class CliError(RuntimeError):
    pass


Runner = Callable[[Sequence[str]], str]


def run_cli(args: Sequence[str]) -> str:
    """Run the Databricks CLI with an argument list (no shell, so spaces in paths are safe)."""
    proc = subprocess.run(["databricks", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise CliError(f"databricks {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def remote_uri(path: str) -> str:
    return f"{VOLUME}/{path.strip('/')}" if path.strip("/") else VOLUME


def list_dir(path: str, run: Runner = run_cli) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = json.loads(run(["fs", "ls", remote_uri(path), "-o", "json"]))
    return entries


def list_target(target: Target, run: Runner = run_cli, workers: int = 8) -> list[RemoteFile]:
    """Return every file under target. Directories are listed level by level in parallel."""
    if not target.is_directory:
        parent, _, name = target.path.rpartition("/")
        for entry in list_dir(parent, run):
            if entry["name"] == name and not entry["is_directory"]:
                return [RemoteFile(target.path, int(entry["size"]))]
        raise FileNotFoundError(remote_uri(target.path))

    files: list[RemoteFile] = []
    pending = [target.path.rstrip("/")]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while pending:
            listings = list(pool.map(lambda d: (d, list_dir(d, run)), pending))
            pending = []
            for directory, entries in listings:
                for entry in entries:
                    child = f"{directory}/{entry['name']}"
                    if entry["is_directory"]:
                        pending.append(child)
                    else:
                        files.append(RemoteFile(child, int(entry["size"])))
    return sorted(files, key=lambda f: f.path)


def summarise(target: Target, files: list[RemoteFile]) -> TargetSummary:
    return TargetSummary(target, files=len(files), bytes=sum(f.size for f in files))


@dataclass
class CopyResult:
    expected: int = 0
    copied: list[RemoteFile] = field(default_factory=list)
    skipped: list[RemoteFile] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def local_path(raw_dir: Path, remote: RemoteFile) -> Path:
    return raw_dir.joinpath(*remote.path.split("/"))


def copy_file(
    remote: RemoteFile,
    raw_dir: Path,
    run: Runner = run_cli,
    retries: int = RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Copy one file. Returns False if it was already present with the same size.

    The copy lands in a .part file and is renamed only when its size matches the listing.
    Failures are retried up to `retries` times with exponential backoff.
    """
    dest = local_path(raw_dir, remote)
    if dest.exists() and dest.stat().st_size == remote.size:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(retries + 1):
        try:
            run(["fs", "cp", "--overwrite", remote_uri(remote.path), str(tmp)])
            size = tmp.stat().st_size
            if size != remote.size:
                raise CliError(f"size {size} != listed {remote.size}")
            tmp.replace(dest)
            return True
        except (CliError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            if attempt == retries:
                raise CliError(f"{remote.path}: {exc}") from exc
            log.warning("retry %d/%d %s: %s", attempt + 1, retries, remote.path, exc)
            sleep(2.0 * 2**attempt)
    raise AssertionError("unreachable")


def copy_all(
    files: Sequence[RemoteFile],
    raw_dir: Path,
    run: Runner = run_cli,
    workers: int = 8,
    sleep: Callable[[float], None] = time.sleep,
) -> CopyResult:
    result = CopyResult(expected=len(files))

    def task(remote: RemoteFile) -> tuple[RemoteFile, bool | str]:
        try:
            return remote, copy_file(remote, raw_dir, run, sleep=sleep)
        except CliError as exc:
            return remote, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for done, (remote, outcome) in enumerate(pool.map(task, files), start=1):
            if outcome is True:
                result.copied.append(remote)
            elif outcome is False:
                result.skipped.append(remote)
            else:
                result.failures.append(str(outcome))
            if done % 500 == 0:
                log.info("%d/%d files processed", done, len(files))
    return result


def manifest_entries(
    files: Sequence[RemoteFile], raw_dir: Path, data_dir: Path, manifest_path: Path
) -> list[ManifestEntry]:
    """Entries for every Volve file present locally with the listed size.

    A file whose existing manifest entry already has the same size keeps that entry (and its
    original retrieved_at). Otherwise the file is hashed and retrieved_at is its local
    modification time in UTC, which is when the copy finished.
    """
    previous = {entry.file: entry for entry in load_manifest(manifest_path)}
    entries = []
    for remote in files:
        path = local_path(raw_dir, remote)
        if not path.exists() or path.stat().st_size != remote.size:
            continue
        key = path.relative_to(data_dir).as_posix()
        old = previous.get(key)
        if old is not None and old.bytes == remote.size and old.source == SOURCE:
            entries.append(old)
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries.append(build_entry(path, data_dir, SOURCE, remote_uri(remote.path), LICENCE, mtime))
    return entries
