"""Compute the Phase 1 data audit from data/raw/ and fill docs/data/data-audit-report.md.

Only the text between `<!-- audit:NAME -->` markers is replaced; everything else in the report
is left as written.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from well_ops.ingestion.audit import build_sections, fill_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--report", type=Path, default=Path("docs/data/data-audit-report.md"))
    args = parser.parse_args(argv)
    sections = build_sections(args.raw_dir)
    report = args.report.read_text(encoding="utf-8")
    args.report.write_text(fill_report(report, sections), encoding="utf-8")
    print(f"filled {len(sections)} sections in {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
