"""Draw the held-out wellbores defined in ADR 0002, decision D8, and write evaluation/splits.json.

D8 as implemented here:
- Population: 15/9-F wellbores with at least 20 daily drilling reports (expected: 17).
- 15/9-F-11 T2 is always a development wellbore.
- The other wellbores are ordered by their D1 key (Sodir NPDID, numerically, then the technical
  sidetrack suffix), and five are drawn with random.Random(20261028).sample(candidates, 5).

The draw is made once. The script refuses to overwrite an existing splits file. It prints no
wellbore names and reads nothing but the drilling report headers needed to count reports.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

from well_ops.ingestion.audit import load_drill_reports, normalise_well_name

SEED = 20261028
HELD_OUT = 5
MIN_REPORTS = 20
EXPECTED_POPULATION = 17
ALWAYS_DEVELOPMENT = "15/9-F-11 T2"


def wellbore_key(npdid: str, name: str) -> str:
    """D1 key: the Sodir NPDID, plus ':T2' (or ':T3', ...) for a technical sidetrack."""
    sidetrack = re.search(r" (T\d+)$", name)
    return f"{npdid}:{sidetrack.group(1)}" if sidetrack else npdid


def sort_key(key: str) -> tuple[int, str]:
    npdid, _, suffix = key.partition(":")
    return int(npdid), suffix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/splits.json"))
    args = parser.parse_args(argv)
    if args.out.exists():
        print(
            f"{args.out} already exists; the draw is made once and not repeated.", file=sys.stderr
        )
        return 1

    reports = load_drill_reports(args.raw_dir)
    counts = Counter((normalise_well_name(r.wellbore), r.npdid) for r in reports)
    population = {
        wellbore_key(npdid, name): name
        for (name, npdid), n in counts.items()
        if name.startswith("15/9-F-") and npdid and n >= MIN_REPORTS
    }
    if len(population) != EXPECTED_POPULATION:
        raise SystemExit(f"population has {len(population)} wellbores, D8 expects 17")
    fixed = [k for k, name in population.items() if name == ALWAYS_DEVELOPMENT]
    if len(fixed) != 1:
        raise SystemExit(f"{ALWAYS_DEVELOPMENT} must be in the population exactly once")

    candidates = sorted((k for k in population if k not in fixed), key=sort_key)
    held_out = sorted(random.Random(SEED).sample(candidates, HELD_OUT), key=sort_key)
    development = sorted((k for k in population if k not in held_out), key=sort_key)

    def entries(keys: list[str]) -> list[dict[str, str]]:
        return [{"key": k, "name": population[k]} for k in keys]

    splits = {
        "decision": "docs/adr/0002-phase-2-data-decisions.md, D8",
        "population_rule": (f"15/9-F wellbores with at least {MIN_REPORTS} daily drilling reports"),
        "always_development": entries(fixed),
        "method": (
            f"random.Random({SEED}).sample(candidates, {HELD_OUT}); candidates are the population "
            "without the always-development wellbore, ordered by D1 key (NPDID numerically, then "
            "sidetrack suffix)"
        ),
        "seed": SEED,
        "candidates": entries(candidates),
        "held_out": entries(held_out),
        "development": entries(development),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(splits, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: {len(population)} in population, {len(held_out)} held out, "
        f"{len(development)} development"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
