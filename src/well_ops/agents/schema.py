"""The agent output contract (ADR 0004): a document of sections, sentences and claims.

An agent returns this JSON. It is validated here, checked by `well_ops.agents.checker`, and only
then rendered. Every quantity, date, measurement, activity code or quotation in a sentence is a
claim; identifiers (wellbore names, NPDIDs, evidence ids) are not.

A claim's `what` names the metric it states and its scope, for example
`{"metric": "lost_hours", "wellbore": "15/9-F-11 T2", "section": 2, "tier": "primary"}`. The
metrics and their scope keys are listed in evaluation/RULES.md.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterator
from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)


class ClaimType(StrEnum):
    HOURS = "hours"
    DEPTH_M = "depth_m"
    DATE = "date"
    COUNT = "count"
    HOLE_SIZE_IN = "hole_size_in"
    RATE_M_PER_H = "rate_m_per_h"
    VOLUME_SM3 = "volume_sm3"
    CODE = "code"
    QUOTE = "quote"


# The one unit each claim type is stated in; None for types without a unit.
UNITS: dict[ClaimType, str | None] = {
    ClaimType.HOURS: "h",
    ClaimType.DEPTH_M: "m",
    ClaimType.DATE: None,
    ClaimType.COUNT: None,
    ClaimType.HOLE_SIZE_IN: "in",
    ClaimType.RATE_M_PER_H: "m/h",
    ClaimType.VOLUME_SM3: "Sm3",
    ClaimType.CODE: None,
    ClaimType.QUOTE: None,
}

NUMERIC = frozenset(
    {
        ClaimType.HOURS,
        ClaimType.DEPTH_M,
        ClaimType.COUNT,
        ClaimType.HOLE_SIZE_IN,
        ClaimType.RATE_M_PER_H,
        ClaimType.VOLUME_SM3,
    }
)

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

Scalar = str | int | float | bool | None


class What(BaseModel):
    """The metric a claim states and its scope (every other key)."""

    model_config = ConfigDict(extra="allow", frozen=True)

    metric: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _scalar_scope(self) -> Self:
        for value in (self.model_extra or {}).values():
            if not isinstance(value, Scalar):
                raise ValueError("scope values must be strings, numbers, booleans or null")
        return self

    @property
    def scope(self) -> dict[str, Scalar]:
        return dict(self.model_extra or {})


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")
    type: ClaimType
    value: StrictInt | StrictFloat | StrictStr
    unit: str | None = None
    # Not validated here: a malformed or unknown id is a checker result, never a dropped claim.
    evidence_ids: list[str] = Field(default_factory=list, max_length=200)
    what: What

    @model_validator(mode="after")
    def _value_fits_type(self) -> Self:
        if self.unit != UNITS[self.type]:
            raise ValueError(f"{self.type} claims take unit {UNITS[self.type]!r}")
        if isinstance(self.value, bool):
            raise ValueError("a claim value is never a boolean")
        if self.type in NUMERIC and not isinstance(self.value, int | float):
            raise ValueError(f"{self.type} claims take a number")
        if self.type is ClaimType.COUNT and not isinstance(self.value, int):
            raise ValueError("count claims take a whole number")
        if self.type is ClaimType.DATE:
            if not (isinstance(self.value, str) and ISO_DATE.fullmatch(self.value)):
                raise ValueError("date claims take a yyyy-mm-dd date")
            dt.date.fromisoformat(self.value)
        if self.type in (ClaimType.CODE, ClaimType.QUOTE) and not (
            isinstance(self.value, str) and self.value
        ):
            raise ValueError(f"{self.type} claims take non-empty text")
        return self


class Sentence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)
    claims: list[Claim] = Field(default_factory=list)


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heading: str = Field(min_length=1)
    sentences: list[Sentence] = Field(min_length=1)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent: str = Field(min_length=1)
    title: str = Field(min_length=1)
    sections: list[Section] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_claim_ids(self) -> Self:
        ids = [claim.id for claim in self.claims()]
        if len(ids) != len(set(ids)):
            raise ValueError("claim ids must be unique within a document")
        return self

    def claims(self) -> Iterator[Claim]:
        for section in self.sections:
            for sentence in section.sentences:
                yield from sentence.claims
