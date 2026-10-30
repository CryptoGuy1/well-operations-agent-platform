"""Extract one wellbore's WITSML logs from the Volve zip on demand (ADR 0002 D6).

Usage: make extract-log WELLBORE=<D1 key>. Run `make stage` first so the alias table exists.
Held-out wellbores are refused unless --allow-heldout is given (ADR 0002 D8).
Prints counts only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from well_ops.ingestion.manifest import write_manifest
from well_ops.ingestion.volve_witsml import extract_logs, heldout_keys, witsml_names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wellbore", required=True, help="D1 key, for example 7078:T2")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--splits", type=Path, default=Path("evaluation/splits.json"))
    parser.add_argument("--allow-heldout", action="store_true")
    args = parser.parse_args(argv)
    if args.wellbore in heldout_keys(args.splits) and not args.allow_heldout:
        print(f"{args.wellbore} is held out (D8); pass --allow-heldout to extract it")
        return 2
    names = witsml_names(args.data_dir / "staging", args.wellbore)
    entries = extract_logs(args.data_dir, args.wellbore, names)
    write_manifest(args.data_dir / "manifest.json", entries)
    total = sum(e.bytes for e in entries)
    print(f"{args.wellbore}: {len(entries)} log files, {total / 1e6:,.1f} MB; manifest updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
