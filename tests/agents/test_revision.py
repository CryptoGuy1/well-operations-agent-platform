"""What a revision removed from the first draft (evaluation/RULES.md, scored draft)."""

from __future__ import annotations

from typing import Any

from well_ops.agents.revision import removed_in_revision, removed_lines
from well_ops.agents.schema import Document


def _claim(id_: str, value: float, evidence: str, section: int = 1) -> dict[str, Any]:
    return {
        "id": id_,
        "type": "hours",
        "value": value,
        "unit": "h",
        "evidence_ids": [evidence],
        "what": {"metric": "lost_hours", "wellbore": "W-1", "tier": "primary", "section": section},
    }


def _document(*sentences: tuple[str, list[dict[str, Any]]]) -> Document:
    return Document.model_validate(
        {
            "agent": "test",
            "title": "t",
            "sections": [
                {
                    "heading": "h",
                    "sentences": [{"text": t, "claims": c} for t, c in sentences],
                }
            ],
        }
    )


def test_a_claim_kept_with_other_evidence_or_id_is_not_removed() -> None:
    first = _document(("Section 1 lost 6.0 h.", [_claim("c1", 6.0, "ddr:x:1")]))
    final = _document(("Section 1 lost 6.0 h.", [_claim("c9", 6.0, "ddr:x:2")]))
    removed = removed_in_revision(first, final)
    assert removed.claims == [] and removed.numbers == []


def test_removed_claims_and_numbers_are_listed_with_repeats() -> None:
    first = _document(
        (
            "Section 1 lost 6.0 h and section 2 lost 3.0 h.",
            [
                _claim("c1", 6.0, "ddr:x:1"),
                _claim("c2", 3.0, "ddr:x:2", section=2),
            ],
        ),
        ("Winds of 40 to 50 knots, then 40 again, in campaign 2.", []),
    )
    final = _document(
        ("Section 1 lost 6.0 h.", [_claim("c1", 6.0, "ddr:x:1")]),
        ("Strong winds, 40 at most, in the second campaign.", []),
    )
    removed = removed_in_revision(first, final)
    assert [c.id for c in removed.claims] == ["c2"]
    assert removed.numbers == ["3.0", "50", "40"]
    lines = removed_lines(removed)
    assert lines[2] == "1 claims and 3 numbers of the first draft are not in the final draft."
    assert "Numbers: `3.0`, `50`, `40`" in lines
