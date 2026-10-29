"""Parse data/raw/ into typed Parquet files under data/staging/ (ADR 0003).

Prints row counts only. Per the held-out rule, no wellbore names are printed.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from well_ops.ingestion.identifiers import stage_aliases
from well_ops.ingestion.sodir_factpages import stage_wellbores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--staging-dir", type=Path, default=Path("data/staging"))
    args = parser.parse_args(argv)
    print(f"sodir/wellbore.parquet: {stage_wellbores(args.raw_dir, args.staging_dir)} rows")
    aliases = stage_aliases(args.raw_dir, args.staging_dir)
    print(f"identifiers/wellbore_alias.parquet: {len(aliases)} rows")
    for (status, method), n in sorted(Counter((a.status, a.match_method) for a in aliases).items()):
        print(f"  status {status}, match {method}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
