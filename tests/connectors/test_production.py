"""Production server tests on a synthetic warehouse (fictional wellbores)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from well_ops.connectors.base import ConnectorServer, connect
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.production.server import build_server
from well_ops.connectors.production.tools import Production
from well_ops.connectors.redaction import Redactor

DEV, HELD_OUT = "9001", "9002"

SCHEMA = """
create schema intermediate;
create table staging.stg_production__monthly (
    wellbore_key varchar, npdid bigint, month_start date, on_stream_hours double, oil_sm3 double,
    gas_sm3 double, water_sm3 double, gas_injected_sm3 double, water_injected_sm3 double);
create table intermediate.int_production__daily_flag (
    wellbore_key varchar, production_date date, flag varchar, detail varchar);
create table intermediate.int_production__daily_units_check (
    wellbore_key varchar, month_start date, in_monthly_sheet boolean, daily_volume_unit varchar,
    oil_agrees boolean, gas_agrees boolean, water_agrees boolean, oil_ratio double,
    gas_ratio double, water_ratio double);
create table marts.fct_production_monthly_reconciliation (
    month_start date, workbook_basis varchar, sodir_gross_basis varchar, sodir_net_basis varchar,
    oil_workbook_sm3 double, oil_sodir_gross_sm3 double, oil_sodir_net_sm3 double,
    oil_workbook_to_gross double, oil_workbook_to_net double, oil_gross_to_net double,
    gas_workbook_sm3 double, gas_sodir_gross_sm3 double, gas_sodir_net_sm3 double,
    gas_workbook_to_gross double, gas_workbook_to_net double, gas_gross_to_net double,
    water_workbook_sm3 double, water_sodir_gross_sm3 double, water_sodir_net_sm3 double,
    water_workbook_to_gross double, water_workbook_to_net double, water_gross_to_net double);
"""

BASES = ("workbook sum", "sodir gross", "sodir net")


def _recon(month: date, oil: float) -> tuple[object, ...]:
    per_fluid = (oil + 0.004999999, oil * 1.01, oil * 0.98, 0.99, 1.0200004, 1.03)
    return (month, *BASES, *per_fluid, *per_fluid, *per_fluid)


@pytest.fixture
def server(tmp_path: Path, mcp: Any) -> ConnectorServer:
    path = mcp.build_warehouse(
        tmp_path / "w.duckdb",
        SCHEMA,
        [(DEV, "XX/1-A-1", "VOLVE"), (HELD_OUT, "XX/1-A-2", "VOLVE")],
        {
            "staging.stg_production__monthly": [
                (DEV, 9001, date(2020, 1, 1), 700.0, 1000.0, 150000.0, 50.0, None, None),
                (DEV, 9001, date(2020, 2, 1), 650.0, 900.0, 140000.0, 60.0, None, None),
                (DEV, 9001, date(2020, 3, 1), 600.0, 800.0, 130000.0, 70.0, None, None),
                (HELD_OUT, 9002, date(2020, 1, 1), 700.0, 500.0, 70000.0, 10.0, None, None),
            ],
            "intermediate.int_production__daily_flag": [
                (DEV, date(2020, 1, 15), "negative_volume", "water volume below zero"),
            ],
            "intermediate.int_production__daily_units_check": [
                (DEV, date(2020, 1, 1), True, "sm3", True, True, True, 1.0, 1.0, 1.0),
                (DEV, date(2020, 2, 1), True, "sm3", True, False, True, 1.0, 0.5, 1.0),
                (DEV, date(2020, 4, 1), False, "sm3", None, None, None, None, None, None),
            ],
            "marts.fct_production_monthly_reconciliation": [
                _recon(date(2020, 1, 1), 1500.0),
                _recon(date(2020, 2, 1), 900.0),
            ],
        },
    )
    tools = Production(connect(path), HeldOutGuard([HELD_OUT], False), Redactor(), 200)
    return build_server(tools)


def test_monthly_production_for_a_wellbore(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.ok(
        server, "monthly_production", wellbore_key=DEV, start="2020-01-20", end="2020-02-03"
    )
    assert body["parameters"] == {"wellbore_key": DEV, "start": "2020-01", "end": "2020-02"}
    assert [(r["evidence_id"], r["oil_sm3"]) for r in body["rows"]] == [
        ("prod:monthly:9001:2020-01", 1000.0),
        ("prod:monthly:9001:2020-02", 900.0),
    ]


def test_monthly_production_for_the_field_uses_the_workbook_sum(
    mcp: Any, server: ConnectorServer
) -> None:
    body = mcp.ok(server, "monthly_production", field="volve", start="2020-01-01", end="2020-12-31")
    assert body["source"] == ["marts.fct_production_monthly_reconciliation"]
    assert [(r["evidence_id"], r["oil_sm3"], r["basis"]) for r in body["rows"]] == [
        ("prod:reconciliation:2020-01", 1500.0, "workbook sum"),
        ("prod:reconciliation:2020-02", 900.0, "workbook sum"),
    ]
    assert mcp.error(server, "monthly_production", field="OTHER", start="2020-01-01",
                 end="2020-01-31")["error"] == "field_not_available"  # fmt: skip


@pytest.mark.parametrize("arguments", [{}, {"wellbore_key": DEV, "field": "VOLVE"}])
def test_monthly_production_needs_exactly_one_of_wellbore_and_field(
    mcp: Any, server: ConnectorServer, arguments: dict[str, str]
) -> None:
    body = mcp.error(
        server, "monthly_production", start="2020-01-01", end="2020-01-31", **arguments
    )
    assert body["error"] == "invalid_arguments"


def test_reconciliation_has_bases_and_ratios(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.ok(server, "reconciliation", start="2020-02-01", end="2020-02-28")
    assert body["basis"] == [
        {"workbook": "workbook sum", "sodir_gross": "sodir gross", "sodir_net": "sodir net"}
    ]
    (row,) = body["rows"]
    assert row["evidence_id"] == "prod:reconciliation:2020-02"
    assert (row["oil_workbook_sm3"], row["oil_workbook_to_net"]) == (900.0, 1.02)


def test_data_quality_flags(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.ok(server, "data_quality_flags", wellbore_key=DEV)
    assert body["units_check_months"] == 3
    assert [(r["kind"], r["evidence_id"]) for r in body["rows"]] == [
        ("daily_flag", "prod:daily:9001:2020-01-15"),
        ("units_check", "prod:monthly:9001:2020-02"),
        ("units_check", None),  # month missing from the monthly sheet
    ]


@pytest.mark.parametrize(
    ("tool", "extra"),
    [
        ("monthly_production", {"start": "2020-01-01", "end": "2020-01-31"}),
        ("data_quality_flags", {}),
    ],
)
def test_held_out_wellbore_is_refused(
    mcp: Any, server: ConnectorServer, tool: str, extra: dict[str, str]
) -> None:
    assert mcp.error(server, tool, wellbore_key=HELD_OUT, **extra) == mcp.refusal
