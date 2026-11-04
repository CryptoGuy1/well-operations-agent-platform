"""The claim checker (ADR 0004): deterministic verification of every claim against the warehouse.

For each claim the checker

1. looks up the claim's metric (`what.metric`), checks that it fits the claim type and reads its
   scope (the other `what` keys; unknown keys are refused, so no filter is silently ignored);
2. fetches every cited evidence row;
3. recomputes the metric from the warehouse, with the evidence ids of the rows the value rests on;
4. requires every cited id to be one of those ids, then compares the stated value with the
   recomputed one within the tolerance of the claim type (evaluation/RULES.md).

A claim is verified, contradicted, unsupported (no, malformed, unknown or unrelated evidence, or a
wellbore that cannot be resolved or is held out) or unverifiable (a metric or scope the checker
cannot compute). Every claim gets a result; none is dropped or corrected. No language model takes
part.

Production is checked by attributed wellbore (ADR 0002 D1, amendment of 2026-11-03): a wellbore's
volumes are recomputed from `attributed_wellbore_key`, and a cited `prod:monthly` id is matched
through the published NPDID it contains. A cited month that the workbook attributes to another
wellbore contradicts the claim.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

import duckdb

from well_ops.agents.schema import Claim, ClaimType, Document, Scalar
from well_ops.connectors import evidence
from well_ops.connectors.base import connect, resolve_wellbore
from well_ops.connectors.drilling_reports.tools import REPORT_DATES, REPORT_DAY
from well_ops.connectors.errors import ToolError
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.redaction import Redactor
from well_ops.settings import Settings


class Verdict(StrEnum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


@dataclass(frozen=True)
class Tolerance:
    absolute: float = 0.0
    relative: float = 0.0  # a share of the recomputed value

    def allows(self, stated: float, expected: float) -> bool:
        return abs(stated - expected) <= self.absolute + self.relative * abs(expected) + 1e-9


# The tolerances of evaluation/RULES.md (a test keeps the two in step). Claim types not listed
# (date, code, quote) must match exactly.
TOLERANCES: dict[ClaimType, Tolerance] = {
    ClaimType.HOURS: Tolerance(absolute=0.25),
    ClaimType.DEPTH_M: Tolerance(absolute=1.0),
    ClaimType.RATE_M_PER_H: Tolerance(relative=0.02),
    ClaimType.HOLE_SIZE_IN: Tolerance(absolute=0.01),
    ClaimType.VOLUME_SM3: Tolerance(relative=0.005),
    ClaimType.COUNT: Tolerance(),
}

Value = int | float | str


@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    verdict: Verdict
    reason: str
    expected: Value | None = None  # the recomputed value, when one was computed
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "verdict": str(self.verdict),
            "reason": self.reason,
            "expected": self.expected,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        return cls(
            data["claim_id"],
            Verdict(data["verdict"]),
            data["reason"],
            data.get("expected"),
            data.get("detail"),
        )


def summary(results: Iterable[ClaimResult]) -> dict[str, int]:
    """Claims per verdict, every verdict listed."""
    counts = Counter(r.verdict for r in results)
    return {str(v): counts[v] for v in Verdict}


class _Fail(Exception):
    """Stops checking one claim with a result."""

    def __init__(self, verdict: Verdict, reason: str, detail: str | None = None) -> None:
        super().__init__(reason)
        self.verdict, self.reason, self.detail = verdict, reason, detail


def _invalid_scope(detail: str) -> _Fail:
    return _Fail(Verdict.UNVERIFIABLE, "invalid_scope", detail)


MONTH = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])")
CODE = re.compile(r"[a-z][a-z ]*[a-z] -- [a-z][a-z /]*[a-z]")


class Scope:
    """A claim's scope keys, read with their expected types."""

    def __init__(self, values: Mapping[str, Scalar], allowed: Iterable[str]) -> None:
        unknown = sorted(set(values) - set(allowed))
        if unknown:
            raise _invalid_scope(f"unknown scope keys: {', '.join(unknown)}")
        self._values = values

    def has(self, name: str) -> bool:
        return self._values.get(name) is not None

    def text(self, name: str) -> str:
        value = self._values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise _invalid_scope(f"{name} must be text")
        return value

    def integer(self, name: str) -> int:
        value = self._values.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise _invalid_scope(f"{name} must be a whole number")
        return value

    def choice(self, name: str, options: Sequence[str]) -> str:
        value = self._values.get(name)
        if value not in options:
            raise _invalid_scope(f"{name} must be one of {', '.join(options)}")
        return str(value)

    def code(self, name: str) -> tuple[str, str]:
        value = self.text(name)
        if not CODE.fullmatch(value):
            raise _invalid_scope(f"{name} must be 'category -- subcategory'")
        category, subcategory = value.split(" -- ")
        return category, subcategory

    def date(self, name: str) -> dt.date:
        try:
            return dt.date.fromisoformat(self.text(name))
        except ValueError:
            raise _invalid_scope(f"{name} must be a yyyy-mm-dd date") from None

    def months(self) -> tuple[dt.date, dt.date]:
        """`month`, or `start` and `end` (inclusive), as first days of months."""
        if self.has("month") and not (self.has("start") or self.has("end")):
            first = last = self._month("month")
        elif self.has("start") and self.has("end") and not self.has("month"):
            first, last = self._month("start"), self._month("end")
        else:
            raise _invalid_scope("give month, or start and end")
        if last < first:
            raise _invalid_scope("end is before start")
        return first, last

    def _month(self, name: str) -> dt.date:
        value = self.text(name)
        if not MONTH.fullmatch(value):
            raise _invalid_scope(f"{name} must be yyyy-mm")
        return dt.date(int(value[:4]), int(value[5:]), 1)


@dataclass(frozen=True)
class Computed:
    value: Value | None  # None: the warehouse holds no value for this metric
    supporting: frozenset[str]  # evidence ids of the rows the value rests on


Row = dict[str, Any]


@dataclass
class _Context:
    cur: duckdb.DuckDBPyConnection
    guard: HeldOutGuard
    redactor: Redactor
    claim: Claim
    cited: list[tuple[evidence.EvidenceId, Row]]

    def wellbore(self, scope: Scope, name: str = "wellbore") -> str:
        text = scope.text(name)
        try:
            key = resolve_wellbore(self.cur, text)
        except ToolError:
            raise _Fail(Verdict.UNSUPPORTED, "wellbore_not_found") from None
        if not self.guard.allows(key):
            raise _Fail(Verdict.UNSUPPORTED, "wellbore_not_available")
        return key

    def rows(self, sql: str, parameters: Sequence[Any]) -> list[tuple[Any, ...]]:
        return self.cur.execute(sql, list(parameters)).fetchall()

    def cited_of(self, kind: str) -> list[tuple[evidence.EvidenceId, Row]]:
        """The cited rows of one evidence kind; any other kind cannot support this metric."""
        return [(eid, row) for eid, row in self.cited if eid.kind == kind]

    def check_cited_wellbore(self, scope: Scope) -> None:
        """With an optional `wellbore` scope, every cited row must belong to that wellbore."""
        if scope.has("wellbore"):
            key = self.wellbore(scope)
            if any(row.get("wellbore_key") != key for _, row in self.cited):
                raise _Fail(Verdict.UNSUPPORTED, "evidence_not_for_claim")


# Relations, as in the connectors.
REPORT = "staging.stg_ddr__report"
ACTIVITY = "staging.stg_ddr__activity"
HOLE_SECTION = "marts.dim_hole_section"
LOST_TIME = "marts.fct_lost_time"
SODIR_WELLBORE = "staging.stg_sodir__wellbore"
MONTHLY = "intermediate.int_production__monthly_attributed"
RECONCILIATION = "marts.fct_production_monthly_reconciliation"
SODIR_FIELD = {
    "sodir_gross": "staging.stg_sodir__field_production_gross_monthly",
    "sodir_net": "staging.stg_sodir__field_production_net_monthly",
}
WORKBOOK_FIELD = "VOLVE"
LOST_TIME_TIERS = ("primary", "possible")
WELLBORE_FLUIDS = ("oil", "gas", "water", "gas_injected", "water_injected")
FIELD_FLUIDS = ("oil", "gas", "water")
FIELD_BASES = ("workbook", "sodir_gross", "sodir_net")


def _id(kind: str, **values: object) -> str:
    return evidence.build(kind, **values)


def _section_id(key: str, number: int) -> str:
    return f"{key}#{number}"


def _section_evidence(key: str, number: int) -> str:
    return _id("ddr:hole-section", wellbore_key=key, section=number)


def _wellbore_evidence(key: str) -> str:
    return _id("well:wellbore", wellbore_key=key)


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


# --- Drilling-report metrics -----------------------------------------------------------------


def _lost_time(ctx: _Context, scope: Scope, *, tiered: bool, column: str) -> Computed:
    key = ctx.wellbore(scope)
    where, parameters = ["wellbore_key = ?"], [key]
    scoped = _wellbore_evidence(key)
    if tiered:
        where.append("tier = ?")
        parameters.append(scope.choice("tier", LOST_TIME_TIERS))
    if scope.has("section"):
        number = scope.integer("section")
        where.append("section_id = ?")
        parameters.append(_section_id(key, number))
        scoped = _section_evidence(key, number)
    if scope.has("code") or not tiered:  # code_hours always names a code
        category, subcategory = scope.code("code")
        where.append("category = ? and subcategory = ?")
        parameters += [category, subcategory]
    rows = ctx.rows(
        f"select section_id, category, subcategory, {column} from {LOST_TIME}"
        f" where {' and '.join(where)}",
        parameters,
    )
    total = sum(r[3] or 0 for r in rows)
    ids = {_id("ddr:lost-time", section_id=s, category=c, subcategory=sc) for s, c, sc, _ in rows}
    return Computed(
        int(total) if column == "activities" else _round(total), frozenset({*ids, scoped})
    )


def lost_hours(ctx: _Context, scope: Scope) -> Computed:
    return _lost_time(ctx, scope, tiered=True, column="hours")


def lost_time_activities(ctx: _Context, scope: Scope) -> Computed:
    return _lost_time(ctx, scope, tiered=True, column="activities")


def code_hours(ctx: _Context, scope: Scope) -> Computed:
    return _lost_time(ctx, scope, tiered=False, column="hours")


def _section_column(column: str) -> Callable[[_Context, Scope], Computed]:
    def compute(ctx: _Context, scope: Scope) -> Computed:
        key = ctx.wellbore(scope)
        number = scope.integer("section")
        rows = ctx.rows(
            f"select {column} from {HOLE_SECTION} where section_id = ?", [_section_id(key, number)]
        )
        if not rows:
            raise _Fail(Verdict.UNSUPPORTED, "section_not_found")
        value = rows[0][0]
        if isinstance(value, float):
            value = _round(value)
        elif isinstance(value, dt.date):
            value = value.isoformat()
        return Computed(value, frozenset({_section_evidence(key, number)}))

    return compute


def section_drilling_rate(ctx: _Context, scope: Scope) -> Computed:
    """New hole over hours coded drilling -- drill, as the drilling_rate tool."""
    key = ctx.wellbore(scope)
    number = scope.integer("section")
    section_id = _section_id(key, number)
    rows = ctx.rows(
        f"""
        select s.new_hole_drilled_m, l.hours
        from {HOLE_SECTION} s
        left join {LOST_TIME} l
          on l.section_id = s.section_id and l.category = 'drilling' and l.subcategory = 'drill'
        where s.section_id = ?
        """,
        [section_id],
    )
    if not rows:
        raise _Fail(Verdict.UNSUPPORTED, "section_not_found")
    new_hole, hours = rows[0]
    ids = {_section_evidence(key, number)}
    if hours is not None:
        ids.add(
            _id("ddr:lost-time", section_id=section_id, category="drilling", subcategory="drill")
        )
    rate = _round(new_hole / hours) if hours and new_hole else None
    return Computed(rate, frozenset(ids))


def activity_duration(ctx: _Context, scope: Scope) -> Computed:
    """The summed duration of the cited activities."""
    ctx.check_cited_wellbore(scope)
    activities = ctx.cited_of("ddr:activity")
    total = sum(row["duration_hours"] or 0 for _, row in activities)
    return Computed(_round(total), frozenset(str(eid) for eid, _ in activities))


def report_md(ctx: _Context, scope: Scope) -> Computed:
    """Measured depth on the report of one operations day, as the report tool."""
    key = ctx.wellbore(scope)
    rows = ctx.rows(
        f"""
        select report_file, md_m from {REPORT}
        where wellbore_key = ? and {REPORT_DAY} = ?
        order by report_file limit 1
        """,
        [key, scope.date("date")],
    )
    if not rows:
        raise _Fail(Verdict.UNSUPPORTED, "report_not_found")
    report_file, md = rows[0]
    return Computed(_round(md), frozenset({_id("ddr:report", report_file=report_file)}))


def deepest_md(ctx: _Context, scope: Scope) -> Computed:
    key = ctx.wellbore(scope)
    rows = ctx.rows(
        f"""
        select report_file, md_m from {REPORT}
        where wellbore_key = ? and md_m = (
            select max(md_m) from {REPORT} where wellbore_key = ?
        )
        """,
        [key, key],
    )
    ids = {_id("ddr:report", report_file=f) for f, _ in rows} | {_wellbore_evidence(key)}
    return Computed(_round(rows[0][1]) if rows else None, frozenset(ids))


def _report_dates(index: int) -> Callable[[_Context, Scope], Computed]:
    """One column of REPORT_DATES: 1 count, 2 first, 3 last, 4 first unflagged, 5 flagged."""

    def compute(ctx: _Context, scope: Scope) -> Computed:
        key = ctx.wellbore(scope)
        rows = ctx.rows(f"select * from ({REPORT_DATES}) where wellbore_key = ?", [key])
        value = rows[0][index] if rows else (0 if index in (1, 5) else None)
        if isinstance(value, dt.date):
            value = value.isoformat()
        return Computed(value, frozenset({_wellbore_evidence(key)}))

    return compute


def _sodir_column(column: str) -> Callable[[_Context, Scope], Computed]:
    """A Sodir wellbore fact; a technical sidetrack takes its parent's, as wellbore_facts."""

    def compute(ctx: _Context, scope: Scope) -> Computed:
        key = ctx.wellbore(scope)
        parent = key.split(":", 1)[0]
        if not ctx.guard.allows(parent):
            raise _Fail(Verdict.UNSUPPORTED, "wellbore_not_available")
        rows = ctx.rows(
            f"""
            select npdid, {column} from {SODIR_WELLBORE}
            where wellbore_key in (?, ?) order by wellbore_key = ? desc limit 1
            """,
            [key, parent, key],
        )
        if not rows:
            raise _Fail(Verdict.UNSUPPORTED, "wellbore_not_in_sodir")
        npdid, value = rows[0]
        if isinstance(value, dt.date):
            value = value.isoformat()
        elif isinstance(value, float):
            value = _round(value)
        return Computed(value, frozenset({_id("sodir:wellbore", npdid=npdid)}))

    return compute


# --- Production metrics ----------------------------------------------------------------------


def wellbore_volume(ctx: _Context, scope: Scope) -> Computed:
    """Monthly sheet volumes by attributed wellbore, summed over the months."""
    key = ctx.wellbore(scope)
    fluid = scope.choice("fluid", WELLBORE_FLUIDS)
    first, last = scope.months()
    rows = ctx.rows(
        f"""
        select published_npdid, month_start, {fluid}_sm3 from {MONTHLY}
        where attributed_wellbore_key = ? and month_start between ? and ?
        """,
        [key, first, last],
    )
    supporting = frozenset(
        _id("prod:monthly", npdid=npdid, month=evidence.month(m)) for npdid, m, _ in rows
    )
    for eid, _ in ctx.cited_of("prod:monthly"):
        if str(eid) in supporting:
            continue
        attributed = ctx.rows(
            f"""
            select attributed_wellbore_key from {MONTHLY}
            where published_npdid = ? and month_start = ?
            """,
            [int(eid.values["npdid"]), _month_date(eid.values["month"])],
        )
        if attributed and attributed[0][0] != key:
            other = str(attributed[0][0])
            raise _Fail(
                Verdict.CONTRADICTED,
                "attributed_to_other_wellbore",
                f"the cited month is attributed to {other}"
                if ctx.guard.allows(other)
                else "the cited month is attributed to another wellbore",
            )
    values = [v for _, _, v in rows if v is not None]
    return Computed(_round(sum(values)) if values else None, supporting)


def field_volume(ctx: _Context, scope: Scope) -> Computed:
    """Field volumes per month on one basis (reconciliation table, Sm3), summed over months."""
    if scope.text("field").strip().upper() != WORKBOOK_FIELD:
        raise _Fail(Verdict.UNVERIFIABLE, "field_not_available")
    fluid = scope.choice("fluid", FIELD_FLUIDS)
    basis = scope.choice("basis", FIELD_BASES)
    first, last = scope.months()
    rows = ctx.rows(
        f"""
        select month_start, {fluid}_{basis}_sm3 from {RECONCILIATION}
        where month_start between ? and ?
        """,
        [first, last],
    )
    ids = {_id("prod:reconciliation", month=evidence.month(m)) for m, _ in rows}
    if basis in SODIR_FIELD:
        kind = "sodir:field-" + basis.removeprefix("sodir_")
        ids |= {
            _id(kind, field_npdid=npdid, month=evidence.month(m))
            for npdid, m in ctx.rows(
                f"""
                select field_npdid, month_start from {SODIR_FIELD[basis]}
                where field_name = ? and month_start between ? and ?
                """,
                [WORKBOOK_FIELD, first, last],
            )
        }
    values = [v for _, v in rows if v is not None]
    return Computed(_round(sum(values)) if values else None, frozenset(ids))


def _month_date(text: str) -> dt.date:
    return dt.date(int(text[:4]), int(text[5:]), 1)


# --- Text metrics ----------------------------------------------------------------------------


def activity_code(ctx: _Context, scope: Scope) -> Computed:
    """The code ('category -- subcategory') of the cited activities."""
    ctx.check_cited_wellbore(scope)
    activities = ctx.cited_of("ddr:activity")
    codes = sorted({f"{row['category']} -- {row['subcategory']}" for _, row in activities})
    return Computed("; ".join(codes) or None, frozenset(str(eid) for eid, _ in activities))


def quote(ctx: _Context, scope: Scope) -> Computed:
    """Text that appears exactly in a text field of a cited row, after redaction."""
    ctx.check_cited_wellbore(scope)
    stated = str(ctx.claim.value)
    for _, row in ctx.cited:
        for value in row.values():
            if isinstance(value, str) and stated in ctx.redactor.redact(value).text:
                return Computed(stated, frozenset(str(eid) for eid, _ in ctx.cited))
    raise _Fail(Verdict.CONTRADICTED, "not_in_evidence")


# --- Registry --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Metric:
    types: frozenset[ClaimType]
    scope: frozenset[str]  # the scope keys the metric accepts
    compute: Callable[[_Context, Scope], Computed]


def _metric(
    types: ClaimType | Iterable[ClaimType], scope: Iterable[str], compute: Callable[..., Computed]
) -> Metric:
    kinds = frozenset({types} if isinstance(types, ClaimType) else types)
    return Metric(kinds, frozenset(scope), compute)


H, M, D, N = ClaimType.HOURS, ClaimType.DEPTH_M, ClaimType.DATE, ClaimType.COUNT
WELLBORE, SECTION = ("wellbore",), ("wellbore", "section")
MONTHS = ("month", "start", "end")

METRICS: dict[str, Metric] = {
    "lost_hours": _metric(H, ("wellbore", "tier", "section", "code"), lost_hours),
    "lost_time_activities": _metric(
        N, ("wellbore", "tier", "section", "code"), lost_time_activities
    ),
    "code_hours": _metric(H, ("wellbore", "code", "section"), code_hours),
    "section_activity_hours": _metric(H, SECTION, _section_column("activity_hours")),
    "section_interruption_hours": _metric(H, SECTION, _section_column("interruption_hours")),
    "activity_duration": _metric(H, WELLBORE, activity_duration),
    "section_start_md": _metric(M, SECTION, _section_column("start_md_m")),
    "section_end_md": _metric(M, SECTION, _section_column("end_md_m")),
    "new_hole_drilled": _metric(M, SECTION, _section_column("new_hole_drilled_m")),
    "report_md": _metric(M, ("wellbore", "date"), report_md),
    "deepest_md": _metric(M, WELLBORE, deepest_md),
    "total_depth": _metric(M, WELLBORE, _sodir_column("total_depth_m")),
    "section_start_date": _metric(D, SECTION, _section_column("start_date_local")),
    "section_end_date": _metric(D, SECTION, _section_column("end_date_local")),
    "first_report_date": _metric(D, WELLBORE, _report_dates(2)),
    "last_report_date": _metric(D, WELLBORE, _report_dates(3)),
    "first_unflagged_report_date": _metric(D, WELLBORE, _report_dates(4)),
    "entry_date": _metric(D, WELLBORE, _sodir_column("entry_date")),
    "completion_date": _metric(D, WELLBORE, _sodir_column("completion_date")),
    "report_count": _metric(N, WELLBORE, _report_dates(1)),
    "flagged_report_count": _metric(N, WELLBORE, _report_dates(5)),
    "section_report_count": _metric(N, SECTION, _section_column("report_count")),
    "section_hole_size": _metric(ClaimType.HOLE_SIZE_IN, SECTION, _section_column("hole_size_in")),
    "section_drilling_rate": _metric(ClaimType.RATE_M_PER_H, SECTION, section_drilling_rate),
    "wellbore_volume": _metric(
        ClaimType.VOLUME_SM3, ("wellbore", "fluid", *MONTHS), wellbore_volume
    ),
    "field_volume": _metric(
        ClaimType.VOLUME_SM3, ("field", "fluid", "basis", *MONTHS), field_volume
    ),
    "activity_code": _metric(ClaimType.CODE, WELLBORE, activity_code),
    "quote": _metric(ClaimType.QUOTE, WELLBORE, quote),
}


# --- Evidence rows ---------------------------------------------------------------------------

WITSML_ID_COLUMNS = {
    "trajectory-station": "station_id",
    "bha-run": "bha_run_id",
    "tubular-component": "component_id",
    "geometry-section": "geometry_section_id",
    "mud-log-interval": "interval_id",
    "rig": "rig_id",
    "message": "message_id",
}


def _where(eid: evidence.EvidenceId) -> tuple[str, list[Any]] | None:
    """The row lookup for an evidence id; None for kinds without a unique row."""
    v = eid.values
    match eid.kind:
        case "rt:log-value":
            return None  # index values repeat within a log, so the id names no single row
        case "ddr:hole-section":
            return "section_id = ?", [f"{v['wellbore_key']}#{v['section']}"]
        case "ddr:activity":
            return "report_file = ? and activity_number = ?", [
                v["report_file"],
                int(v["activity_number"]),
            ]
        case "prod:daily":
            return "npdid = ? and production_date = ?", [
                int(v["npdid"]),
                dt.date.fromisoformat(v["day"]),
            ]
        case "prod:monthly":
            return "npdid = ? and month_start = ?", [int(v["npdid"]), _month_date(v["month"])]
        case "prod:reconciliation":
            return "month_start = ?", [_month_date(v["month"])]
        case "sodir:wellbore":
            return "npdid = ?", [int(v["npdid"])]
        case "sodir:field-net" | "sodir:field-gross":
            return "field_npdid = ? and month_start = ?", [
                int(v["field_npdid"]),
                _month_date(v["month"]),
            ]
    if eid.kind.startswith("witsml:"):
        return f"{WITSML_ID_COLUMNS[eid.kind.removeprefix('witsml:')]} = ?", [v["object_id"]]
    # Every other kind is keyed by columns named as its fields.
    return " and ".join(f"{name} = ?" for name in v), list(v.values())


def fetch(cur: duckdb.DuckDBPyConnection, eid: evidence.EvidenceId) -> Row | None:
    """The warehouse row an evidence id names, or None if there is none."""
    where = _where(eid)
    if where is None:
        raise _Fail(Verdict.UNSUPPORTED, "evidence_not_checkable")
    sql, parameters = where
    rows = cur.execute(f"select * from {eid.relation} where {sql} limit 1", parameters)
    names = [d[0] for d in rows.description]
    found = rows.fetchall()
    return dict(zip(names, found[0], strict=True)) if found else None


# --- The checker -----------------------------------------------------------------------------


class Checker:
    def __init__(
        self, con: duckdb.DuckDBPyConnection, guard: HeldOutGuard, redactor: Redactor
    ) -> None:
        self._con = con
        self.guard = guard
        self.redactor = redactor

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            connect(settings.warehouse_path),
            HeldOutGuard.from_settings(settings),
            Redactor.from_file(settings.redaction_denylist_path),
        )

    def check(self, document: Document) -> list[ClaimResult]:
        """One result per claim, in document order."""
        return [self.check_claim(claim) for claim in document.claims()]

    def check_claim(self, claim: Claim) -> ClaimResult:
        try:
            return self._check(claim)
        except _Fail as fail:
            return ClaimResult(claim.id, fail.verdict, fail.reason, detail=fail.detail)

    def _check(self, claim: Claim) -> ClaimResult:
        metric = METRICS.get(claim.what.metric)
        if metric is None:
            raise _Fail(Verdict.UNVERIFIABLE, "unknown_metric")
        if claim.type not in metric.types:
            raise _Fail(Verdict.UNVERIFIABLE, "metric_not_for_type")
        scope = Scope(claim.what.scope, metric.scope)
        if not claim.evidence_ids:
            raise _Fail(Verdict.UNSUPPORTED, "no_evidence")
        cur = self._con.cursor()
        ctx = _Context(cur, self.guard, self.redactor, claim, self._cited(cur, claim))
        computed = metric.compute(ctx, scope)
        if not {str(eid) for eid, _ in ctx.cited} <= computed.supporting:
            raise _Fail(Verdict.UNSUPPORTED, "evidence_not_for_claim")
        return self._compare(claim, computed)

    def _cited(
        self, cur: duckdb.DuckDBPyConnection, claim: Claim
    ) -> list[tuple[evidence.EvidenceId, Row]]:
        cited = []
        for text in claim.evidence_ids:
            try:
                eid = evidence.parse(text)
            except evidence.EvidenceIdError:
                raise _Fail(Verdict.UNSUPPORTED, "malformed_evidence") from None
            row = fetch(cur, eid)
            if row is None:
                raise _Fail(Verdict.UNSUPPORTED, "unknown_evidence")
            key = row.get("wellbore_key")
            if isinstance(key, str) and not self.guard.allows(key):
                raise _Fail(Verdict.UNSUPPORTED, "wellbore_not_available")
            cited.append((eid, row))
        return cited

    @staticmethod
    def _compare(claim: Claim, computed: Computed) -> ClaimResult:
        expected = computed.value
        if expected is None:
            return ClaimResult(claim.id, Verdict.CONTRADICTED, "no_value")
        tolerance = TOLERANCES.get(claim.type)
        if tolerance is not None and tolerance != Tolerance():
            assert isinstance(claim.value, int | float) and isinstance(expected, int | float)
            ok = tolerance.allows(float(claim.value), float(expected))
            reason = "within_tolerance" if ok else "outside_tolerance"
        elif tolerance is not None:  # counts: exact
            ok = claim.value == expected
            reason = "exact" if ok else "different"
        else:
            ok = str(claim.value) == str(expected)
            reason = "exact" if ok else "different"
        verdict = Verdict.VERIFIED if ok else Verdict.CONTRADICTED
        return ClaimResult(claim.id, verdict, reason, expected)
