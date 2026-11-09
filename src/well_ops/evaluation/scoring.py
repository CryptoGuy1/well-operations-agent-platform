"""Scoring of one draft (evaluation/RULES.md): claim counts and rates, and answer-key coverage.

A key fact is covered by a verified claim of the same metric and scope, wrong when a claim of
that metric and scope is contradicted and none is verified, and missing otherwise. A claim's
scope is compared after its wellbore is resolved to its key. The section count is covered when
every hole section of the wellbore (section 0 excepted) has a verified section-scoped claim and
no claim names a section the wellbore does not have; it is wrong when a claim names such a
section.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from well_ops.agents.checker import Checker, ClaimResult, UnclaimedNumber, Verdict
from well_ops.agents.schema import Claim, Document, Scalar
from well_ops.evaluation.answer_key import SECTION_COUNT, WellboreKey

COVERED, WRONG, MISSING = "covered", "wrong", "missing"


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def normalise_scope(
    scope: Mapping[str, Scalar], resolve: Callable[[str], str | None]
) -> dict[str, Scalar] | None:
    """A claim's scope in the answer key's form: the wellbore as its key, section and campaign
    numbers as integers. None when the wellbore or a number cannot be read."""
    out: dict[str, Scalar] = {}
    for name, value in scope.items():
        if name == "wellbore":
            key = resolve(str(value))
            if key is None:
                return None
            out[name] = key
        elif name in ("section", "campaign"):
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                out[name] = value
            elif isinstance(value, str) and value.strip().isdigit():
                out[name] = int(value)
            else:
                return None
        else:
            out[name] = value
    return out


@dataclass(frozen=True)
class FactResult:
    metric: str
    scope: dict[str, Scalar]
    status: str  # covered, wrong or missing


@dataclass(frozen=True)
class Coverage:
    facts: int
    covered: int
    wrong: int
    missing: int
    details: list[FactResult] = field(default_factory=list)

    @property
    def rate(self) -> float | None:
        return _ratio(self.covered, self.facts)


def coverage(
    key: WellboreKey,
    claims: Sequence[Claim],
    results: Sequence[ClaimResult],
    resolve: Callable[[str], str | None],
) -> Coverage:
    by_id = {r.claim_id: r.verdict for r in results}
    scoped: list[tuple[str, dict[str, Scalar], Verdict]] = []
    for claim in claims:
        scope = normalise_scope(claim.what.scope, resolve)
        if scope is not None and claim.id in by_id:
            scoped.append((claim.what.metric, scope, by_id[claim.id]))

    details = []
    for fact in key.facts:
        if fact.metric == SECTION_COUNT:
            status = _section_count(key, scoped)
        else:
            verdicts = {v for m, s, v in scoped if m == fact.metric and s == fact.scope}
            if Verdict.VERIFIED in verdicts:
                status = COVERED
            elif Verdict.CONTRADICTED in verdicts:
                status = WRONG
            else:
                status = MISSING
        details.append(FactResult(fact.metric, fact.scope, status))
    count = {s: sum(d.status == s for d in details) for s in (COVERED, WRONG, MISSING)}
    return Coverage(len(details), count[COVERED], count[WRONG], count[MISSING], details)


def _section_count(
    key: WellboreKey, scoped: Iterable[tuple[str, dict[str, Scalar], Verdict]]
) -> str:
    named: set[Scalar] = set()
    verified: set[Scalar] = set()
    for _, scope, verdict in scoped:
        if scope.get("wellbore") == key.wellbore_key and "section" in scope:
            named.add(scope["section"])
            if verdict is Verdict.VERIFIED:
                verified.add(scope["section"])
    if named - set(key.sections):
        return WRONG
    return COVERED if {n for n in key.sections if n > 0} <= verified else MISSING


@dataclass(frozen=True)
class DraftScore:
    claims: int
    verified: int
    contradicted: int
    unsupported: int
    unverifiable: int
    unclaimed: int
    coverage: Coverage

    @property
    def accuracy(self) -> float | None:
        """verified / (verified + contradicted)"""
        return _ratio(self.verified, self.verified + self.contradicted)

    @property
    def unsupported_rate(self) -> float | None:
        return _ratio(self.unsupported, self.claims)

    @property
    def unverifiable_rate(self) -> float | None:
        return _ratio(self.unverifiable, self.claims)

    @property
    def unclaimed_rate(self) -> float | None:
        return _ratio(self.unclaimed, self.claims + self.unclaimed)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["coverage"] = {
            "facts": self.coverage.facts,
            "covered": self.coverage.covered,
            "wrong": self.coverage.wrong,
            "missing": self.coverage.missing,
            "rate": self.coverage.rate,
            "details": [asdict(d) for d in self.coverage.details],
        }
        data |= {
            "accuracy": self.accuracy,
            "unsupported_rate": self.unsupported_rate,
            "unverifiable_rate": self.unverifiable_rate,
            "unclaimed_rate": self.unclaimed_rate,
        }
        return data


def score_draft(
    document: Document,
    results: Sequence[ClaimResult],
    unclaimed: Sequence[UnclaimedNumber],
    key: WellboreKey,
    checker: Checker,
) -> DraftScore:
    counts = {v: sum(r.verdict is v for r in results) for v in Verdict}
    return DraftScore(
        claims=len(results),
        verified=counts[Verdict.VERIFIED],
        contradicted=counts[Verdict.CONTRADICTED],
        unsupported=counts[Verdict.UNSUPPORTED],
        unverifiable=counts[Verdict.UNVERIFIABLE],
        unclaimed=len(unclaimed),
        coverage=coverage(key, list(document.claims()), results, checker.wellbore_key),
    )
