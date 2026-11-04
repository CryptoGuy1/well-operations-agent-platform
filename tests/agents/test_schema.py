"""Output contract validation (fictional values)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from well_ops.agents.schema import Claim, ClaimType, Document


def _claim(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "c1",
        "type": "hours",
        "value": 3.5,
        "unit": "h",
        "evidence_ids": ["ddr:report:R1"],
        "what": {"metric": "lost_hours", "wellbore": "XX/1-A-1", "section": 2},
        **overrides,
    }


def test_a_valid_claim_keeps_its_scope() -> None:
    claim = Claim.model_validate(_claim())
    assert claim.type is ClaimType.HOURS
    assert claim.what.scope == {"wellbore": "XX/1-A-1", "section": 2}


@pytest.mark.parametrize(
    "overrides",
    [
        {"unit": "min"},  # the unit is fixed by the type
        {"value": "3.5"},  # numbers are numbers
        {"value": True},
        {"type": "count", "unit": None, "value": 2.5},
        {"type": "date", "unit": None, "value": "2020-02-30"},
        {"type": "date", "unit": None, "value": "02/01/2020"},
        {"type": "quote", "unit": None, "value": ""},
        {"type": "volume", "unit": "Sm3"},  # not a claim type
        {"what": {"wellbore": "XX/1-A-1"}},  # no metric
        {"what": {"metric": "lost_hours", "section": [1, 2]}},  # scope values are scalars
        {"id": "has space"},
        {"comment": "extra field"},
    ],
)
def test_invalid_claims_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate(_claim(**overrides))


def test_evidence_ids_are_not_validated_by_the_schema() -> None:
    # A malformed id is a checker result (unsupported), never a rejected document.
    assert Claim.model_validate(_claim(evidence_ids=["not an id"])).evidence_ids == ["not an id"]


def test_claim_ids_are_unique_in_a_document() -> None:
    sentence = {"text": "Two claims.", "claims": [_claim(), _claim()]}
    with pytest.raises(ValidationError, match="unique"):
        Document.model_validate(
            {"agent": "a", "title": "t", "sections": [{"heading": "h", "sentences": [sentence]}]}
        )
