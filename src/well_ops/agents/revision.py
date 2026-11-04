"""What a revision removed (evaluation/RULES.md, scored draft): the claims and the numbers of the
first draft that the final draft no longer has. A claim is matched by its type, value and `what`,
so a claim kept with other evidence or another id is not removed; a number by its text as
written, identifiers masked, counted over the whole document."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from well_ops.agents.checker import written_numbers
from well_ops.agents.schema import Claim, Document


@dataclass(frozen=True)
class Removed:
    claims: list[Claim]  # first-draft claims, in document order
    numbers: list[str]  # first-draft numbers and dates as written, in document order


def _key(claim: Claim) -> str:
    what = claim.what.model_dump(mode="json")
    return json.dumps([str(claim.type), claim.value, what], sort_keys=True)


def _numbers(document: Document) -> list[str]:
    return [
        written
        for section in document.sections
        for sentence in section.sentences
        for _, written in written_numbers(sentence.text)
    ]


def _missing[T](first: list[T], final: list[T], key: Callable[[T], str] = str) -> list[T]:
    """The items of `first` that `final` does not have, counting repeats."""
    left = Counter(key(item) for item in final)
    missing = []
    for item in first:
        if left[key(item)] > 0:
            left[key(item)] -= 1
        else:
            missing.append(item)
    return missing


def removed_in_revision(first: Document, final: Document) -> Removed:
    """The claims and numbers of the first draft that are absent from the final draft."""
    return Removed(
        _missing(list(first.claims()), list(final.claims()), _key),
        _missing(_numbers(first), _numbers(final)),
    )


def removed_lines(removed: Removed) -> list[str]:
    """Markdown for a run report, next to the final-draft results."""
    lines = [
        "## Removed during revision",
        "",
        f"{len(removed.claims)} claims and {len(removed.numbers)} numbers of the first draft are "
        "not in the final draft.",
    ]
    if removed.claims:
        lines += ["", "| Claim | Type | Metric | Value |", "|---|---|---|---|"]
        lines += [
            f"| {c.id} | {c.type} | {c.what.metric} | {str(c.value).replace('|', '\\|')} |"
            for c in removed.claims
        ]
    if removed.numbers:
        lines += ["", "Numbers: " + ", ".join(f"`{n}`" for n in removed.numbers)]
    return lines
