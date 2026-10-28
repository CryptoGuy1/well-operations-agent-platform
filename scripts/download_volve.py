"""Copy the Volve Data Village files used by this project into data/raw/volve/.

Requires the Databricks CLI, signed in with `databricks auth login`. Resumable: files already
present with the listed size are skipped. Adds every Volve file to data/manifest.json.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from well_ops.ingestion.manifest import MANIFEST_NAME, write_manifest
from well_ops.ingestion.volve_files import (
    TARGETS,
    RemoteFile,
    copy_all,
    list_target,
    manifest_entries,
    summarise,
)


def _size(n: int) -> str:
    return f"{n / 1e6:,.1f} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--list-only", action="store_true", help="measure only, copy nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print(f"{'path':<65} {'files':>7} {'expected':>9} {'size':>12}")
    files: list[RemoteFile] = []
    for target in TARGETS:
        listed = list_target(target)
        summary = summarise(target, listed)
        expected = "" if target.expected_files is None else f"{target.expected_files:,}"
        print(f"{target.path:<65} {summary.files:>7,} {expected:>9} {_size(summary.bytes):>12}")
        files.extend(listed)
    print(f"{'TOTAL':<65} {len(files):>7,} {'':>9} {_size(sum(f.size for f in files)):>12}")
    if args.list_only:
        return 0

    raw_dir = args.data_dir / "raw" / "volve"
    result = copy_all(files, raw_dir)
    manifest_path = args.data_dir / MANIFEST_NAME
    entries = manifest_entries(files, raw_dir, args.data_dir, manifest_path)
    write_manifest(manifest_path, entries)

    print(
        f"\nexpected {result.expected:,}, copied {len(result.copied):,}, "
        f"already present {len(result.skipped):,}, failed {len(result.failures):,}; "
        f"{len(entries):,} Volve files in manifest"
    )
    for failure in result.failures:
        print(f"FAILED {failure}", file=sys.stderr)
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
