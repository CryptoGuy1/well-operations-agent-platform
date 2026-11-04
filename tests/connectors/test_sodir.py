"""Sodir server tests on a synthetic warehouse (fictional wellbores and fields)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from well_ops.connectors.base import ConnectorServer, connect
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.redaction import Redactor
from well_ops.connectors.sodir.server import build_server
from well_ops.connectors.sodir.tools import Sodir

DEV, HELD_OUT = "9001", "9002"

SCHEMA = """
create table staging.stg_sodir__wellbore (
    wellbore_key varchar, npdid bigint, wellbore_name varchar, well_name varchar,
    field_name varchar, purpose varchar, status varchar, entry_date date, completion_date date,
    total_depth_m double);
create table staging.stg_sodir__field_production_gross_monthly (
    field_npdid bigint, field_name varchar, month_start date, oil_gross_mill_sm3 double,
    gas_gross_bill_sm3 double, condensate_gross_mill_sm3 double, oe_gross_mill_sm3 double,
    produced_water_in_field_mill_sm3 double);
create table staging.stg_sodir__field_production_net_monthly (
    field_npdid bigint, field_name varchar, month_start date, oil_net_mill_sm3 double,
    gas_net_bill_sm3 double, ngl_net_mill_sm3 double, condensate_net_mill_sm3 double,
    oe_net_mill_sm3 double, produced_water_in_field_mill_sm3 double);
"""


def _facts(key: str, name: str) -> tuple[Any, ...]:
    return (key, int(key), name, name, "ØSTFELT", "PRODUCTION", "PRODUCING",
            date(2010, 1, 5), date(2010, 3, 1), 3500.0)  # fmt: skip


@pytest.fixture
def server(tmp_path: Path, mcp: Any) -> ConnectorServer:
    path = mcp.build_warehouse(
        tmp_path / "w.duckdb",
        SCHEMA,
        [
            (DEV, "XX/1-A-1", "ØSTFELT"),
            (f"{DEV}:T2", "XX/1-A-1 T2", "ØSTFELT"),
            (HELD_OUT, "XX/1-A-2", "ØSTFELT"),
            (f"{HELD_OUT}:T2", "XX/1-A-2 T2", "ØSTFELT"),
            ("9003", "XX/1-A-3", "ØSTFELT"),
        ],
        {
            "staging.stg_sodir__wellbore": [_facts(DEV, "XX/1-A-1"), _facts(HELD_OUT, "XX/1-A-2")],
            "staging.stg_sodir__field_production_gross_monthly": [
                (777, "ØSTFELT", date(2010, 1, 1), 0.1, 0.02, 0.0, 0.12, 0.01),
                (777, "ØSTFELT", date(2010, 2, 1), 0.2, 0.03, 0.0, 0.23, 0.02),
            ],
            "staging.stg_sodir__field_production_net_monthly": [
                (777, "ØSTFELT", date(2010, 1, 1), 0.09, 0.01, 0.0, 0.0, 0.1, 0.01),
            ],
        },
    )
    tools = Sodir(connect(path), HeldOutGuard([HELD_OUT], False), Redactor(), 200)
    return build_server(tools)


def test_wellbore_facts(mcp: Any, server: ConnectorServer) -> None:
    (row,) = mcp.ok(server, "wellbore_facts", wellbore_key="XX/1-A-1")["rows"]
    assert row["evidence_id"] == "sodir:wellbore:9001"
    assert (row["completion_date"], row["total_depth_m"], row["note"]) == (
        "2010-03-01",
        3500.0,
        None,
    )


def test_technical_sidetrack_gets_its_parents_facts(mcp: Any, server: ConnectorServer) -> None:
    (row,) = mcp.ok(server, "wellbore_facts", wellbore_key=f"{DEV}:T2")["rows"]
    assert (row["wellbore_key"], row["sodir_wellbore_key"]) == (f"{DEV}:T2", DEV)
    assert row["evidence_id"] == "sodir:wellbore:9001"
    assert "parent" in row["note"]


def test_held_out_wellbore_and_its_sidetrack_are_refused(mcp: Any, server: ConnectorServer) -> None:
    for key in (HELD_OUT, f"{HELD_OUT}:T2", "XX/1-A-2"):
        assert mcp.error(server, "wellbore_facts", wellbore_key=key) == mcp.refusal


def test_wellbore_missing_from_sodir(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.error(server, "wellbore_facts", wellbore_key="9003")
    assert body["error"] == "wellbore_not_in_sodir"


def test_field_production_by_basis(mcp: Any, server: ConnectorServer) -> None:
    gross = mcp.ok(server, "field_production", field="østfelt", start="2010-01-31",
                   end="2010-02-01", basis="gross")  # fmt: skip
    assert gross["parameters"]["field"] == "ØSTFELT"
    assert [(r["evidence_id"], r["oil_gross_mill_sm3"]) for r in gross["rows"]] == [
        ("sodir:field-gross:777:2010-01", 0.1),
        ("sodir:field-gross:777:2010-02", 0.2),
    ]
    net = mcp.ok(server, "field_production", field="ØSTFELT", start="2010-01-01", end="2010-12-31")
    assert net["parameters"]["basis"] == "net"
    assert net["basis_label"].startswith("Sodir saleable")
    assert [r["evidence_id"] for r in net["rows"]] == ["sodir:field-net:777:2010-01"]


def test_unknown_field(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.error(server, "field_production", field="NOWHERE", start="2010-01-01",
                     end="2010-01-31")  # fmt: skip
    assert body["error"] == "field_not_found" and "NOWHERE" not in str(body)
