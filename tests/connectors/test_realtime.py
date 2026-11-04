"""Real-time server tests on a synthetic warehouse (fictional wellbores and logs)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from well_ops.connectors.base import ConnectorServer, connect
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.realtime.server import build_server
from well_ops.connectors.realtime.tools import Realtime
from well_ops.connectors.redaction import Redactor

T2, HELD_OUT = "9001:T2", "9002"
DEPTH_LOG, TIME_LOG, HELD_LOG = f"{T2}#1/1/1", f"{T2}#1/2/1", f"{HELD_OUT}#1/1/1"

SCHEMA = """
create schema intermediate;
create table staging.stg_witsml__log (
    log_id varchar, wellbore_key varchar, log_name varchar, index_type varchar,
    index_curve varchar, index_uom varchar, start_index varchar, end_index varchar,
    direction varchar, service_company varchar, run_number varchar, rows bigint);
create table staging.stg_witsml__log_curve (
    log_curve_id varchar, log_id varchar, mnemonic varchar, unit varchar,
    curve_description varchar);
create table staging.stg_witsml__log_value (
    wellbore_key varchar, log_id varchar, "Depth" double, "Time" timestamp, "GR" double,
    "ROP_AVG" double, "LITHO" varchar);
create table intermediate.int_witsml__log_flag (log_id varchar, flag varchar);
"""


def _log(log_id: str, key: str, kind: str, curve: str, uom: str | None) -> tuple[Any, ...]:
    return (log_id, key, "TESTLOG", kind, curve, uom, "0", "1", "increasing", "Vendor", "1", 4)


def _curve(log_id: str, mnemonic: str, unit: str | None) -> tuple[Any, ...]:
    return (f"{log_id}|{mnemonic}|{unit}", log_id, mnemonic, unit, f"{mnemonic} curve")


@pytest.fixture
def server(tmp_path: Path, mcp: Any) -> ConnectorServer:
    t0 = datetime(2020, 1, 1, 10, 0)
    path = mcp.build_warehouse(
        tmp_path / "w.duckdb",
        SCHEMA,
        [("9001", "XX/1-A-1", "F"), (T2, "XX/1-A-1 T2", "F"), (HELD_OUT, "XX/1-A-2", "F")],
        {
            "staging.stg_witsml__log": [
                _log(DEPTH_LOG, T2, "measured depth", "Depth", "m"),
                _log(TIME_LOG, T2, "date time", "TIME", None),
                _log(HELD_LOG, HELD_OUT, "measured depth", "Depth", "m"),
            ],
            "staging.stg_witsml__log_curve": [
                _curve(DEPTH_LOG, "Depth", "m"),
                _curve(DEPTH_LOG, "GR", "gAPI"),
                _curve(DEPTH_LOG, "LITHO", None),
                _curve(TIME_LOG, "TIME", None),
                _curve(TIME_LOG, "ROP_AVG", "m/h"),
                _curve(HELD_LOG, "GR", "gAPI"),
            ],
            "staging.stg_witsml__log_value": [
                (T2, DEPTH_LOG, 100.0, None, 50.0, None, "sand"),
                (T2, DEPTH_LOG, 101.0, None, 60.0, None, "sand"),
                (T2, DEPTH_LOG, 101.0, None, 70.0, None, "shale"),  # repeated index value
                (T2, DEPTH_LOG, 102.0, None, None, None, "shale"),
                (T2, TIME_LOG, None, t0, None, 10.0, None),
                (T2, TIME_LOG, None, t0.replace(hour=11), None, 20.0, None),
                (T2, TIME_LOG, None, t0.replace(hour=12), None, 30.0, None),
                (HELD_OUT, HELD_LOG, 100.0, None, 1.0, None, None),
            ],
            "intermediate.int_witsml__log_flag": [(TIME_LOG, "outside_report_period")],
        },
    )
    tools = Realtime(connect(path), HeldOutGuard([HELD_OUT], False), Redactor(), 200)
    return build_server(tools)


def test_list_logs(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.ok(server, "list_logs", wellbore_key="XX/1-A-1 T2")
    assert [(r["evidence_id"], r["curve_count"], r["flags"]) for r in body["rows"]] == [
        (f"rt:log:{DEPTH_LOG}", 3, []),
        (f"rt:log:{TIME_LOG}", 2, ["outside_report_period"]),
    ]
    depth = mcp.ok(server, "list_logs", wellbore_key=T2, index_type="measured depth")
    assert [r["log_id"] for r in depth["rows"]] == [DEPTH_LOG]


def test_wellbore_without_extracted_logs(mcp: Any, server: ConnectorServer) -> None:
    assert mcp.error(server, "list_logs", wellbore_key="9001")["error"] == "logs_not_extracted"


def test_curve_summary_over_a_depth_range(mcp: Any, server: ConnectorServer) -> None:
    (row,) = mcp.ok(server, "curve_summary", wellbore_key=T2, log=DEPTH_LOG, mnemonic="GR")["rows"]
    assert row["evidence_id"] == f"rt:log-curve:{DEPTH_LOG}|GR|gAPI"
    assert (row["rows_in_range"], row["distinct_index_values"], row["count"]) == (4, 3, 3)
    assert (row["min"], row["max"], row["mean"], row["unit"]) == (50.0, 70.0, 60.0, "gAPI")
    (ranged,) = mcp.ok(server, "curve_summary", wellbore_key=T2, log=DEPTH_LOG, mnemonic="GR",
                       start=100.5, end=101.0)["rows"]  # fmt: skip
    assert (ranged["count"], ranged["mean"], ranged["first_index"]) == (2, 65.0, 101.0)


def test_curve_summary_over_a_time_range(mcp: Any, server: ConnectorServer) -> None:
    body = mcp.ok(server, "curve_summary", wellbore_key=T2, log=TIME_LOG, mnemonic="ROP_AVG",
                  start="2020-01-01T11:30:00+01:00", end="2020-01-01T12:00:00Z")  # fmt: skip
    (row,) = body["rows"]
    assert body["parameters"]["start"] == "2020-01-01T10:30:00+00:00"
    assert (row["count"], row["mean"], row["last_index"]) == (2, 25.0, "2020-01-01T12:00:00+00:00")


@pytest.mark.parametrize(
    ("arguments", "code"),
    [
        ({"log": DEPTH_LOG, "mnemonic": "NOPE"}, "curve_not_found"),
        ({"log": DEPTH_LOG, "mnemonic": "LITHO"}, "curve_not_numeric"),
        ({"log": DEPTH_LOG, "mnemonic": 'GR"; drop'}, "invalid_arguments"),
        ({"log": HELD_LOG, "mnemonic": "GR"}, "log_not_found"),
        ({"log": DEPTH_LOG, "mnemonic": "GR", "start": "2020-01-01T00:00:00"}, "invalid_arguments"),
        ({"log": TIME_LOG, "mnemonic": "ROP_AVG", "start": 100.0}, "invalid_arguments"),
        ({"log": DEPTH_LOG, "mnemonic": "GR", "start": 102.0, "end": 100.0}, "invalid_arguments"),
    ],
)
def test_curve_summary_errors(
    mcp: Any, server: ConnectorServer, arguments: dict[str, Any], code: str
) -> None:
    body = mcp.error(server, "curve_summary", wellbore_key=T2, **arguments)
    assert body["error"] == code and "drop" not in str(body)


def test_held_out_wellbore_is_refused(mcp: Any, server: ConnectorServer) -> None:
    assert mcp.error(server, "list_logs", wellbore_key=HELD_OUT) == mcp.refusal
    body = mcp.error(server, "curve_summary", wellbore_key=HELD_OUT, log=HELD_LOG, mnemonic="GR")
    assert body == mcp.refusal
