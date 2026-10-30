"""Parse data/raw/ into typed Parquet files under data/staging/ (ADR 0003).

Prints row counts only. Per the held-out rule, no wellbore names are printed.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from well_ops.ingestion.identifiers import stage_aliases
from well_ops.ingestion.sodir_factpages import stage_field_production, stage_wellbores
from well_ops.ingestion.volve_ddr import load_drill_reports, stage_drill_reports
from well_ops.ingestion.volve_production import stage_production
from well_ops.ingestion.volve_witsml import (
    stage_witsml_log_values,
    stage_witsml_logs,
    stage_witsml_objects,
)


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
    daily, monthly = stage_production(args.raw_dir, args.staging_dir)
    print(f"production/daily.parquet: {daily} rows, production/monthly.parquet: {monthly} rows")
    for table, n in stage_field_production(args.raw_dir, args.staging_dir).items():
        print(f"sodir/{table}.parquet: {n} rows")
    for table, n in stage_witsml_objects(args.raw_dir, args.staging_dir).items():
        print(f"witsml/{table}.parquet: {n} rows")
    logs, curves = stage_witsml_logs(args.raw_dir, args.staging_dir)
    print(f"witsml_log/log.parquet: {logs} rows, witsml_log/log_curve.parquet: {curves} rows")
    for key, (files, rows, nulled) in stage_witsml_log_values(
        args.raw_dir, args.staging_dir
    ).items():
        print(f"witsml_log_values/{key}: {files} files, {rows} rows, {nulled} values read as null")
    return 0


if __name__ == "__main__":
    sys.exit(main())
