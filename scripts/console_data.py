"""Export the console's data bundle (ADR 0005) into `console/public/data/`.

    uv run python scripts/console_data.py

Reads the warehouse, the dbt build results `make dbt-build` copies beside it, the local run logs
(development runs and release r2) and the committed evaluation results. Prints the bundle size,
the five largest files and the personal-data scan (counts only); exits 1 if the scan finds
anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from well_ops.connectors.redaction import MATCH_TYPES, Redactor
from well_ops.console_data.bundle import Bundle, scan
from well_ops.console_data.export import build
from well_ops.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("console/public/data"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args(argv)

    settings = Settings()
    if settings.evaluation_mode:
        print("refused: the bundle is not exported in evaluation mode", file=sys.stderr)
        return 2
    bundle = Bundle(args.out)
    build(settings, bundle, args.results_dir)

    sizes = bundle.sizes()
    print(f"bundle: {len(sizes)} files, {sum(n for _, n in sizes) / 1024:.1f} KiB in {args.out}")
    for name, n in sizes[:5]:
        print(f"  {n / 1024:8.1f} KiB  {name}")
    found = scan(bundle, Redactor.from_file(settings.redaction_denylist_path))
    print("personal-data scan: " + ", ".join(f"{found[k]} {k}" for k in MATCH_TYPES))
    return 1 if sum(found.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
