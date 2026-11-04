"""evaluation/RULES.md and the checker must state the same tolerances and metrics."""

from __future__ import annotations

import re
from pathlib import Path

from well_ops.agents.checker import METRICS, TOLERANCES, Tolerance
from well_ops.agents.schema import UNITS, ClaimType

RULES = Path(__file__).parents[2] / "evaluation" / "RULES.md"


def _table(heading: str) -> list[list[str]]:
    """The rows of the first table after a `## heading`, without its header lines."""
    section = RULES.read_text(encoding="utf-8").split(f"## {heading}\n", 1)[1]
    rows = [line for line in section.split("\n## ", 1)[0].splitlines() if line.startswith("|")]
    return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows[2:]]


def test_tolerances_match() -> None:
    stated = {
        ClaimType(t): (unit or None, Tolerance(float(a), float(r)))
        for t, unit, a, r in _table("Tolerances")
    }
    assert stated == {t: (UNITS[t], tol) for t, tol in TOLERANCES.items()}


def test_metrics_match() -> None:
    stated = {}
    for metric, claim_type, scope, _ in _table("Metrics"):
        keys = set(re.findall(r"[a-z_]+", scope)) - {"or", "and"}
        stated[metric] = (ClaimType(claim_type), keys)
    assert stated == {name: (next(iter(m.types)), set(m.scope)) for name, m in METRICS.items()}
