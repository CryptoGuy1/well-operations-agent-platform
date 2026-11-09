"""Run audit log, loader, rendering and replay tests (fictional runs and data)."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from well_ops.agents.audit_log import (
    LogIntegrityError,
    Prices,
    RunLog,
    evidence_ids,
    load,
    read_events,
    replay,
)
from well_ops.agents.checker import Checker, ClaimResult, Verdict
from well_ops.agents.render import render_document
from well_ops.agents.schema import Document

T2 = "9001:T2"
DOCUMENT = {
    "agent": "post_well_review",
    "title": "Fictional post-well review",
    "sections": [
        {
            "heading": "Lost time",
            "sentences": [
                {
                    "text": "Section 2 lost 3.5 h to repairs | pipes.",
                    "claims": [
                        {
                            "id": "c1",
                            "type": "hours",
                            "value": 3.5,
                            "unit": "h",
                            "evidence_ids": [f"ddr:lost-time:{T2}#2|interruption -- repair"],
                            "what": {
                                "metric": "lost_hours",
                                "wellbore": T2,
                                "tier": "primary",
                                "section": 2,
                            },
                        },
                        {
                            "id": "c2",
                            "type": "count",
                            "value": 7,
                            "evidence_ids": [f"well:wellbore:{T2}"],
                            "what": {"metric": "report_count", "wellbore": T2},
                        },
                    ],
                }
            ],
        }
    ],
}
PRICES = Prices(10.0, 50.0, dt.date(2020, 1, 1))  # fictional prices
TOOL_RESULT = {
    "rows": [
        {"evidence_ids": ["b", "a"], "x": 1},
        {"evidence_id": "c", "nested": {"deepest_md_evidence_id": "d"}},
    ]
}


@pytest.fixture
def clock() -> Iterator[dt.datetime]:
    start = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    return (start + dt.timedelta(seconds=n) for n in range(1000))


@pytest.fixture
def prompt(tmp_path: Path) -> Path:
    path = tmp_path / "v1.md"
    path.write_text("You review wells.\n", encoding="utf-8")
    return path


def _run(tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker) -> RunLog:
    log = RunLog.create(
        tmp_path / "runs",
        agent="post_well_review",
        prompt_path=prompt,
        model="test-model",
        settings={"effort": None, "max_steps": 5},
        code_version="abc123",
        prices=PRICES,
        run_id="run-1",
        clock=lambda: next(clock),
    )
    log.model_call(
        request={"messages": 1},
        response={"stop": "tool_use"},
        usage={"input_tokens": 100, "output_tokens": 20},
        latency_ms=900,
    )
    log.tool_call(
        server="ddr",
        tool="lost_time",
        arguments={"wellbore_key": T2},
        result=TOOL_RESULT,
        is_error=False,
        latency_ms=30,
    )
    log.model_call(
        request={"messages": 3},
        response={"stop": "end_turn"},
        usage={"input_tokens": 300, "output_tokens": 50},
        latency_ms=1100,
    )
    document = Document.model_validate(DOCUMENT)
    log.draft(document)
    log.check(checker.check(document))
    log.end("completed")
    return log


def test_a_run_is_a_hash_chained_sequence(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    events = read_events(log.path)
    assert [e["type"] for e in events] == [
        "run_start",
        "model_call",
        "tool_call",
        "model_call",
        "draft",
        "check",
        "run_end",
    ]
    start, tool, end = events[0]["data"], events[2]["data"], events[-1]["data"]
    assert len(start["prompt_sha256"]) == 64 and start["code_version"] == "abc123"
    assert tool["evidence_ids"] == ["a", "b", "c", "d"] and len(tool["result_sha256"]) == 64
    assert end["usage"] == {"input_tokens": 400, "output_tokens": 70}
    # 100 * 10 / 1e6 + 20 * 50 / 1e6 = 0.002, and 300 * 10 / 1e6 + 50 * 50 / 1e6 = 0.0055.
    assert [e["data"]["cost_usd"] for e in events if e["type"] == "model_call"] == [0.002, 0.0055]
    assert (end["cost_usd"], end["model_calls"], end["tool_calls"]) == (0.0075, 2, 1)
    assert start["prices"] == {
        "input_per_mtok_usd": 10.0,
        "output_per_mtok_usd": 50.0,
        "checked_on": "2020-01-01",
        "cache_write_per_mtok_usd": None,
        "cache_read_per_mtok_usd": None,
        "threshold_tokens": None,
        "above_input_per_mtok_usd": None,
        "above_output_per_mtok_usd": None,
        "above_cache_write_per_mtok_usd": None,
        "above_cache_read_per_mtok_usd": None,
    }
    assert end["elapsed_ms"] == 6000 and events[-1]["at"] == "2020-01-01T00:00:06+00:00"


def test_a_run_file_is_never_reused(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    _run(tmp_path, prompt, clock, checker)
    with pytest.raises(FileExistsError):
        RunLog.create(
            tmp_path / "runs",
            agent="x",
            prompt_path=prompt,
            model="m",
            settings={},
            code_version=None,
            prices=None,
            run_id="run-1",
        )


def test_only_approvals_follow_the_end(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    reopened = RunLog.open(log.path, clock=lambda: next(clock))
    with pytest.raises(LogIntegrityError):
        reopened.draft(Document.model_validate(DOCUMENT))
    reopened.approval(decision="approved", reviewer="reviewer-1")
    assert read_events(log.path)[-1]["type"] == "approval"


@pytest.mark.parametrize("edit", ["change", "remove", "swap"])
def test_edits_break_the_chain(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker, edit: str
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    if edit == "change":
        lines[1] = lines[1].replace('"latency_ms":900', '"latency_ms":901')
    elif edit == "remove":
        del lines[2]
    else:
        lines[1], lines[2] = lines[2], lines[1]
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(LogIntegrityError):
        read_events(log.path)


def test_unknown_cost_stays_unknown(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime]
) -> None:
    log = RunLog.create(
        tmp_path,
        agent="a",
        prompt_path=prompt,
        model="m",
        settings={},
        code_version=None,
        prices=None,
        run_id="r",
        clock=lambda: next(clock),
    )
    log.model_call(
        request={}, response={}, usage={"input_tokens": 5, "output_tokens": 1}, latency_ms=1
    )
    log.end("failed", error="max_steps")
    end = read_events(log.path)[-1]["data"]
    assert end["cost_usd"] is None and end["usage"] == {"input_tokens": 5, "output_tokens": 1}


def test_token_kinds_without_a_price_make_cost_unknown(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime]
) -> None:
    log = RunLog.create(
        tmp_path,
        agent="a",
        prompt_path=prompt,
        model="m",
        settings={},
        code_version=None,
        prices=PRICES,
        run_id="r",
        clock=lambda: next(clock),
    )
    usage = {"input_tokens": 5, "output_tokens": 1, "cache_read_input_tokens": 0}
    log.model_call(request={}, response={}, usage=usage, latency_ms=1)
    log.model_call(
        request={}, response={}, usage={**usage, "cache_read_input_tokens": 9}, latency_ms=1
    )
    log.end("completed")
    events = read_events(log.path)
    assert [e["data"]["cost_usd"] for e in events if e["type"] == "model_call"] == [0.0001, None]
    assert events[-1]["data"]["cost_usd"] is None


def test_cache_tokens_are_priced_when_cache_prices_are_set() -> None:
    prices = Prices(10.0, 50.0, dt.date(2020, 1, 1), 12.5, 1.0)
    usage = {"input_tokens": 100, "output_tokens": 10, "cache_creation_input_tokens": 1000}
    # 100 * 10 + 10 * 50 + 1000 * 12.5, per million tokens.
    assert prices.cost({**usage, "cache_read_input_tokens": 2000}) == 0.016


def test_a_call_above_the_threshold_is_priced_at_the_upper_tier() -> None:
    # Fictional prices: 10/50/12.5/1 per million tokens, 20/75/25/2 above 1000 prompt tokens.
    prices = Prices(10.0, 50.0, dt.date(2020, 1, 1), 12.5, 1.0, 1000, 20.0, 75.0, 25.0, 2.0)
    # Prompt 100 + 400 + 500 = 1000 tokens: not above the threshold.
    at = {"input_tokens": 100, "cache_creation_input_tokens": 400, "cache_read_input_tokens": 500}
    assert prices.cost({**at, "output_tokens": 10}) == 0.007
    # Prompt 1001 tokens: every token at the upper tier, output included.
    above = {**at, "input_tokens": 101, "output_tokens": 10}
    assert prices.cost(above) == 0.01377
    assert Prices.from_dict(prices.as_dict()) == prices


def test_a_missing_upper_tier_price_makes_cost_unknown() -> None:
    prices = Prices(10.0, 50.0, dt.date(2020, 1, 1), 12.5, 1.0, 1000, 20.0, 75.0)
    assert prices.cost({"input_tokens": 100, "cache_read_input_tokens": 1000}) is None
    assert prices.cost({"input_tokens": 100, "cache_read_input_tokens": 900}) == 0.0019


def test_tokens_are_always_logged(tmp_path: Path, prompt: Path) -> None:
    log = RunLog.create(
        tmp_path,
        agent="a",
        prompt_path=prompt,
        model="m",
        settings={},
        code_version=None,
        prices=None,
        run_id="r",
    )
    with pytest.raises(ValueError, match="input_tokens"):
        log.model_call(request={}, response={}, usage={"output_tokens": 1}, latency_ms=1)


def test_evidence_ids_are_collected_at_any_depth() -> None:
    assert evidence_ids(TOOL_RESULT) == ["a", "b", "c", "d"]


def test_load_builds_the_runs_database(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    RunLog.open(log.path, clock=lambda: next(clock)).approval(
        decision="rejected", reviewer="reviewer-1", note="report count wrong"
    )
    db = tmp_path / "runs.duckdb"
    assert load(tmp_path / "runs", db) == {"runs": 1, "events": 8, "tool_calls": 1, "claims": 2}
    con = duckdb.connect(str(db), read_only=True)
    run = con.execute(
        "select status, input_tokens, cost_usd, claims, verified, contradicted, approval from runs"
    ).fetchall()
    assert run == [("completed", 400, 0.0075, 2, 1, 1, "rejected")]
    claims = con.execute("select claim_id, verdict, expected from claims order by 1").fetchall()
    assert claims == [("c1", "verified", "3.5"), ("c2", "contradicted", "3")]


def test_load_refuses_a_broken_log(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    with log.path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"seq": 99}) + "\n")
    with pytest.raises(LogIntegrityError):
        load(tmp_path / "runs", tmp_path / "runs.duckdb")


def test_render_marks_each_claim_and_needs_every_result() -> None:
    document = Document.model_validate(DOCUMENT)
    results = [
        ClaimResult("c1", Verdict.VERIFIED, "within_tolerance", 3.5),
        ClaimResult("c2", Verdict.CONTRADICTED, "outside_tolerance", 3),
    ]
    text = render_document(document, results)
    assert "repairs | pipes. [c1: verified] [c2: CONTRADICTED]" in text
    assert "| c2 | count | report_count | 7 | 3 | CONTRADICTED | outside_tolerance |" in text
    assert "`ddr:lost-time:9001:T2#2\\|interruption -- repair`" in text  # pipe escaped
    with pytest.raises(ValueError, match="every claim"):
        render_document(document, results[:1])


def test_replay_from_the_log_alone(
    tmp_path: Path,
    prompt: Path,
    clock: Iterator[dt.datetime],
    checker: Checker,
    warehouse: Path,
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    warehouse.unlink()  # replay does not need the warehouse
    prompt.unlink()  # nor the prompt file
    text = replay(log.path)
    assert text.startswith("# Run run-1\n")
    assert "- Agent: `post_well_review`; model: `test-model`" in text
    assert "| 1 | ddr | lost_time |" in text
    assert "## Fictional post-well review" in text and "### Lost time" in text
    assert "[c2: CONTRADICTED]" in text


def test_replay_rechecks_against_the_current_warehouse(
    tmp_path: Path, prompt: Path, clock: Iterator[dt.datetime], checker: Checker
) -> None:
    log = _run(tmp_path, prompt, clock, checker)
    assert "All 2 results are unchanged." in replay(log.path, checker)

    # A log whose results no longer hold (here: logged as verified, now contradicted).
    stale = RunLog.create(
        tmp_path / "runs",
        agent="a",
        prompt_path=prompt,
        model="m",
        settings={},
        code_version=None,
        prices=None,
        run_id="run-2",
        clock=lambda: next(clock),
    )
    document = Document.model_validate(DOCUMENT)
    stale.draft(document)
    logged: list[Any] = [
        ClaimResult(c.id, Verdict.VERIFIED, "within_tolerance") for c in document.claims()
    ]
    stale.check(logged)
    text = replay(stale.path, checker)
    assert "| c2 | verified | contradicted | different |" in text
    assert "| c1 |" not in text.split("Re-check")[1]
