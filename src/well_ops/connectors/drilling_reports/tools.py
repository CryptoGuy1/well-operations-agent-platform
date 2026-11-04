"""Drilling-report tools: fixed, parameterised queries over the DDR views and marts.

Each method resolves the wellbore, applies the held-out guard, runs one fixed query, attaches an
evidence id to every row, and returns an envelope with the row cap and redaction applied
(`well_ops.connectors.base.envelope`). The MCP server in `server.py` only registers these methods.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Literal

from well_ops.connectors import evidence
from well_ops.connectors.base import (
    ConnectorTools,
    field_name,
    invalid_arguments,
    iso,
    local_iso,
    local_sql,
    utc_iso,
)
from well_ops.connectors.errors import ToolError

Category = Literal[
    "completion",
    "drilling",
    "formation evaluation",
    "interruption",
    "moving",
    "plug abandon",
    "workover",
]
GroupBy = Literal["section", "code", "tier"]

LOST_TIME_TIERS = ("primary", "possible")
RATE_LABEL = "average rate while coded drilling -- drill"

# A report covers one operations day from local midnight; its day is the local start date.
REPORT_DAY = f"cast({local_sql('start_utc', 'start_offset')} as date)"

REPORT = "staging.stg_ddr__report"
ACTIVITY = "staging.stg_ddr__activity"
REPORT_FLAG = "intermediate.int_ddr__report_flag"
HOLE_SECTION = "marts.dim_hole_section"
CAMPAIGN = "marts.dim_campaign"
LOST_TIME = "marts.fct_lost_time"
WELLBORE = "marts.dim_wellbore"
CODES = "reference.lost_time_codes"

# Reports dated before the spud date: placeholder or pre-spud dates in the source (ADR 0002 D4).
SPUD_FLAGS = ("before_report_spud", "before_sodir_spud")

# Report counts and dates per wellbore; the published dates are kept, and the first report date
# without a spud-date flag is given beside them. report_span_days runs from the start of the first
# report without a spud-date flag to the end of the last report, in days of 24 h; active_days
# counts the operations days of reports without such a flag.
REPORT_DATES = f"""
    select wellbore_key, count(*) as report_count, min(day) as first_day, max(day) as last_day,
           min(day) filter (where not spud_flagged) as first_unflagged_day,
           count(*) filter (where spud_flagged) as flagged_count,
           epoch(max(end_utc) - min(start_utc) filter (where not spud_flagged)) / 86400.0
               as report_span_days,
           count(distinct day) filter (where not spud_flagged) as active_days
    from (
        select wellbore_key, start_utc, end_utc, {REPORT_DAY} as day,
               report_file in (
                   select report_file from {REPORT_FLAG} where flag in {SPUD_FLAGS}
               ) as spud_flagged
        from {REPORT}
    )
    group by wellbore_key
"""

ACTIVITY_COLUMNS = """
    a.report_file, a.activity_number, a.start_utc, a.start_offset, a.end_utc, a.end_offset,
    a.duration_hours, a.md_m, a.phase, a.category, a.subcategory,
    coalesce(c.tier, 'none') as lost_time_tier, a.state, a.state_detail, a.comments
"""


def report_not_found() -> ToolError:
    return ToolError(
        "report_not_found",
        "No drilling report for this wellbore covers this date.",
        "Use well_overview for the wellbore's first and last report dates.",
    )


def _hours(value: float | None) -> float:
    return round(value or 0.0, 2)


def _share(part: float | None, total: float | None) -> float | None:
    """`part` as a percentage of `total`, to 0.01; None without a total."""
    return round(100 * (part or 0.0) / total, 2) if total else None


def _activity(r: Sequence[Any]) -> dict[str, Any]:
    """One row selected with ACTIVITY_COLUMNS."""
    return {
        "evidence_id": evidence.build("ddr:activity", report_file=r[0], activity_number=r[1]),
        "start": local_iso(r[2], r[3]),
        "end": local_iso(r[4], r[5]),
        "duration_hours": r[6],
        "md_m": r[7],
        "phase": r[8],
        "code": f"{r[9]} -- {r[10]}",
        "lost_time_tier": r[11],
        "state": r[12],
        "state_detail": r[13],
        "comments": r[14],
    }


def _section_evidence(wellbore_key: str, section_id: str) -> str:
    return evidence.build(
        "ddr:hole-section", wellbore_key=wellbore_key, section=section_id.split("#", 1)[1]
    )


def _lost_time_evidence(section_id: str, category: str, subcategory: str) -> str:
    return evidence.build(
        "ddr:lost-time", section_id=section_id, category=category, subcategory=subcategory
    )


class DrillingReports(ConnectorTools):
    def list_wellbores(self, field: str = "VOLVE") -> dict[str, Any]:
        name = field_name(field)
        cur = self._cursor()
        rows = cur.execute(
            f"""
            select r.wellbore_key, w.wellbore_name, r.report_count, r.first_day, r.last_day,
                   r.first_unflagged_day, r.flagged_count
            from ({REPORT_DATES}) r join {WELLBORE} w using (wellbore_key)
            where upper(w.field_name) = ?
            order by w.wellbore_name, r.wellbore_key
            """,
            [name],
        ).fetchall()
        visible = self.guard.visible(rows, key=lambda row: str(row[0]))
        return self._envelope(
            [REPORT, REPORT_FLAG, WELLBORE],
            {"field": name},
            [
                {
                    "evidence_id": evidence.build("well:wellbore", wellbore_key=key),
                    "wellbore_key": key,
                    "wellbore_name": wellbore_name,
                    "report_count": count,
                    "first_report_date": iso(first),
                    "last_report_date": iso(last),
                    "first_unflagged_report_date": iso(first_unflagged),
                    "flagged_report_count": flagged,
                }
                for key, wellbore_name, count, first, last, first_unflagged, flagged in visible
            ],
        )

    def well_overview(self, wellbore_key: str) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        wellbore_name, field_name = cur.execute(
            f"select wellbore_name, field_name from {WELLBORE} where wellbore_key = ?", [key]
        ).fetchall()[0]
        dates = cur.execute(
            f"select report_count, first_day, last_day, first_unflagged_day, flagged_count,"
            f" report_span_days, active_days from ({REPORT_DATES}) where wellbore_key = ?",
            [key],
        ).fetchall()
        count, first, last, first_unflagged, flagged, span, active = (
            dates[0] if dates else (0, None, None, None, 0, None, 0)
        )
        campaigns = cur.execute(
            f"""
            select campaign_number, start_date_local, end_date_local, span_days, active_days,
                   operation_phase
            from {CAMPAIGN} where wellbore_key = ? order by campaign_number
            """,
            [key],
        ).fetchall()
        total = cur.execute(
            f"select coalesce(sum(activity_hours), 0) from {HOLE_SECTION} where wellbore_key = ?",
            [key],
        ).fetchall()[0][0]
        lost = dict(
            cur.execute(
                f"select tier, sum(hours) from {LOST_TIME}"
                " where wellbore_key = ? and tier in ('primary', 'possible') group by tier",
                [key],
            ).fetchall()
        )
        deepest = cur.execute(
            f"""
            select report_file, md_m, tvd_m from {REPORT}
            where wellbore_key = ? and md_m is not null
            order by md_m desc, start_utc, report_file
            limit 1
            """,
            [key],
        ).fetchall()
        flags = cur.execute(
            f"""
            select flag, count(distinct report_file) from {REPORT_FLAG}
            where wellbore_key = ? group by flag order by flag
            """,
            [key],
        ).fetchall()
        row = {
            "evidence_id": evidence.build("well:wellbore", wellbore_key=key),
            "wellbore_key": key,
            "wellbore_name": wellbore_name,
            "field_name": field_name,
            "report_count": count,
            "first_report_date": iso(first),
            "last_report_date": iso(last),
            "first_unflagged_report_date": iso(first_unflagged),
            "flagged_report_count": flagged,
            "report_span_days": None if span is None else round(span, 2),
            "active_days": active,
            "total_activity_hours": _hours(total),
            **{f"{t}_lost_hours": _hours(lost.get(t)) for t in LOST_TIME_TIERS},
            **{f"{t}_lost_share_pct": _share(lost.get(t), total) for t in LOST_TIME_TIERS},
            "deepest_md_m": deepest[0][1] if deepest else None,
            "deepest_tvd_m": deepest[0][2] if deepest else None,
            "deepest_md_evidence_id": (
                evidence.build("ddr:report", report_file=deepest[0][0]) if deepest else None
            ),
            "flagged_reports": [{"flag": flag, "reports": n} for flag, n in flags],
            "campaigns": [
                {
                    "evidence_id": evidence.build("ddr:campaign", wellbore_key=key, campaign=n),
                    "campaign": int(n),
                    "start_date_local": iso(start),
                    "end_date_local": iso(end),
                    "span_days": round(days, 2),
                    "active_days": int(active_days),
                    "operation_phase": phase,
                }
                for n, start, end, days, active_days, phase in campaigns
            ],
        }
        return self._envelope(
            [CAMPAIGN, HOLE_SECTION, LOST_TIME, REPORT, REPORT_FLAG, WELLBORE],
            {"wellbore_key": key},
            [row],
        )

    def hole_sections(self, wellbore_key: str) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        rows = cur.execute(
            f"""
            select section_id, section_number, section_label, hole_size_in, hole_size_source,
                   operation_phase, start_utc, end_utc, stated_start_utc, start_md_m, end_md_m,
                   new_hole_drilled_m, report_count, inferred_share, activity_hours,
                   interruption_hours, start_date_local, end_date_local, start_casing_shoe_md_m,
                   casing_shoe_md_m, end_tvd_m
            from {HOLE_SECTION} where wellbore_key = ? order by section_number
            """,
            [key],
        ).fetchall()
        return self._envelope(
            [HOLE_SECTION],
            {"wellbore_key": key},
            [
                {
                    "evidence_id": _section_evidence(key, r[0]),
                    "section_number": int(r[1]),
                    "section_label": r[2],
                    "hole_size_in": r[3],
                    "hole_size_source": r[4],
                    "operation_phase": r[5],
                    "start_utc": utc_iso(r[6]),
                    "end_utc": utc_iso(r[7]),
                    "start_date_local": iso(r[16]),
                    "end_date_local": iso(r[17]),
                    "stated_start_utc": utc_iso(r[8]),
                    "start_md_m": r[9],
                    "end_md_m": r[10],
                    "end_tvd_m": r[20],
                    "start_casing_shoe_md_m": r[18],
                    "casing_shoe_md_m": r[19],
                    "new_hole_drilled_m": r[11],
                    "report_count": r[12],
                    "inferred_share": r[13],
                    "activity_hours": r[14],
                    "interruption_hours": r[15],
                }
                for r in rows
            ],
        )

    def lost_time(self, wellbore_key: str, group_by: GroupBy = "section") -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        base = cur.execute(
            f"""
            select s.section_number, l.section_id, l.section_label, l.hole_size_in,
                   l.category, l.subcategory, l.tier, l.hours, l.activities, s.activity_hours
            from {LOST_TIME} l left join {HOLE_SECTION} s using (section_id)
            where l.wellbore_key = ? and l.tier in ('primary', 'possible')
            order by s.section_number, l.category, l.subcategory
            """,
            [key],
        ).fetchall()
        groups: dict[tuple[Any, ...], list[tuple[Any, ...]]] = defaultdict(list)
        for record in base:
            number, _, label, size, category, sub, tier = record[:7]
            if group_by == "section":
                group: tuple[Any, ...] = (number, label, size)
            elif group_by == "code":
                group = (f"{category} -- {sub}", tier)
            else:
                group = (LOST_TIME_TIERS.index(tier), tier)
            groups[group].append(record)

        out = []
        for group in sorted(groups, key=lambda g: tuple((x is None, x) for x in g)):
            members = groups[group]
            hours = {t: sum(m[7] for m in members if m[6] == t) for t in LOST_TIME_TIERS}
            row: dict[str, Any]
            if group_by == "section":
                row = {
                    "section_number": int(group[0]) if group[0] is not None else None,
                    "section_label": group[1],
                    "hole_size_in": group[2],
                    "primary_hours": _hours(hours["primary"]),
                    "possible_hours": _hours(hours["possible"]),
                    # Shares of the section's activity hours.
                    "primary_share_pct": _share(hours["primary"], members[0][9]),
                    "possible_share_pct": _share(hours["possible"], members[0][9]),
                }
            elif group_by == "code":
                row = {"code": group[0], "tier": group[1]}
            else:
                row = {"tier": group[1]}
            row["hours"] = _hours(sum(hours.values()))
            row["activities"] = int(sum(m[8] for m in members))
            row["evidence_ids"] = [_lost_time_evidence(m[1], m[4], m[5]) for m in members]
            out.append(row)
        return self._envelope(
            [HOLE_SECTION, LOST_TIME], {"wellbore_key": key, "group_by": group_by}, out
        )

    def activities(
        self,
        wellbore_key: str,
        start: dt.date,
        end: dt.date,
        category: Category | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        if end < start:
            raise invalid_arguments(["end"])
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        cap = min(limit, self.row_cap)
        rows = cur.execute(
            f"""
            select {ACTIVITY_COLUMNS}, count(*) over () as matched
            from {ACTIVITY} a left join {CODES} c using (category, subcategory)
            where a.wellbore_key = ?
              and cast({local_sql("a.start_utc", "a.start_offset")} as date) between ? and ?
              and (cast(? as varchar) is null or a.category = ?)
            order by a.start_utc, a.report_file, a.activity_number
            limit ?
            """,
            [key, start, end, category, category, cap],
        ).fetchall()
        return self._envelope(
            [ACTIVITY, CODES],
            {
                "wellbore_key": key,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "category": category,
                "limit": cap,
            },
            [_activity(r) for r in rows],
            cap=cap,
            matched=rows[0][15] if rows else 0,
        )

    def report(self, wellbore_key: str, date: dt.date) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        found = cur.execute(
            f"""
            select report_file, start_utc, start_offset, end_utc, end_offset, md_m, tvd_m,
                   md_planned_m, dist_drill_m, dia_hole_in, md_dia_hole_start_m, dia_pilot_in,
                   md_csg_last_m, tvd_csg_last_m, md_kickoff_m, md_plug_top_m, elev_kelly_m,
                   water_depth_m, activities
            from {REPORT} where wellbore_key = ? and {REPORT_DAY} = ?
            order by report_file
            limit 1
            """,
            [key, date],
        ).fetchall()
        if not found:
            raise report_not_found()
        r = found[0]
        flags = cur.execute(
            f"select flag, detail from {REPORT_FLAG} where report_file = ? order by flag, detail",
            [r[0]],
        ).fetchall()
        activities = cur.execute(
            f"""
            select {ACTIVITY_COLUMNS}
            from {ACTIVITY} a left join {CODES} c using (category, subcategory)
            where a.report_file = ?
            order by a.start_utc, a.activity_number
            """,
            [r[0]],
        ).fetchall()
        report = {
            "evidence_id": evidence.build("ddr:report", report_file=r[0]),
            "operations_day": date.isoformat(),
            "start": local_iso(r[1], r[2]),
            "end": local_iso(r[3], r[4]),
            "md_m": r[5],
            "tvd_m": r[6],
            "md_planned_m": r[7],
            "dist_drill_m": r[8],
            "dia_hole_in": r[9],
            "md_dia_hole_start_m": r[10],
            "dia_pilot_in": r[11],
            "md_csg_last_m": r[12],
            "tvd_csg_last_m": r[13],
            "md_kickoff_m": r[14],
            "md_plug_top_m": r[15],
            "elev_kelly_m": r[16],
            "water_depth_m": r[17],
            "activity_count": r[18],
            "flags": [{"flag": flag, "detail": detail} for flag, detail in flags],
        }
        return self._envelope(
            [ACTIVITY, CODES, REPORT, REPORT_FLAG],
            {"wellbore_key": key, "date": date.isoformat()},
            [_activity(a) for a in activities],
            extra={"report": report},
        )

    def drilling_rate(self, wellbore_key: str) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        rows = cur.execute(
            f"""
            select s.section_id, s.section_number, s.section_label, s.hole_size_in,
                   s.operation_phase, s.new_hole_drilled_m, l.hours
            from {HOLE_SECTION} s
            left join {LOST_TIME} l
              on l.section_id = s.section_id and l.category = 'drilling'
             and l.subcategory = 'drill'
            where s.wellbore_key = ?
            order by s.section_number
            """,
            [key],
        ).fetchall()
        out = []
        for section_id, number, label, size, phase, new_hole, hours in rows:
            ids = [_section_evidence(key, section_id)]
            if hours is not None:
                ids.append(_lost_time_evidence(section_id, "drilling", "drill"))
            if not hours:
                rate, reason = None, "no_drilling_hours"
            elif not new_hole:
                rate, reason = None, "no_new_hole"
            else:
                rate, reason = round(new_hole / hours, 2), None
            out.append(
                {
                    "section_number": int(number),
                    "section_label": label,
                    "hole_size_in": size,
                    "operation_phase": phase,
                    "new_hole_drilled_m": new_hole,
                    "drill_hours": _hours(hours),
                    "rate_m_per_h": rate,
                    "rate_reason": reason,
                    "rate_label": RATE_LABEL,
                    "evidence_ids": ids,
                }
            )
        return self._envelope([HOLE_SECTION, LOST_TIME], {"wellbore_key": key}, out)
