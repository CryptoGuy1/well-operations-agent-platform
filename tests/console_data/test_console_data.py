"""The console data bundle on a synthetic warehouse: fictional wellbores 9001 (development) and
9002 (held out), fictional names, numbers and runs."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from well_ops.agents.audit_log import Run, RunLog
from well_ops.agents.checker import ClaimResult, Verdict
from well_ops.agents.schema import Document
from well_ops.connectors.redaction import Redactor
from well_ops.console_data import evaluation, health, reconciliation, runs, wells
from well_ops.console_data.bundle import Bundle, dumps, jsonable, scan

DEV, HELD_OUT = "9001", "9002"
PERSON = "Alex Placeholder"
REDACTOR = Redactor([PERSON])

SCHEMA = """
create schema staging; create schema intermediate; create schema marts;
create table marts.dim_wellbore (
    wellbore_key varchar, wellbore_name varchar, field_name varchar, is_heldout boolean);
create table staging.stg_identifiers__wellbore_alias (
    normalised_name varchar, wellbore_key varchar, status varchar);
create table staging.stg_ddr__report (
    report_file varchar, wellbore_key varchar, start_utc timestamp, start_offset varchar,
    end_utc timestamp, md_m double);
create table intermediate.int_ddr__report_flag (
    report_file varchar, wellbore_key varchar, flag varchar);
create table staging.stg_ddr__activity (
    report_file varchar, activity_number integer, wellbore_key varchar, comments varchar);
create table marts.dim_hole_section (
    section_id varchar, wellbore_key varchar, section_number hugeint, section_label varchar,
    hole_size_in double, hole_size_source varchar, start_date_local date, end_date_local date,
    start_md_m double, end_md_m double, end_tvd_m double, casing_shoe_md_m double,
    report_count bigint, inferred_share double, operation_phase varchar, activity_hours double,
    interruption_hours double, new_hole_drilled_m double);
create table marts.dim_campaign (
    campaign_id varchar, wellbore_key varchar, campaign_number hugeint, start_date_local date,
    end_date_local date, span_days double, active_days bigint, report_count bigint,
    operation_phase varchar);
create table marts.fct_lost_time (
    wellbore_key varchar, section_id varchar, category varchar, subcategory varchar,
    tier varchar, hours double, activities bigint);
create table marts.fct_production_monthly_reconciliation (
    month_start date, workbook_basis varchar, sodir_gross_basis varchar, sodir_net_basis varchar,
    oil_workbook_sm3 double);
create table intermediate.int_production__monthly_attributed (
    attributed_wellbore_key varchar, attribution_source varchar, attribution_reason varchar,
    published_npdid bigint, month_start date);
"""


def _day(n: int) -> dt.datetime:
    return dt.datetime(2020, 1, n, 22)  # local midnight at UTC+2: operations day n + 1


@pytest.fixture
def con(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(str(tmp_path / "w.duckdb"))
    c.execute(SCHEMA)
    rows: dict[str, list[tuple[Any, ...]]] = {
        "marts.dim_wellbore": [
            (DEV, "XX/1-A-1", "VOLVE", False),
            (HELD_OUT, "XX/1-A-2", "VOLVE", True),
        ],
        "staging.stg_ddr__report": [
            ("R1", DEV, _day(1), "+02:00", _day(2), 500.0),
            ("R2", DEV, _day(2), "+02:00", _day(3), None),  # depth not recorded
            ("R3", DEV, _day(3), "+02:00", _day(4), 1500.0),
            ("RH", HELD_OUT, _day(1), "+02:00", _day(2), 900.0),
        ],
        "intermediate.int_ddr__report_flag": [
            ("R2", DEV, "depth_not_recorded"),
            ("RH", HELD_OUT, "depth_not_recorded"),
        ],
        "staging.stg_ddr__activity": [("R1", 1, DEV, f"Waited on weather. {PERSON} on deck.")],
        "marts.dim_hole_section": [
            (
                f"{DEV}#1",
                DEV,
                1,
                "26 in",
                26.0,
                "report",
                dt.date(2020, 1, 2),
                dt.date(2020, 1, 3),
                0.0,
                1000.0,
                990.0,
                990.0,
                2,
                0.0,
                "drilling",
                48.0,
                3.5,
                1000.0,
            ),
            (
                f"{HELD_OUT}#1",
                HELD_OUT,
                1,
                "17 1/2 in",
                17.5,
                "report",
                dt.date(2020, 1, 2),
                dt.date(2020, 1, 2),
                0.0,
                900.0,
                890.0,
                None,
                1,
                0.0,
                "drilling",
                24.0,
                0.0,
                900.0,
            ),
        ],
        "marts.dim_campaign": [
            (f"{DEV}#1", DEV, 1, dt.date(2020, 1, 2), dt.date(2020, 1, 4), 3.0, 3, 3, "drilling")
        ],
        "marts.fct_lost_time": [
            (DEV, f"{DEV}#1", "interruption", "wait", "primary", 2.5, 1),
            (DEV, f"{DEV}#1", "interruption", "repair", "primary", 1.0, 1),
            (DEV, f"{DEV}#1", "drilling", "trip", "possible", 2.0, 2),
            (HELD_OUT, f"{HELD_OUT}#1", "interruption", "wait", "primary", 9.0, 1),
        ],
        "marts.fct_production_monthly_reconciliation": [
            (dt.date(2020, 2, 1), "workbook", "gross", "net", 20.0),
            (dt.date(2020, 1, 1), "workbook", "gross", "net", 10.0),
        ],
        "intermediate.int_production__monthly_attributed": [
            (DEV, "override", "fictional reason", 9000, dt.date(2020, 1, 1)),
            (DEV, "override", "fictional reason", 9000, dt.date(2020, 2, 1)),
            (HELD_OUT, "npdid", None, 9002, dt.date(2020, 1, 1)),
        ],
    }
    for table, values in rows.items():
        c.executemany(f"insert into {table} values ({', '.join('?' * len(values[0]))})", values)
    return c


@pytest.fixture
def roles(tmp_path: Path) -> dict[str, str]:
    path = tmp_path / "splits.json"
    path.write_text(
        json.dumps(
            {
                "development": [{"key": DEV, "name": "XX/1-A-1"}],
                "held_out": [{"key": HELD_OUT, "name": "XX/1-A-2"}],
            }
        ),
        encoding="utf-8",
    )
    return wells.split_roles(path)


# --- bundle ---


def test_json_is_canonical() -> None:
    a = dumps({"b": 1, "a": [dt.date(2020, 1, 2), float("nan")]})
    assert a == '{"a":["2020-01-02",null],"b":1}\n'
    assert dumps({"a": [dt.date(2020, 1, 2), float("nan")], "b": 1}) == a
    with pytest.raises(TypeError):
        jsonable(object())


def test_the_scan_counts_personal_data_without_returning_it(tmp_path: Path) -> None:
    bundle = Bundle(tmp_path / "data")
    bundle.reset()
    bundle.write("a.json", {"text": f"Call {PERSON} at someone@example.invalid", "n": 1})
    bundle.write("b/c.json", ["host 192.0.2.10", "[redacted]"])
    found = scan(bundle, REDACTOR)
    assert (found["name"], found["email"], found["ip"]) == (1, 1, 1)
    assert [name for name, _ in bundle.sizes()] == ["a.json", "b/c.json"]


# --- wells ---


def test_held_out_wellbores_are_listed_without_detail(
    con: duckdb.DuckDBPyConnection, roles: dict[str, str]
) -> None:
    entries, details = wells.export(con, roles)
    held = next(e for e in entries if e["key"] == HELD_OUT)
    assert held == {
        "key": HELD_OUT,
        "name": "XX/1-A-2",
        "split": "held_out",
        "detail": False,
        "file": None,
        "note": "Held out for evaluation; see the evaluation runs.",
    }
    assert list(details) == [f"wells/{DEV}.json"]
    assert HELD_OUT not in dumps(details)


def test_a_development_wellbore_has_its_detail(
    con: duckdb.DuckDBPyConnection, roles: dict[str, str]
) -> None:
    entries, details = wells.export(con, roles)
    entry = next(e for e in entries if e["key"] == DEV)
    assert entry["report_count"] == 3 and entry["campaigns"] == 1
    assert entry["flags"] == {"depth_not_recorded": 1}
    assert entry["first_report_date"] == dt.date(2020, 1, 2)
    d = details[f"wells/{DEV}.json"]
    assert [(p["date"], p["md_m"], p["deepest_md_m"]) for p in d["depth_time"]] == [
        (dt.date(2020, 1, 2), 500.0, 500.0),
        (dt.date(2020, 1, 3), None, 500.0),
        (dt.date(2020, 1, 4), 1500.0, 1500.0),
    ]
    assert d["depth_time"][1]["flags"] == ["depth_not_recorded"]
    assert d["lost_time"]["by_tier"] == [
        {"tier": "possible", "hours": 2.0, "activities": 2},
        {"tier": "primary", "hours": 3.5, "activities": 2},
    ]
    assert {"tier": "primary", "cause": "interruption -- wait", "hours": 2.5, "activities": 1} in (
        d["lost_time"]["by_cause"]
    )
    assert [s["section_number"] for s in d["hole_sections"]] == [1]
    assert wells.file_name("7078:T2") == "7078-T2"


# --- runs ---


@pytest.fixture
def prompt(tmp_path: Path) -> Path:
    path = tmp_path / "v1.md"
    path.write_text("You review wells.\n", encoding="utf-8")
    return path


def _document(*values: float) -> Document:
    claims = [
        {
            "id": f"c{i}",
            "type": "hours",
            "value": v,
            "unit": "h",
            "evidence_ids": ["ddr:activity:R1#1"],
            "what": {"metric": "lost_hours", "wellbore": DEV},
        }
        for i, v in enumerate(values, 1)
    ]
    return Document.model_validate(
        {
            "agent": "post_well_review",
            "title": "Fictional review",
            "sections": [
                {
                    "heading": "Lost time",
                    "sentences": [
                        {"text": f"Lost {v} h.", "claims": [c]}
                        for v, c in zip(values, claims, strict=True)
                    ],
                }
            ],
        }
    )


def _log(tmp_path: Path, prompt: Path, name: str, *, calls: bool = True) -> Run:
    clock = (dt.datetime(2020, 1, 1, tzinfo=dt.UTC) + dt.timedelta(seconds=n) for n in range(99))
    log = RunLog.create(
        tmp_path / "runs",
        agent="post_well_review",
        prompt_path=prompt,
        model="test-model",
        settings={},
        code_version="abc123",
        prices=None,
        run_id=f"run-{name.replace('/', '-')}",
        clock=lambda: next(clock),
    )
    if calls:
        task = f"Write the end-of-well review for wellbore {name}."
        log.model_call(
            request={"new_messages": [{"role": "user", "content": task}]},
            response={"stop_reason": "tool_use"},
            usage={"input_tokens": 100, "output_tokens": 20},
            latency_ms=900,
        )
        log.tool_call(
            server="ddr",
            tool="activities",
            arguments={"wellbore": name, "note": f"asked by {PERSON}"},
            result={"matched": 3, "returned": 2, "capped": False, "rows": [{"secret": 1}]},
            is_error=False,
            latency_ms=30,
        )
        first, final = _document(2.5, 9.0), _document(2.5)
        log.draft(first)
        log.check(
            [
                ClaimResult("c1", Verdict.VERIFIED, "ok", 2.5),
                ClaimResult("c2", Verdict.CONTRADICTED, "mismatch", 2.5),
            ]
        )
        log.draft(final)
        log.check([ClaimResult("c1", Verdict.VERIFIED, "ok", 2.5)])
        log.end("completed")
    else:
        log.end("failed", "BadRequestError")
    return Run.read(log.path)


def test_a_run_file_holds_steps_drafts_and_redacted_evidence(
    tmp_path: Path, prompt: Path, con: duckdb.DuckDBPyConnection
) -> None:
    run = _log(tmp_path, prompt, "XX/1-A-1")
    out = runs.export_run(run, "development", con.cursor(), REDACTOR, frozenset({HELD_OUT}))
    assert (out["wellbore_key"], out["wellbore_name"], out["status"]) == (
        DEV,
        "XX/1-A-1",
        "completed",
    )
    tool = next(s for s in out["steps"] if s["type"] == "tool_call")
    assert (tool["matched"], tool["returned"], tool["arguments"]["note"]) == (
        3,
        2,
        "asked by [redacted]",
    )
    assert "rows" not in tool and "secret" not in dumps(out)
    assert len(out["drafts"]) == 2 and out["drafts"][0]["check"]["summary"]["contradicted"] == 1
    assert out["removed_in_revision"]["claims"][0]["value"] == 9.0
    row = out["evidence"]["ddr:activity:R1#1"]
    assert (
        row["status"] == "found"
        and row["row"]["comments"] == "Waited on weather. [redacted] on deck."
    )
    entry = runs.index_entry(out)
    assert entry["file"] == "runs/run-XX-1-A-1.json"
    assert entry["first_draft_summary"]["verified"] == 1


def test_a_development_run_on_a_held_out_wellbore_is_refused(
    tmp_path: Path, prompt: Path, con: duckdb.DuckDBPyConnection
) -> None:
    run = _log(tmp_path, prompt, "XX/1-A-2")
    with pytest.raises(ValueError, match="held-out"):
        runs.export_run(run, "development", con.cursor(), REDACTOR, frozenset({HELD_OUT}))


def test_a_run_that_failed_before_any_call_has_no_wellbore(
    tmp_path: Path, prompt: Path, con: duckdb.DuckDBPyConnection
) -> None:
    run = _log(tmp_path, prompt, "none", calls=False)
    out = runs.export_run(run, "development", con.cursor(), REDACTOR, frozenset({HELD_OUT}))
    assert (out["wellbore_key"], out["status"], out["error"]) == (None, "failed", "BadRequestError")
    assert out["drafts"] == [] and out["evidence"] == {}


def _result(directory: Path, run_id: str, system: str, run: int, attempts: list[str]) -> None:
    path = directory / "runs" / system / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "system": system,
        "run": run,
        "wellbore_key": DEV,
        "wellbore_name": "XX/1-A-1",
        "status": "scored",
        "attempts": [{"run_id": a} for a in attempts],
    }
    path.write_text(json.dumps(record), encoding="utf-8")


def test_evaluation_results_place_every_attempt(tmp_path: Path) -> None:
    results = tmp_path / "r9"
    _result(results, "b", "primary", 2, ["b"])
    _result(results, "a2", "primary", 1, ["a1", "a2"])
    _result(results, "c", "baseline", 1, ["c"])
    placed = runs.evaluation_runs(results)
    assert placed["a1"].status == "rerun" and placed["a2"].status == "scored"
    exported = evaluation.export(results)
    assert exported["summary_md"] is None
    assert [r["run_id"] for r in exported["runs"]] == ["c", "a2", "b"]


# --- reconciliation ---


def test_reconciliation_gives_one_basis_and_the_override(con: duckdb.DuckDBPyConnection) -> None:
    out = reconciliation.export(con, frozenset({HELD_OUT}))
    assert out["basis"] == {
        "workbook_basis": "workbook",
        "sodir_gross_basis": "gross",
        "sodir_net_basis": "net",
    }
    assert [m["month"] for m in out["months"]] == ["2020-01", "2020-02"]
    assert "workbook_basis" not in out["months"][0]
    assert out["attribution_overrides"] == [
        {
            "attributed_wellbore_key": DEV,
            "attributed_wellbore_name": "XX/1-A-1",
            "published_npdid": 9000,
            "reason": "fictional reason",
            "months": 2,
            "first_month": "2020-01",
            "last_month": "2020-02",
        }
    ]
    with pytest.raises(ValueError, match="held-out"):
        reconciliation.export(con, frozenset({DEV}))


# --- data health ---


def test_data_health_reads_the_build_copy_not_dbt_target(
    tmp_path: Path, con: duckdb.DuckDBPyConnection
) -> None:
    """A dbt compile rewrites warehouse/target/ with results the export cannot use; the export
    reads the copy `make dbt-build` leaves beside the warehouse."""
    node = {"schema": "marts", "name": "dim_wellbore", "resource_type": "model"}
    test = {"schema": "marts", "name": "not_null_key", "resource_type": "test"}
    manifest = {"nodes": {"model.w": node, "test.w": test}}
    built = {
        "args": {"which": "build"},
        "metadata": {"dbt_version": "1.0.0", "generated_at": "2020-01-01T00:00:00Z"},
        "results": [
            {"unique_id": "model.w", "status": "success"},
            {"unique_id": "test.w", "status": "pass"},
        ],
    }
    warehouse_dir, target = tmp_path / "warehouse", tmp_path / "target"
    for directory, which in ((warehouse_dir, "build"), (target, "compile")):
        directory.mkdir()
        results = {**built, "args": {"which": which}}
        (directory / health.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        (directory / health.RUN_RESULTS).write_text(json.dumps(results), encoding="utf-8")
    with pytest.raises(ValueError, match="dbt build"):
        health.export(con, *health.load_dbt(target))
    out = health.export(con, *health.load_dbt(warehouse_dir))
    assert out["warehouse_built_at"] == "2020-01-01T00:00:00Z"
    assert out["models"] == [
        {
            "schema": "marts",
            "name": "dim_wellbore",
            "type": "model",
            "rows": 2,
            "columns": 4,
            "nulls": {"wellbore_key": 0, "wellbore_name": 0, "field_name": 0, "is_heldout": 0},
        }
    ]
    assert out["tests"]["by_type"] == [{"test": "singular", "status": "pass", "count": 1}]
    with pytest.raises(FileNotFoundError, match="make dbt-build"):
        health.load_dbt(tmp_path)
