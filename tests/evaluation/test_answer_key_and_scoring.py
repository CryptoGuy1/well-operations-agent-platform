"""Answer key and scoring on the synthetic warehouse of conftest.py (fictional wellbore 9001:T2,
a development wellbore)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from well_ops.agents.checker import Checker, ClaimResult, Verdict
from well_ops.agents.schema import Claim
from well_ops.connectors.base import connect
from well_ops.evaluation import answer_key
from well_ops.evaluation.answer_key import SECTION_COUNT, Fact, WellboreKey
from well_ops.evaluation.scoring import COVERED, MISSING, WRONG, coverage, normalise_scope

T2 = "9001:T2"


def key_of(warehouse: Path, checker: Checker) -> WellboreKey:
    con = connect(warehouse)
    try:
        return answer_key.wellbore_key(con, checker, T2, "XX/1-A-1 T2", "development")
    finally:
        con.close()


def facts(key: WellboreKey) -> dict[tuple[str, tuple[tuple[str, Any], ...]], Any]:
    return {(f.metric, tuple(sorted(f.scope.items()))): f.value for f in key.facts}


def scope(**values: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted({"wellbore": T2, **values}.items()))


def test_the_key_holds_the_listed_facts(warehouse: Path, checker: Checker) -> None:
    key = key_of(warehouse, checker)
    found = facts(key)
    assert key.sections == [1, 2, 3]
    assert found[(SECTION_COUNT, scope())] == 3
    assert found[("campaign_count", scope())] == 1
    assert found[("campaign_start_date", scope(campaign=1))] == "2020-01-02"
    assert found[("section_hole_size", scope(section=2))] == 12.25
    assert found[("section_end_md", scope(section=2))] == 2000.0
    assert found[("new_hole_drilled", scope(section=1))] == 1000.0
    assert found[("lost_hours", scope(tier="primary", section=1))] == 5.0
    assert found[("lost_hours", scope(tier="possible", section=2))] == 2.0
    # The largest primary cause, and the totals.
    assert found[("lost_hours", scope(tier="primary", code="interruption -- wait"))] == 5.0
    assert found[("lost_hours", scope(tier="primary"))] == 8.5
    assert found[("lost_hours", scope(tier="possible"))] == 2.0
    # Zero facts are left out: section 3 drilled no new hole and lost no time, section 1 starts
    # at 0 m and has no possible lost time.
    assert ("new_hole_drilled", scope(section=3)) not in found
    assert ("section_start_md", scope(section=1)) not in found
    assert ("lost_hours", scope(tier="possible", section=1)) not in found
    assert key.zero >= 5


def test_the_key_file_round_trips(warehouse: Path, checker: Checker, tmp_path: Path) -> None:
    key = key_of(warehouse, checker)
    path = tmp_path / "key.jsonl"
    sha256 = answer_key.write([key], path)
    assert len(sha256) == 64 and answer_key.read(path) == [key]
    assert answer_key.dumps(answer_key.read(path)) == path.read_text(encoding="utf-8")


def claim(n: int, metric: str, value: Any, **what: Any) -> Claim:
    types = {"section_hole_size": ("hole_size_in", "in"), "lost_hours": ("hours", "h")}
    claim_type, unit = types[metric]
    return Claim.model_validate(
        {
            "id": f"c{n}",
            "type": claim_type,
            "value": value,
            "unit": unit,
            "evidence_ids": [],
            "what": {"metric": metric, **what},
        }
    )


KEY = WellboreKey(
    T2,
    "XX/1-A-1 T2",
    "development",
    [0, 1, 2],
    [
        Fact(SECTION_COUNT, {"wellbore": T2}, 2),
        Fact("section_hole_size", {"wellbore": T2, "section": 1}, 26.0),
        Fact("section_hole_size", {"wellbore": T2, "section": 2}, 12.25),
        Fact("lost_hours", {"wellbore": T2, "tier": "primary"}, 8.5),
    ],
)


def resolve(text: str) -> str | None:
    return {"XX/1-A-1 T2": T2, T2: T2}.get(text)


def statuses(claims: list[Claim], verdicts: list[Verdict]) -> list[str]:
    results = [ClaimResult(c.id, v, "test") for c, v in zip(claims, verdicts, strict=True)]
    return [d.status for d in coverage(KEY, claims, results, resolve).details]


def test_a_fact_is_covered_wrong_or_missing() -> None:
    claims = [
        claim(1, "section_hole_size", 26.0, wellbore="XX/1-A-1 T2", section=1),  # by name
        claim(2, "section_hole_size", 12.0, wellbore=T2, section="2"),
        claim(3, "lost_hours", 8.5, wellbore=T2, tier="primary", section=1),  # another scope
    ]
    verdicts = [Verdict.VERIFIED, Verdict.CONTRADICTED, Verdict.VERIFIED]
    # Section 2 has no verified claim, so the section count is missing.
    assert statuses(claims, verdicts) == [MISSING, COVERED, WRONG, MISSING]


def test_a_verified_claim_wins_over_a_contradicted_one() -> None:
    claims = [
        claim(1, "lost_hours", 9.0, wellbore=T2, tier="primary"),
        claim(2, "lost_hours", 8.5, wellbore=T2, tier="primary"),
    ]
    assert statuses(claims, [Verdict.CONTRADICTED, Verdict.VERIFIED])[3] == COVERED


def test_the_section_count_is_implied_by_the_sections() -> None:
    both = [
        claim(1, "section_hole_size", 26.0, wellbore=T2, section=1),
        claim(2, "section_hole_size", 12.25, wellbore=T2, section=2),
    ]
    verified = [Verdict.VERIFIED, Verdict.VERIFIED]
    assert statuses(both, verified)[0] == COVERED  # section 0 is not needed
    extra = [*both, claim(3, "lost_hours", 1.0, wellbore=T2, tier="primary", section=7)]
    assert statuses(extra, [*verified, Verdict.UNSUPPORTED])[0] == WRONG
    zero = [*both, claim(3, "lost_hours", 1.0, wellbore=T2, tier="primary", section=0)]
    assert statuses(zero, [*verified, Verdict.VERIFIED])[0] == COVERED


def test_scopes_are_normalised() -> None:
    assert normalise_scope({"wellbore": "XX/1-A-1 T2", "section": "2"}, resolve) == {
        "wellbore": T2,
        "section": 2,
    }
    assert normalise_scope({"wellbore": "unknown"}, resolve) is None
    assert normalise_scope({"wellbore": T2, "section": True}, resolve) is None
