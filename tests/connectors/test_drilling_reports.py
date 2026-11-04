"""Drilling-report server tests on a tiny synthetic warehouse (fictional wellbores and names)."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pytest
from mcp.client.client import Client

from well_ops.connectors.base import ConnectorServer, connect
from well_ops.connectors.drilling_reports.server import build_server
from well_ops.connectors.drilling_reports.tools import RATE_LABEL, DrillingReports
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.redaction import Redactor

T2 = "9001:T2"
HELD_OUT = "9002"
R1 = "XX_1_A_1_T2_2020_01_02.xml"
R2 = "XX_1_A_1_T2_2020_01_03.xml"

SCHEMA = """
create schema staging; create schema intermediate; create schema marts; create schema reference;
create table marts.dim_wellbore (wellbore_key varchar, wellbore_name varchar, field_name varchar);
create table staging.stg_identifiers__wellbore_alias (
    normalised_name varchar, wellbore_key varchar, status varchar);
create table staging.stg_ddr__report (
    report_file varchar, wellbore_key varchar, start_utc timestamp, start_offset varchar,
    end_utc timestamp, end_offset varchar, md_m double, tvd_m double, md_planned_m double,
    dist_drill_m double, dia_hole_in double, md_dia_hole_start_m double, dia_pilot_in double,
    md_csg_last_m double, tvd_csg_last_m double, md_kickoff_m double, md_plug_top_m double,
    elev_kelly_m double, water_depth_m double, activities integer);
create table staging.stg_ddr__activity (
    report_file varchar, activity_number integer, wellbore_key varchar, start_utc timestamp,
    start_offset varchar, end_utc timestamp, end_offset varchar, duration_hours double,
    md_m double, phase varchar, category varchar, subcategory varchar, state varchar,
    state_detail varchar, comments varchar);
create table intermediate.int_ddr__report_flag (
    report_file varchar, wellbore_key varchar, flag varchar, detail varchar);
create table reference.lost_time_codes (category varchar, subcategory varchar, tier varchar);
create table marts.dim_hole_section (
    section_id varchar, wellbore_key varchar, section_number hugeint, section_label varchar,
    hole_size_in double, hole_size_source varchar, start_utc timestamp, end_utc timestamp,
    stated_start_utc timestamp, start_md_m double, end_md_m double, report_count bigint,
    inferred_share double, operation_phase varchar, activity_hours double,
    interruption_hours double, new_hole_drilled_m double, bit_size_evidence_in double,
    start_date_local date, end_date_local date);
create table marts.fct_lost_time (
    wellbore_key varchar, section_id varchar, section_label varchar, hole_size_in double,
    category varchar, subcategory varchar, tier varchar, hours double, activities bigint);
"""


def _report(file: str, key: str, start: str, md: float) -> tuple[Any, ...]:
    begin = datetime.fromisoformat(start)
    end = begin + timedelta(days=1)
    return (file, key, begin, "+01:00", end, "+01:00", md, md - 10, None, 500.0, 12.25,
            None, None, 400.0, None, None, None, 30.0, 90.0, 3)  # fmt: skip


def _activity(file: str, n: int, key: str, start: str, hours: float, code: str, comment: str
              ) -> tuple[Any, ...]:  # fmt: skip
    category, sub = code.split(" -- ")
    begin = datetime.fromisoformat(start)
    return (file, n, key, begin, "+01:00", begin, "+01:00", hours, 1000.0, "drilling", category,
            sub, "ok", "success", comment)  # fmt: skip


def _section(n: int, label: str, size: float | None, new_hole: float) -> tuple[Any, ...]:
    return (f"{T2}#{n}", T2, n, label, size, "report" if size else "unknown",
            datetime(2020, 1, n), datetime(2020, 1, n + 1), None, 500.0, 1000.0, 1, 0.0,
            "drilling", 20.0, 6.0, new_hole, None, date(2020, 1, n), date(2020, 1, n))  # fmt: skip


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    path = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(path))
    con.execute(SCHEMA)
    con.executemany(
        "insert into marts.dim_wellbore values (?, ?, ?)",
        [("9001", "XX/1-A-1", "TESTFIELD"), (T2, "XX/1-A-1 T2", "TESTFIELD"),
         (HELD_OUT, "XX/1-A-2", "TESTFIELD"), ("9003", "XX/2-B-1", "OTHERFIELD")],
    )  # fmt: skip
    con.execute(
        "insert into staging.stg_identifiers__wellbore_alias values ('XX/1-A-1 T2', ?, 'wellbore')",
        [T2],
    )
    con.executemany(
        "insert into staging.stg_ddr__report values"
        " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [_report(R1, T2, "2019-12-31T23:00", 1000.0), _report(R2, T2, "2020-01-01T23:00", 1500.0),
         _report("XX_1_A_2_2020_01_02.xml", HELD_OUT, "2019-12-31T23:00", 800.0),
         _report("XX_1_A_1_2019_06_02.xml", "9001", "2019-05-31T23:00", 300.0)],
    )  # fmt: skip
    con.executemany(
        "insert into staging.stg_ddr__activity values"
        " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [_activity(R1, 1, T2, "2019-12-31T23:00", 10.0, "drilling -- drill",
                   "Drilled to 1000 m. Called Alex Placeholder on tel 12345678."),
         _activity(R1, 2, T2, "2020-01-01T09:00", 4.0, "interruption -- repair", "Repaired pump."),
         _activity(R1, 3, T2, "2020-01-01T13:00", 2.0, "interruption -- maintain", "Serviced."),
         _activity(R2, 1, T2, "2020-01-01T23:00", 12.0, "drilling -- drill", "Drilled ahead."),
         _activity(R2, 2, T2, "2020-01-02T11:00", 6.0, "drilling -- trip", "Tripped out.")],
    )  # fmt: skip
    con.execute(
        "insert into intermediate.int_ddr__report_flag values"
        f" ('{R2}', '{T2}', 'depth_not_recorded', 'md missing on one activity'),"
        f" ('{R1}', '{T2}', 'before_sodir_spud', 'dated before spud')"
    )
    con.execute(
        "insert into reference.lost_time_codes values ('interruption', 'repair', 'primary'),"
        " ('interruption', 'maintain', 'possible')"
    )
    con.executemany(
        "insert into marts.dim_hole_section values"
        " (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            _section(1, "12.25 in", 12.25, 500.0),
            _section(2, "hole size unknown", None, 0.0),
            _section(3, "8.5 in", 8.5, 300.0),
        ],
    )
    con.executemany(
        "insert into marts.fct_lost_time values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(T2, f"{T2}#1", "12.25 in", 12.25, "drilling", "drill", "none", 10.0, 1),
         (T2, f"{T2}#1", "12.25 in", 12.25, "interruption", "repair", "primary", 4.0, 1),
         (T2, f"{T2}#1", "12.25 in", 12.25, "interruption", "maintain", "possible", 2.0, 1),
         (T2, f"{T2}#2", "hole size unknown", None, "drilling", "drill", "none", 12.0, 1),
         (T2, f"{T2}#2", "hole size unknown", None, "drilling", "trip", "none", 6.0, 1)],
    )  # fmt: skip
    con.close()
    return path


def _server(warehouse: Path, evaluation_mode: bool = False, row_cap: int = 200) -> ConnectorServer:
    tools = DrillingReports(
        connect(warehouse),
        HeldOutGuard([HELD_OUT], evaluation_mode),
        Redactor(["Alex Placeholder"]),
        row_cap,
    )
    return build_server(tools)


def call(server: ConnectorServer, name: str, **arguments: Any) -> tuple[bool, dict[str, Any]]:
    async def run() -> tuple[bool, dict[str, Any]]:
        async with Client(server) as client:
            result = await client.call_tool(name, arguments)
        assert result.structured_content is not None
        return bool(result.is_error), result.structured_content

    return asyncio.run(run())


def ok(server: ConnectorServer, name: str, **arguments: Any) -> dict[str, Any]:
    is_error, body = call(server, name, **arguments)
    assert not is_error, body
    return body


def test_tools_are_listed_read_only(warehouse: Path) -> None:
    async def run() -> list[Any]:
        async with Client(_server(warehouse)) as client:
            return (await client.list_tools()).tools

    tools = asyncio.run(run())
    assert sorted(t.name for t in tools) == [
        "activities",
        "drilling_rate",
        "hole_sections",
        "list_wellbores",
        "lost_time",
        "report",
        "well_overview",
    ]
    assert all(t.annotations and t.annotations.read_only_hint for t in tools)
    assert all(t.description for t in tools)


def test_list_wellbores_hides_held_out_outside_evaluation_mode(warehouse: Path) -> None:
    body = ok(_server(warehouse), "list_wellbores", field="testfield")
    assert [r["wellbore_key"] for r in body["rows"]] == ["9001", T2]
    t2 = body["rows"][1]
    assert t2["evidence_id"] == f"well:wellbore:{T2}"
    assert (t2["report_count"], t2["first_report_date"], t2["last_report_date"]) == (
        2,
        "2020-01-01",
        "2020-01-02",
    )
    assert (t2["first_unflagged_report_date"], t2["flagged_report_count"]) == ("2020-01-02", 1)
    unflagged = body["rows"][0]
    assert (unflagged["first_unflagged_report_date"], unflagged["flagged_report_count"]) == (
        unflagged["first_report_date"],
        0,
    )
    assert body["parameters"] == {"field": "TESTFIELD"}

    evaluation = ok(_server(warehouse, evaluation_mode=True), "list_wellbores", field="TESTFIELD")
    assert HELD_OUT in [r["wellbore_key"] for r in evaluation["rows"]]


def test_well_overview_resolves_names(warehouse: Path) -> None:
    body = ok(_server(warehouse), "well_overview", wellbore_key="NO XX/1-A-1 T2")
    (row,) = body["rows"]
    assert body["parameters"] == {"wellbore_key": T2}
    assert row["report_count"] == 2
    assert row["deepest_md_m"] == 1500.0
    assert row["deepest_md_evidence_id"] == f"ddr:report:{R2}"
    assert row["first_report_date"] == "2020-01-01"  # published dates are kept
    assert (row["first_unflagged_report_date"], row["flagged_report_count"]) == ("2020-01-02", 1)
    assert row["flagged_reports"] == [
        {"flag": "before_sodir_spud", "reports": 1},
        {"flag": "depth_not_recorded", "reports": 1},
    ]


def test_hole_sections(warehouse: Path) -> None:
    rows = ok(_server(warehouse), "hole_sections", wellbore_key=T2)["rows"]
    assert [r["evidence_id"] for r in rows] == [
        f"ddr:hole-section:{T2}#1",
        f"ddr:hole-section:{T2}#2",
        f"ddr:hole-section:{T2}#3",
    ]
    assert rows[1]["hole_size_source"] == "unknown"
    assert rows[0]["start_utc"] == "2020-01-01T00:00:00+00:00"
    assert (rows[1]["start_date_local"], rows[1]["end_date_local"]) == ("2020-01-02", "2020-01-02")
    assert rows[0]["new_hole_drilled_m"] == 500.0


def test_lost_time_groupings(warehouse: Path) -> None:
    server = _server(warehouse)
    (section,) = ok(server, "lost_time", wellbore_key=T2, group_by="section")["rows"]
    assert (section["section_number"], section["primary_hours"], section["possible_hours"]) == (
        1,
        4.0,
        2.0,
    )
    assert section["hours"] == 6.0
    assert section["evidence_ids"] == [
        f"ddr:lost-time:{T2}#1|interruption -- maintain",
        f"ddr:lost-time:{T2}#1|interruption -- repair",
    ]
    codes = ok(server, "lost_time", wellbore_key=T2, group_by="code")["rows"]
    assert [(r["code"], r["tier"], r["hours"]) for r in codes] == [
        ("interruption -- maintain", "possible", 2.0),
        ("interruption -- repair", "primary", 4.0),
    ]
    tiers = ok(server, "lost_time", wellbore_key=T2, group_by="tier")["rows"]
    assert [(r["tier"], r["hours"]) for r in tiers] == [("primary", 4.0), ("possible", 2.0)]


def test_activities_are_redacted_capped_and_local(warehouse: Path) -> None:
    server = _server(warehouse)
    body = ok(server, "activities", wellbore_key=T2, start="2020-01-01", end="2020-01-01")
    assert body["matched"] == 3 and not body["capped"]
    first = body["rows"][0]
    assert first["evidence_id"] == f"ddr:activity:{R1}#1"
    assert first["start"] == "2020-01-01T00:00:00+01:00"
    assert "Alex" not in first["comments"] and "12345678" not in first["comments"]
    assert body["redactions"] == {"name": 1, "phone": 1}
    assert [r["lost_time_tier"] for r in body["rows"]] == ["none", "primary", "possible"]

    capped = ok(server, "activities", wellbore_key=T2, start="2020-01-01", end="2020-01-02",
                limit=2)  # fmt: skip
    assert (capped["matched"], capped["returned"], capped["capped"]) == (5, 2, True)

    small_cap = _server(warehouse, row_cap=1)
    body = ok(small_cap, "activities", wellbore_key=T2, start="2020-01-01", end="2020-01-02")
    assert (body["returned"], body["parameters"]["limit"]) == (1, 1)

    filtered = ok(server, "activities", wellbore_key=T2, start="2020-01-01", end="2020-01-02",
                  category="interruption")  # fmt: skip
    assert filtered["matched"] == 2


def test_report_by_operations_day(warehouse: Path) -> None:
    server = _server(warehouse)
    body = ok(server, "report", wellbore_key=T2, date="2020-01-02")
    report = body["report"]
    assert report["evidence_id"] == f"ddr:report:{R2}"  # the file is dated the next day
    assert report["start"] == "2020-01-02T00:00:00+01:00"
    assert report["flags"] == [
        {"flag": "depth_not_recorded", "detail": "md missing on one activity"}
    ]
    assert [r["evidence_id"] for r in body["rows"]] == [
        f"ddr:activity:{R2}#1",
        f"ddr:activity:{R2}#2",
    ]

    is_error, error = call(server, "report", wellbore_key=T2, date="2021-06-30")
    assert is_error and error["error"] == "report_not_found"


def test_drilling_rate(warehouse: Path) -> None:
    rows = ok(_server(warehouse), "drilling_rate", wellbore_key=T2)["rows"]
    assert [
        (r["new_hole_drilled_m"], r["drill_hours"], r["rate_m_per_h"], r["rate_reason"])
        for r in rows
    ] == [
        (500.0, 10.0, 50.0, None),
        (0.0, 12.0, None, "no_new_hole"),
        (300.0, 0.0, None, "no_drilling_hours"),
    ]
    assert rows[2]["evidence_ids"] == [f"ddr:hole-section:{T2}#3"]
    assert all(r["rate_label"] == RATE_LABEL for r in rows)
    assert rows[0]["evidence_ids"] == [
        f"ddr:hole-section:{T2}#1",
        f"ddr:lost-time:{T2}#1|drilling -- drill",
    ]


PER_WELLBORE = [
    ("well_overview", {}),
    ("hole_sections", {}),
    ("lost_time", {"group_by": "code"}),
    ("activities", {"start": "2020-01-01", "end": "2020-01-02"}),
    ("report", {"date": "2020-01-01"}),
    ("drilling_rate", {}),
]


@pytest.mark.parametrize(("tool", "extra"), PER_WELLBORE)
def test_held_out_wellbore_is_refused(warehouse: Path, tool: str, extra: dict[str, Any]) -> None:
    server = _server(warehouse)
    for wellbore in (HELD_OUT, "XX/1-A-2"):
        is_error, body = call(server, tool, wellbore_key=wellbore, **extra)
        assert is_error
        assert body == {
            "error": "wellbore_not_available",
            "detail": "This wellbore is not available to tools in this mode.",
            "hint": "Use a development wellbore.",
        }
    is_error, _ = call(_server(warehouse, evaluation_mode=True), tool, wellbore_key=HELD_OUT,
                       **extra)  # fmt: skip
    assert not is_error


def test_errors_never_echo_the_input(warehouse: Path) -> None:
    server = _server(warehouse)
    day = {"start": "2020-01-01", "end": "2020-01-01"}
    cases: list[tuple[str, dict[str, Any], str, str]] = [
        ("well_overview", {"wellbore_key": "77777"}, "wellbore_not_found", "77777"),
        ("well_overview", {"wellbore_key": "x'; drop y"}, "invalid_arguments", "drop"),
        ("activities", {"wellbore_key": T2, "start": "2020-13-45", "end": "2020-01-01"},
         "invalid_arguments", "2020-13-45"),
        ("activities", {"wellbore_key": T2, "start": "2020-01-02", "end": "2020-01-01"},
         "invalid_arguments", "2020-01-02"),
        ("activities", {"wellbore_key": T2, **day, "limit": 987654}, "invalid_arguments",
         "987654"),
        ("lost_time", {"wellbore_key": T2, "group_by": "secret-grouping"}, "invalid_arguments",
         "secret"),
        ("no_such_tool_zzz", {}, "unknown_tool", "zzz"),
    ]  # fmt: skip
    for tool, arguments, code, marker in cases:
        is_error, body = call(server, tool, **arguments)
        assert is_error and body["error"] == code
        assert marker not in json.dumps(body)


def test_output_is_deterministic(warehouse: Path) -> None:
    server = _server(warehouse)
    args = {"wellbore_key": T2, "start": "2020-01-01", "end": "2020-01-02"}
    assert call(server, "activities", **args) == call(server, "activities", **args)
