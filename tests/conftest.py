"""Shared test fixtures.

- `mcp`: build a synthetic warehouse and call connector tools over MCP.
- `warehouse` and `checker`: a synthetic warehouse for the claim checker (fictional wellbores,
  names and numbers). Wellbores: 9001 and its technical sidetrack 9001:T2 (development), 9002
  (held out), and 9004 / 9005, where the workbook books 9005's production to NPDID 9004 and an
  override attributes it to 9005. The comment of one activity names a deny-listed fictional
  person.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest
from mcp.client.client import Client

from well_ops.agents.checker import Checker
from well_ops.connectors.base import ConnectorServer, connect
from well_ops.connectors.guard import HeldOutGuard, not_available
from well_ops.connectors.redaction import Redactor

WELLBORE_SCHEMA = """
create schema if not exists staging; create schema if not exists marts;
create table marts.dim_wellbore (wellbore_key varchar, wellbore_name varchar, field_name varchar);
create table staging.stg_identifiers__wellbore_alias (
    normalised_name varchar, wellbore_key varchar, status varchar);
"""


class Mcp:
    refusal = not_available().as_dict()

    @staticmethod
    def build_warehouse(
        path: Path,
        schema: str,
        wellbores: Iterable[tuple[str, str, str]],
        rows: dict[str, Sequence[tuple[Any, ...]]],
    ) -> Path:
        """A DuckDB file with the wellbore tables, `schema`, and `rows` inserted per table."""
        con = duckdb.connect(str(path))
        con.execute(WELLBORE_SCHEMA)
        con.execute(schema)
        con.executemany("insert into marts.dim_wellbore values (?, ?, ?)", list(wellbores))
        for table, values in rows.items():
            if values:
                marks = ", ".join("?" * len(values[0]))
                con.executemany(f"insert into {table} values ({marks})", list(values))
        con.close()
        return path

    @staticmethod
    def call(server: ConnectorServer, name: str, **arguments: Any) -> tuple[bool, dict[str, Any]]:
        async def run() -> tuple[bool, dict[str, Any]]:
            async with Client(server) as client:
                result = await client.call_tool(name, arguments)
            assert result.structured_content is not None
            return bool(result.is_error), result.structured_content

        return asyncio.run(run())

    @staticmethod
    def ok(server: ConnectorServer, name: str, **arguments: Any) -> dict[str, Any]:
        is_error, body = Mcp.call(server, name, **arguments)
        assert not is_error, body
        return body

    @staticmethod
    def error(server: ConnectorServer, name: str, **arguments: Any) -> dict[str, Any]:
        is_error, body = Mcp.call(server, name, **arguments)
        assert is_error, body
        return body


@pytest.fixture
def mcp() -> type[Mcp]:
    return Mcp


# --- Claim checker warehouse ---

T2, HELD_OUT, PUBLISHED, ATTRIBUTED = "9001:T2", "9002", "9004", "9005"
PERSON = "Alex Placeholder"

CHECKER_SCHEMA = """
create schema intermediate; create schema reference;
create table staging.stg_ddr__report (
    report_file varchar, wellbore_key varchar, start_utc timestamp, start_offset varchar,
    md_m double, comments varchar);
create table intermediate.int_ddr__report_flag (
    report_file varchar, wellbore_key varchar, flag varchar);
create table staging.stg_ddr__activity (
    report_file varchar, activity_number integer, wellbore_key varchar, duration_hours double,
    category varchar, subcategory varchar, comments varchar);
create table marts.dim_hole_section (
    section_id varchar, wellbore_key varchar, section_number hugeint, hole_size_in double,
    start_md_m double, end_md_m double, report_count bigint, activity_hours double,
    interruption_hours double, new_hole_drilled_m double, start_date_local date,
    end_date_local date);
create table marts.fct_lost_time (
    wellbore_key varchar, section_id varchar, category varchar, subcategory varchar,
    tier varchar, hours double, activities bigint);
create table staging.stg_sodir__wellbore (
    wellbore_key varchar, npdid bigint, entry_date date, completion_date date,
    total_depth_m double);
create table staging.stg_production__monthly (
    wellbore_key varchar, npdid bigint, month_start date, oil_sm3 double);
create table intermediate.int_production__monthly_attributed (
    attributed_wellbore_key varchar, published_npdid bigint, month_start date, oil_sm3 double,
    gas_sm3 double, water_sm3 double, gas_injected_sm3 double, water_injected_sm3 double);
create table marts.fct_production_monthly_reconciliation (
    month_start date, oil_workbook_sm3 double, oil_sodir_gross_sm3 double,
    oil_sodir_net_sm3 double, gas_workbook_sm3 double, gas_sodir_gross_sm3 double,
    gas_sodir_net_sm3 double, water_workbook_sm3 double, water_sodir_gross_sm3 double,
    water_sodir_net_sm3 double);
create table staging.stg_sodir__field_production_gross_monthly (
    field_npdid bigint, field_name varchar, month_start date);
create table staging.stg_sodir__field_production_net_monthly (
    field_npdid bigint, field_name varchar, month_start date);
"""

JAN, FEB = date(2020, 1, 1), date(2020, 2, 1)


def _section(n: int, size: float, start: float, end: float, new_hole: float) -> tuple[Any, ...]:
    day = date(2020, 1, n)
    return (f"{T2}#{n}", T2, n, size, start, end, 3, 72.0, 4.0, new_hole, day, day)


def _report(name: str, key: str, utc: datetime, md: float | None) -> tuple[Any, ...]:
    return (name, key, utc, "+02:00", md, None)


@pytest.fixture
def warehouse(tmp_path: Path, mcp: Any) -> Path:
    path: Path = mcp.build_warehouse(
        tmp_path / "w.duckdb",
        CHECKER_SCHEMA,
        [
            ("9001", "XX/1-A-1", "VOLVE"),
            (T2, "XX/1-A-1 T2", "VOLVE"),
            (HELD_OUT, "XX/1-A-2", "VOLVE"),
            (PUBLISHED, "XX/1-A-4", "VOLVE"),
            (ATTRIBUTED, "XX/1-A-4 B", "VOLVE"),
        ],
        {
            "staging.stg_ddr__report": [
                _report("R0", T2, datetime(1980, 1, 1), None),  # placeholder date, flagged
                _report("R1", T2, datetime(2020, 1, 1, 22), 500.0),  # operations day 2020-01-02
                _report("R2", T2, datetime(2020, 1, 2, 22), 1500.0),
                _report("RH", HELD_OUT, datetime(2020, 1, 1, 22), 900.0),
            ],
            "intermediate.int_ddr__report_flag": [("R0", T2, "before_sodir_spud")],
            "staging.stg_ddr__activity": [
                ("R1", 1, T2, 2.5, "interruption", "wait", f"Waited on weather. {PERSON} on deck."),
                ("R1", 2, T2, 3.0, "drilling", "drill", "Drilled 12 1/4in hole to 1500 m."),
                ("RH", 1, HELD_OUT, 1.0, "drilling", "drill", "Drilled ahead."),
            ],
            "marts.dim_hole_section": [
                _section(1, 26.0, 0.0, 1000.0, 1000.0),
                _section(2, 12.25, 1000.0, 2000.0, 1000.0),
                _section(3, 8.5, 2000.0, 2000.0, 0.0),
            ],
            "marts.fct_lost_time": [
                (T2, f"{T2}#1", "interruption", "wait", "primary", 5.0, 2),
                (T2, f"{T2}#2", "interruption", "repair", "primary", 3.5, 1),
                (T2, f"{T2}#2", "drilling", "ream", "possible", 2.0, 1),
                (T2, f"{T2}#1", "drilling", "drill", "none", 62.5, 8),
                (T2, f"{T2}#2", "drilling", "drill", "none", 50.0, 10),
            ],
            "staging.stg_sodir__wellbore": [
                ("9001", 9001, date(2019, 12, 1), date(2020, 3, 1), 2500.0),
                (HELD_OUT, 9002, date(2019, 6, 1), date(2019, 9, 1), 3000.0),
            ],
            "staging.stg_production__monthly": [
                (PUBLISHED, 9004, JAN, 1000.0),
                (PUBLISHED, 9004, FEB, 2000.0),
                ("9001", 9001, JAN, 500.0),
            ],
            "intermediate.int_production__monthly_attributed": [
                (ATTRIBUTED, 9004, JAN, 1000.0, 1e5, 10.0, None, None),
                (ATTRIBUTED, 9004, FEB, 2000.0, 2e5, 20.0, None, None),
                ("9001", 9001, JAN, 500.0, 5e4, 5.0, None, None),
            ],
            "marts.fct_production_monthly_reconciliation": [
                (JAN, 1500.0, 1510.0, 1490.0, 1.5e5, 1.5e5, 0.8e5, 15.0, 15.0, 15.0),
                (FEB, 2000.0, 2010.0, 1990.0, 2e5, 2e5, 1e5, 20.0, 20.0, 20.0),
            ],
            "staging.stg_sodir__field_production_gross_monthly": [
                (777, "VOLVE", JAN),
                (777, "VOLVE", FEB),
            ],
            "staging.stg_sodir__field_production_net_monthly": [(777, "VOLVE", JAN)],
        },
    )
    return path


@pytest.fixture
def checker(warehouse: Path) -> Checker:
    return Checker(connect(warehouse), HeldOutGuard([HELD_OUT], False), Redactor([PERSON]))
