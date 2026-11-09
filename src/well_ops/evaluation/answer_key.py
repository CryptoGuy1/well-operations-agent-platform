"""The answer key (evaluation/RULES.md): per wellbore, the key facts a post-well review should
state, computed from the warehouse by code.

Each fact is a checker metric with its scope and value, computed with the same code that checks
claims (`Checker.compute`), so a fact and a claim of the same metric and scope are recomputed
alike. The facts of a wellbore are:

- the report date range (`first_report_date`, `last_report_date`);
- the campaign count and each campaign's start and end dates;
- the section count (`section_count`, covered through the sections; see `scoring`);
- per hole section: start and end measured depth, hole size, new hole drilled, primary and
  possible lost hours and the drilling rate. Section 0, the activities before the first stated
  hole section, is not a hole section: it gives no facts and is not counted;
- the largest primary lost-time cause (code) with its hours; ties go to the first code in
  alphabetical order;
- the wellbore's total primary and possible lost hours.

A fact whose value is unknown (null in the warehouse) or zero is left out of the key and
counted. The key covers every wellbore of the evaluation population, held-out ones included, so
it is written to a local file and never printed. Its SHA-256 and the commit it was built from
are committed in `answer_key.sha256`, so a release can prove which key it scored against.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import duckdb

from well_ops.agents.checker import Checker, Value
from well_ops.agents.schema import Scalar

SECTION_COUNT = "section_count"  # not a checker metric: covered through the sections
SECTION_FACTS = (
    "section_start_md",
    "section_end_md",
    "section_hole_size",
    "new_hole_drilled",
    "section_drilling_rate",
)
TIERS = ("primary", "possible")


@dataclass(frozen=True)
class Fact:
    metric: str
    scope: dict[str, Scalar]  # wellbore key, section and campaign numbers, tier, code
    value: Value

    def as_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "scope": self.scope, "value": self.value}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(str(data["metric"]), dict(data["scope"]), data["value"])


@dataclass(frozen=True)
class WellboreKey:
    wellbore_key: str
    wellbore_name: str
    split: str  # "development" or "held_out"
    sections: list[int]  # every section number in the warehouse, section 0 included
    facts: list[Fact]
    unknown: int = 0  # facts left out: no value in the warehouse
    zero: int = 0  # facts left out: zero

    def as_dict(self) -> dict[str, Any]:
        return {
            "wellbore_key": self.wellbore_key,
            "wellbore_name": self.wellbore_name,
            "split": self.split,
            "sections": self.sections,
            "facts": [f.as_dict() for f in self.facts],
            "unknown": self.unknown,
            "zero": self.zero,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            str(data["wellbore_key"]),
            str(data["wellbore_name"]),
            str(data["split"]),
            [int(n) for n in data["sections"]],
            [Fact.from_dict(f) for f in data["facts"]],
            int(data["unknown"]),
            int(data["zero"]),
        )


def population(splits_path: Path) -> list[tuple[str, str, str]]:
    """(key, name, split) of every wellbore in the evaluation population: the development and
    held-out wellbores of evaluation/splits.json."""
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    return [
        (str(e["key"]), str(e["name"]), split)
        for split in ("development", "held_out")
        for e in data[split]
    ]


def _numbers(con: duckdb.DuckDBPyConnection, sql: str, key: str) -> list[int]:
    return [int(n) for (n,) in con.execute(sql, [key]).fetchall()]


def wellbore_key(
    con: duckdb.DuckDBPyConnection, checker: Checker, key: str, name: str, split: str
) -> WellboreKey:
    sections = _numbers(
        con,
        "select section_number from marts.dim_hole_section where wellbore_key = ? order by 1",
        key,
    )
    campaigns = _numbers(
        con,
        "select campaign_number from marts.dim_campaign where wellbore_key = ? order by 1",
        key,
    )
    largest = con.execute(
        "select category || ' -- ' || subcategory as code, sum(hours) as hours"
        " from marts.fct_lost_time where wellbore_key = ? and tier = 'primary'"
        " group by code having sum(hours) > 0 order by hours desc, code limit 1",
        [key],
    ).fetchone()

    wanted: list[tuple[str, dict[str, Scalar]]] = [
        ("first_report_date", {}),
        ("last_report_date", {}),
        ("campaign_count", {}),
    ]
    for n in campaigns:
        wanted += [("campaign_start_date", {"campaign": n}), ("campaign_end_date", {"campaign": n})]
    numbered = [n for n in sections if n > 0]
    for n in numbered:
        wanted += [(metric, {"section": n}) for metric in SECTION_FACTS]
        wanted += [("lost_hours", {"tier": tier, "section": n}) for tier in TIERS]
    if largest is not None:
        wanted.append(("lost_hours", {"tier": "primary", "code": str(largest[0])}))
    wanted += [("lost_hours", {"tier": tier}) for tier in TIERS]

    facts = [Fact(SECTION_COUNT, {"wellbore": key}, len(numbered))] if numbered else []
    unknown = zero = 0
    for metric, scope in wanted:
        full: dict[str, Scalar] = {"wellbore": key, **scope}
        value = checker.compute(metric, full).value
        if value is None:
            unknown += 1
        elif not isinstance(value, str) and value == 0:
            zero += 1
        else:
            facts.append(Fact(metric, full, value))
    return WellboreKey(key, name, split, sections, facts, unknown, zero)


def compute(
    con: duckdb.DuckDBPyConnection, checker: Checker, wellbores: Iterable[tuple[str, str, str]]
) -> list[WellboreKey]:
    return [wellbore_key(con, checker, key, name, split) for key, name, split in wellbores]


def dumps(keys: Sequence[WellboreKey]) -> str:
    """One JSON line per wellbore, in population order; deterministic."""
    return "".join(json.dumps(k.as_dict(), sort_keys=True, ensure_ascii=False) + "\n" for k in keys)


def sha256(keys: Sequence[WellboreKey]) -> str:
    """SHA-256 of the key file these keys are written to."""
    return hashlib.sha256(dumps(keys).encode("utf-8")).hexdigest()


def write(keys: Sequence[WellboreKey], path: Path) -> str:
    """Writes the key file and returns its SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(keys), encoding="utf-8")
    return sha256(keys)


@dataclass(frozen=True)
class KeyHash:
    """The committed record of a key file: its SHA-256 and the commit it was built from."""

    sha256: str
    built_from: str | None

    def dumps(self, file_name: str) -> str:
        return f"{self.sha256}  {file_name}\nbuilt from commit {self.built_from or 'unknown'}\n"

    @classmethod
    def read(cls, path: Path) -> KeyHash:
        lines = path.read_text(encoding="utf-8").splitlines()
        digest = lines[0].split()[0]
        built = lines[1].removeprefix("built from commit ").strip() if len(lines) > 1 else ""
        return cls(digest, None if built in ("", "unknown") else built)


def read(path: Path) -> list[WellboreKey]:
    return [
        WellboreKey.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
