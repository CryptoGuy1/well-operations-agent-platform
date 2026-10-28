"""Download all Phase 1 raw data and write data/manifest.json."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from well_ops.ingestion import cira_pumps, sodir_factpages
from well_ops.ingestion.manifest import MANIFEST_NAME, write_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    entries = []
    failures = []
    for source in (cira_pumps, sodir_factpages):
        result = source.download(args.data_dir)
        entries.extend(result.entries)
        failures.extend(result.failures)

    manifest = write_manifest(args.data_dir / MANIFEST_NAME, entries)
    print(f"\n{'file':<45} {'bytes':>10}  sha256        licence")
    for entry in manifest:
        print(f"{entry.file:<45} {entry.bytes:>10}  {entry.sha256[:12]}  {entry.licence}")
    print(f"\n{len(entries)} downloaded, {len(failures)} failed, {len(manifest)} in manifest")
    for failure in failures:
        print(f"FAILED {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
