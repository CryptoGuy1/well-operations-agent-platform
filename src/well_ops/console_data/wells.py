"""wells.json and wells/<key>.json: Volve wellbores with drilling reports.

Held-out wellbores appear in the console's evaluation and run views only (ADR 0005): wells.json
lists them with key, name and split role, and they get no detail file.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb

from well_ops.connectors.drilling_reports.tools import (
    CAMPAIGN,
    CODES,
    HOLE_SECTION,
    LOST_TIME,
    LOST_TIME_TIERS,
    RATE_LABEL,
    REPORT,
    REPORT_DATES,
    REPORT_DAY,
    REPORT_FLAG,
    WELLBORE,
    section_rate,
)

DEVELOPMENT, HELD_OUT, OUTSIDE = "development", "held_out", "outside_population"
HELD_OUT_NOTE = "Held out for evaluation; see the evaluation runs."
# The activities fct_lost_time is built from, each with its hole section.
ACTIVITY_SECTION = "intermediate.int_ddr__activity_section"

SECTION_COLUMNS = (
    "section_id",
    "section_number",
    "section_label",
    "hole_size_in",
    "hole_size_source",
    "start_date_local",
    "end_date_local",
    "start_md_m",
    "end_md_m",
    "end_tvd_m",
    "casing_shoe_md_m",
    "report_count",
    "inferred_share",
    "operation_phase",
    "activity_hours",
    "interruption_hours",
    "new_hole_drilled_m",
)
CAMPAIGN_COLUMNS = (
    "campaign_id",
    "campaign_number",
    "start_date_local",
    "end_date_local",
    "span_days",
    "active_days",
    "report_count",
    "operation_phase",
)


def split_roles(splits_path: Path) -> dict[str, str]:
    """Split role per wellbore key of the evaluation population (evaluation/splits.json)."""
    data = json.loads(splits_path.read_text(encoding="utf-8"))
    roles = {str(e["key"]): DEVELOPMENT for e in data[DEVELOPMENT]}
    roles.update({str(e["key"]): HELD_OUT for e in data[HELD_OUT]})
    return roles


def held_out_keys(con: duckdb.DuckDBPyConnection, roles: dict[str, str]) -> frozenset[str]:
    """Held out by the splits file or by the warehouse flag; either is enough."""
    rows = con.execute(f"select wellbore_key from {WELLBORE} where is_heldout").fetchall()
    flagged = {str(k) for (k,) in rows}
    return frozenset(flagged | {k for k, r in roles.items() if r == HELD_OUT})


def _records(cur: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    names = [d[0] for d in cur.description or ()]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def index(
    con: duckdb.DuckDBPyConnection, roles: dict[str, str], held_out: frozenset[str]
) -> list[dict[str, Any]]:
    """One entry per Volve wellbore with reports, sorted by name and key."""
    rows = _records(
        con.execute(
            f"""
            select r.wellbore_key, w.wellbore_name, r.report_count, r.first_day,
                   r.last_day, r.first_unflagged_day, r.report_span_days, r.active_days
            from ({REPORT_DATES}) r join {WELLBORE} w using (wellbore_key)
            where upper(w.field_name) = 'VOLVE'
            order by w.wellbore_name, r.wellbore_key
            """
        )
    )
    campaigns = dict(
        con.execute(f"select wellbore_key, count(*) from {CAMPAIGN} group by 1").fetchall()
    )
    flags: dict[str, dict[str, int]] = defaultdict(dict)
    for key, flag, n in con.execute(
        f"select wellbore_key, flag, count(*) from {REPORT_FLAG} group by 1, 2"
    ).fetchall():
        flags[key][flag] = n
    entries = []
    for r in rows:
        key = r["wellbore_key"]
        if key in held_out:
            entries.append(
                {
                    "key": key,
                    "name": r["wellbore_name"],
                    "split": HELD_OUT,
                    "detail": False,
                    "note": HELD_OUT_NOTE,
                }
            )
            continue
        entries.append(
            {
                "key": key,
                "name": r["wellbore_name"],
                "split": roles.get(key, OUTSIDE),
                "detail": True,
                "report_count": r["report_count"],
                "first_report_date": r["first_day"],
                "last_report_date": r["last_day"],
                "first_unflagged_report_date": r["first_unflagged_day"],
                "report_span_days": _round(r["report_span_days"]),
                "active_days": r["active_days"],
                "campaigns": campaigns.get(key, 0),
                "flags": dict(sorted(flags[key].items())),
            }
        )
    return entries


def _lost_time(con: duckdb.DuckDBPyConnection, key: str) -> dict[str, Any]:
    rows = _records(
        con.execute(
            f"""
            select section_id, tier, category || ' -- ' || subcategory as cause,
                   sum(hours) as hours, sum(activities) as activities
            from {LOST_TIME} where wellbore_key = ?
            group by all order by section_id, tier, cause
            """,
            [key],
        )
    )

    def total(*by: str) -> list[dict[str, Any]]:
        sums: dict[tuple[Any, ...], list[float]] = defaultdict(lambda: [0.0, 0])
        for r in rows:
            s = sums[tuple(r[b] for b in by)]
            s[0] += r["hours"] or 0.0
            s[1] += r["activities"] or 0
        return [
            {**dict(zip(by, k, strict=True)), "hours": _round(h), "activities": int(n)}
            for k, (h, n) in sorted(sums.items())
        ]

    tiers = ", ".join(f"'{t}'" for t in LOST_TIME_TIERS)
    by_day = _records(
        con.execute(
            f"""
            select d.day as date, c.tier, sum(a.duration_hours) as hours
            from {ACTIVITY_SECTION} a
            join (select report_file, {REPORT_DAY} as day from {REPORT}) d using (report_file)
            join {CODES} c on c.category = a.category and c.subcategory = a.subcategory
            where a.wellbore_key = ? and c.tier in ({tiers})
            group by all order by date, c.tier
            """,
            [key],
        )
    )
    return {
        "rows": [
            {**r, "hours": _round(r["hours"]), "activities": int(r["activities"])} for r in rows
        ],
        "by_section": total("section_id", "tier"),
        "by_tier": total("tier"),
        "by_cause": total("tier", "cause"),
        # Primary and possible lost time per operations day of the activity's report.
        "by_day": [{**r, "hours": _round(r["hours"])} for r in by_day],
    }


def _sections(con: duckdb.DuckDBPyConnection, key: str) -> list[dict[str, Any]]:
    """Hole sections with the drilling rate as the drilling_rate tool gives it, or its reason."""
    sections = _records(
        con.execute(
            f"""
            select {", ".join(f"s.{c}" for c in SECTION_COLUMNS)}, l.hours as drill_hours
            from {HOLE_SECTION} s
            left join {LOST_TIME} l
              on l.section_id = s.section_id and l.category = 'drilling'
             and l.subcategory = 'drill'
            where s.wellbore_key = ?
            order by s.section_number
            """,
            [key],
        )
    )
    for s in sections:
        s["rate_m_per_h"], s["rate_reason"] = section_rate(
            s["new_hole_drilled_m"], s["drill_hours"]
        )
        s["drill_hours"] = _round(s["drill_hours"])
    return sections


def _depth_time(con: duckdb.DuckDBPyConnection, key: str) -> list[dict[str, Any]]:
    """One point per report, in report order: its operations day, its measured depth and the
    deepest depth reported so far, with the report's flags."""
    rows = con.execute(
        f"""
        select r.report_file, {REPORT_DAY} as day, r.md_m,
               list(f.flag order by f.flag) filter (where f.flag is not null) as flags
        from {REPORT} r left join {REPORT_FLAG} f using (report_file)
        where r.wellbore_key = ?
        group by r.report_file, day, r.md_m
        order by day, r.report_file
        """,
        [key],
    ).fetchall()
    points, deepest = [], None
    for report_file, day, md, flags in rows:
        if md is not None:
            deepest = md if deepest is None else max(deepest, md)
        points.append(
            {
                "report_file": report_file,
                "date": day,
                "md_m": _round(md, 1),
                "deepest_md_m": _round(deepest, 1),
                "flags": flags or [],
            }
        )
    return points


def detail(con: duckdb.DuckDBPyConnection, key: str, name: str) -> dict[str, Any]:
    sections = _sections(con, key)
    campaigns = _records(
        con.execute(
            f"select {', '.join(CAMPAIGN_COLUMNS)} from {CAMPAIGN} where wellbore_key = ? "
            "order by campaign_number",
            [key],
        )
    )
    flags = _records(
        con.execute(
            f"""
            select f.flag, count(*) as reports, min({REPORT_DAY}) as first_date,
                   max({REPORT_DAY}) as last_date
            from {REPORT_FLAG} f join {REPORT} r using (report_file)
            where f.wellbore_key = ? group by f.flag order by f.flag
            """,
            [key],
        )
    )
    return {
        "key": key,
        "name": name,
        "hole_sections": sections,
        "rate_label": RATE_LABEL,
        "campaigns": campaigns,
        "lost_time": _lost_time(con, key),
        "depth_time": _depth_time(con, key),
        "flags": flags,
    }


def file_name(key: str) -> str:
    """A wellbore key as a file name: `:` is not portable, so 9001:T2 becomes 9001-T2."""
    return key.replace(":", "-")


def export(
    con: duckdb.DuckDBPyConnection, roles: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """wells.json and the detail files by file name; never a detail file for a held-out key."""
    held_out = held_out_keys(con, roles)
    entries = index(con, roles, held_out)
    details = {
        f"wells/{file_name(e['key'])}.json": detail(con, e["key"], e["name"])
        for e in entries
        if e["detail"]
    }
    for e in entries:
        e["file"] = f"wells/{file_name(e['key'])}.json" if e["detail"] else None
    return entries, details
