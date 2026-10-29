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
from well_ops.ingestion.volve_ddr import load_drill_reports, stage_drill_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--staging-dir", type=Path, default=Path("data/staging"))
    args = parser.parse_args(argv)
    print(f"sodir/wellbore.parquet: {stage_wellbores(args.raw_dir, args.staging_dir)} rows")
    reports = load_drill_reports(args.raw_dir)
    aliases = stage_aliases(args.raw_dir, args.staging_dir, reports)
    print(f"identifiers/wellbore_alias.parquet: {len(aliases)} rows")
    for (status, method), n in sorted(Counter((a.status, a.match_method) for a in aliases).items()):
        print(f"  status {status}, match {method}: {n}")
    ddr = stage_drill_reports(args.raw_dir, args.staging_dir, reports)
    print(
        f"ddr/report.parquet: {ddr.reports} rows ({ddr.wellbore_keys} wellbore keys), "
        f"ddr/activity.parquet: {ddr.activities} rows"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
