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
# The workbook books OVERRIDDEN's production to PUBLISHED; a seed override attributes it back.
PUBLISHED, OVERRIDDEN = "9004", "9005"
REASON = "fictional reason"

SCHEMA = """
create schema intermediate;
create table intermediate.int_production__monthly_attributed (
    attributed_wellbore_key varchar, attribution_source varchar, attribution_reason varchar,
    published_npdid bigint, month_start date, on_stream_hours double, oil_sm3 double,
    gas_sm3 double, water_sm3 double, gas_injected_sm3 double, water_injected_sm3 double);
create table intermediate.int_production__monthly_flag (
    wellbore_key varchar, month_start date, published_npdid bigint, flag varchar, detail varchar);
create table intermediate.int_production__daily_flag (
    wellbore_key varchar, published_npdid bigint, production_date date, flag varchar,
    detail varchar);
create table intermediate.int_production__daily_units_check (
    wellbore_key varchar, published_npdid bigint, month_start date, in_monthly_sheet boolean,
    daily_volume_unit varchar,
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


def _monthly(
    key: str, npdid: int, month: date, oil: float, source: str = "npdid"
) -> tuple[object, ...]:
    reason = REASON if source == "override" else None
    return (key, source, reason, npdid, month, 700.0, oil, oil * 150, oil / 20, None, None)


def _recon(month: date, oil: float) -> tuple[object, ...]:
    per_fluid = (oil + 0.004999999, oil * 1.01, oil * 0.98, 0.99, 1.0200004, 1.03)
    return (month, *BASES, *per_fluid, *per_fluid, *per_fluid)


@pytest.fixture
def server(tmp_path: Path, mcp: Any) -> ConnectorServer:
    path = mcp.build_warehouse(
        tmp_path / "w.duckdb",
        SCHEMA,
        [
            (DEV, "XX/1-A-1", "VOLVE"),
            (HELD_OUT, "XX/1-A-2", "VOLVE"),
            (PUBLISHED, "XX/1-A-4", "VOLVE"),
            (OVERRIDDEN, "XX/1-A-4 B", "VOLVE"),
        ],
        {
            "intermediate.int_production__monthly_attributed": [
                _monthly(DEV, 9001, date(2020, 1, 1), 1000.0),
                _monthly(DEV, 9001, date(2020, 2, 1), 900.0),
                _monthly(DEV, 9001, date(2020, 3, 1), 800.0),
                _monthly(HELD_OUT, 9002, date(2020, 1, 1), 500.0),
                _monthly(OVERRIDDEN, 9004, date(2020, 1, 1), 300.0, "override"),
            ],
            "intermediate.int_production__monthly_flag": [
                (
                    DEV,
                    date(2020, 1, 1),
                    9001,
                    "production_before_completion",
                    "Sodir completion month 2020-02",
                ),
                (
                    OVERRIDDEN,
                    date(2020, 1, 1),
                    9004,
                    "attribution_override",
                    "published NPDID 9004",
                ),
            ],
            "intermediate.int_production__daily_flag": [
                (DEV, 9001, date(2020, 1, 15), "negative_volume", "water volume below zero"),
            ],
            "intermediate.int_production__daily_units_check": [
                (DEV, 9001, date(2020, 1, 1), True, "sm3", True, True, True, 1.0, 1.0, 1.0),
                (DEV, 9001, date(2020, 2, 1), True, "sm3", True, False, True, 1.0, 0.5, 1.0),
                (DEV, 9001, date(2020, 4, 1), False, "sm3", None, None, None, None, None, None),
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
    first = body["rows"][0]
    assert (first["wellbore_key"], first["published_npdid"], first["attribution_source"]) == (
        DEV,
        9001,
        "npdid",
    )
    assert first["attribution_reason"] is None


def test_overridden_rows_use_the_attributed_key_and_cite_the_published_npdid(
    mcp: Any, server: ConnectorServer
) -> None:
    window = {"start": "2020-01-01", "end": "2020-12-31"}
    (row,) = mcp.ok(server, "monthly_production", wellbore_key="XX/1-A-4 B", **window)["rows"]
    assert row["evidence_id"] == "prod:monthly:9004:2020-01"
    assert (row["wellbore_key"], row["published_npdid"]) == (OVERRIDDEN, 9004)
    assert (row["attribution_source"], row["attribution_reason"]) == ("override", REASON)
    assert mcp.ok(server, "monthly_production", wellbore_key=PUBLISHED, **window)["rows"] == []
    (flag,) = mcp.ok(server, "data_quality_flags", wellbore_key=OVERRIDDEN)["rows"]
    assert (flag["kind"], flag["flag"], flag["evidence_id"]) == (
        "monthly_flag",
        "attribution_override",
        "prod:monthly:9004:2020-01",
    )


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
        ("monthly_flag", "prod:monthly:9001:2020-01"),  # production_before_completion
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
