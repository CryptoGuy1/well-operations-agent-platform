"""Compute the Phase 2 data-quality report and fill docs/data/data-quality-report.md.

Reads the warehouse and the last `dbt build` results; run `make rebuild` (or `make dbt-build`)
first. Only the text between `<!-- quality:NAME -->` markers is replaced.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from well_ops.markdown import fill_report
from well_ops.warehouse.quality import build_sections


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/warehouse/well_ops.duckdb"))
    parser.add_argument("--staging-dir", type=Path, default=Path("data/staging"))
    parser.add_argument("--target-dir", type=Path, default=Path("warehouse/target"))
    parser.add_argument("--report", type=Path, default=Path("docs/data/data-quality-report.md"))
    args = parser.parse_args(argv)
    sections = build_sections(args.database, args.staging_dir, args.target_dir)
    report = args.report.read_text(encoding="utf-8")
    args.report.write_text(fill_report(report, sections, prefix="quality"), encoding="utf-8")
    print(f"filled {len(sections)} sections in {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
