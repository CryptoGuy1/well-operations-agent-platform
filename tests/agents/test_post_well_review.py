"""Post-well review agent tests with a scripted model and a stand-in connector server (fictional
data; no network). The checker runs on the synthetic warehouse of tests/conftest.py."""

from __future__ import annotations

import asyncio
import datetime as dt
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
from anthropic.types import Message

from well_ops.agents.audit_log import read_events
from well_ops.agents.checker import METRICS, Checker, Verdict
from well_ops.agents.post_well_review.agent import AGENT, PROMPT_VERSION, prompt_path, review
from well_ops.agents.runtime import Outcome, Toolbox, stdio_servers
from well_ops.connectors.base import READ_ONLY, ConnectorServer
from well_ops.settings import Settings

REPO = Path(__file__).parents[2]
SECTION2 = "ddr:hole-section:9001:T2#2"


def fake_drilling_reports() -> ConnectorServer:
    server = ConnectorServer("fake-ddr")

    @server.tool(annotations=READ_ONLY)
    def hole_sections(wellbore_key: str) -> dict[str, Any]:
        """Hole sections of a wellbore."""
        return {"rows": [{"evidence_id": SECTION2, "section_number": 2, "hole_size_in": 12.25}]}

    return server


def document(size: float) -> dict[str, Any]:
    claim = {
        "id": "c1",
        "type": "hole_size_in",
        "value": size,
        "unit": "in",
        "evidence_ids": [SECTION2],
        "what": {"metric": "section_hole_size", "wellbore": "9001:T2", "section": 2},
    }
    sentence = {"text": f"Section 2 was drilled in {size} in hole.", "claims": [claim]}
    return {
        "agent": AGENT,
        "title": "Fictional review",
        "sections": [{"heading": "Hole sections", "sentences": [sentence]}],
    }


def message(n: int, *blocks: dict[str, Any], stop: str = "tool_use") -> Message:
    return Message.model_validate(
        {
            "id": f"msg_{n}",
            "type": "message",
            "role": "assistant",
            "model": "test-model",
            "content": list(blocks),
            "stop_reason": stop,
            "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 100, "cache_read_input_tokens": 0},
        }
    )


def use(name: str, arguments: dict[str, Any], n: int = 0) -> dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_{name}_{n}", "name": name, "input": arguments}


def submit(size: float, n: int = 0) -> dict[str, Any]:
    return use("submit_review", document(size), n)


class ScriptedModel:
    """Returns the scripted responses in order and records every request."""

    def __init__(self, *responses: Message) -> None:
        self._responses: Iterator[Message] = iter(responses)
        self.requests: list[dict[str, Any]] = []

    async def create(self, params: Mapping[str, Any]) -> Message:
        self.requests.append({**params, "messages": list(params["messages"])})
        return next(self._responses)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        model="test-model",
        runs_dir=tmp_path / "runs",
        prompts_dir=REPO / "prompts",
        max_steps=6,
        price_input_per_mtok_usd=10.0,
        price_output_per_mtok_usd=50.0,
        price_checked_on=dt.date(2020, 1, 1),
    )


def run(settings: Settings, model: ScriptedModel, checker: Checker) -> Outcome:
    return asyncio.run(
        review(
            "XX/1-A-1 T2",
            settings,
            model=model,
            servers={"drilling_reports": fake_drilling_reports()},
            checker=checker,
            code_version="abc123",
        )
    )


def last_user_blocks(request: Mapping[str, Any]) -> list[dict[str, Any]]:
    content = request["messages"][-1]["content"]
    assert request["messages"][-1]["role"] == "user" and isinstance(content, list)
    return content


def test_a_checked_review(settings: Settings, checker: Checker) -> None:
    model = ScriptedModel(
        message(1, use("hole_sections", {"wellbore_key": "9001:T2"})),
        message(2, submit(12.25)),
    )
    outcome = run(settings, model, checker)

    assert (outcome.status, outcome.error) == ("completed", None)
    assert outcome.results is not None and outcome.results[0].verdict is Verdict.VERIFIED
    first, second = model.requests
    assert first["system"] == prompt_path(settings).read_text(encoding="utf-8")
    assert first["messages"] == [
        {"role": "user", "content": "Write the end-of-well review for wellbore XX/1-A-1 T2."}
    ]
    assert first["cache_control"] == {"type": "ephemeral"}
    assert "temperature" not in first and "output_config" not in first
    assert {t["name"] for t in first["tools"]} == {"hole_sections", "submit_review"}
    (result,) = last_user_blocks(second)
    assert result["tool_use_id"] == "toolu_hole_sections_0" and SECTION2 in result["content"]

    events = read_events(outcome.log_path)
    assert [e["type"] for e in events] == [
        "run_start",
        "model_call",
        "tool_call",
        "model_call",
        "draft",
        "check",
        "run_end",
    ]
    assert events[2]["data"]["evidence_ids"] == [SECTION2]
    # Two calls of 1000 input and 100 output tokens at USD 10 and 50 per million.
    assert events[-1]["data"]["cost_usd"] == 0.03


def test_contradicted_claims_get_one_revision_without_the_answer(
    settings: Settings, checker: Checker
) -> None:
    model = ScriptedModel(message(1, submit(9.875)), message(2, submit(12.25, 1)))
    outcome = run(settings, model, checker)

    assert outcome.status == "completed"
    assert [c["contradicted"] for c in outcome.checks] == [1, 0]
    assert outcome.results is not None and outcome.results[0].verdict is Verdict.VERIFIED
    received, findings = last_user_blocks(model.requests[1])
    assert received["type"] == "tool_result" and not received["is_error"]
    assert "- c1: contradicted, outside_tolerance" in findings["text"]
    assert "12.25" not in findings["text"]  # the recomputed value is never handed over
    types = [e["type"] for e in read_events(outcome.log_path)]
    assert types.count("draft") == 2 and types.count("check") == 2


def test_what_remains_after_the_revision_is_reported(settings: Settings, checker: Checker) -> None:
    model = ScriptedModel(message(1, submit(9.875)), message(2, submit(9.875, 1)))
    outcome = run(settings, model, checker)

    assert outcome.status == "completed" and len(model.requests) == 2  # one revision only
    assert outcome.results is not None and outcome.results[0].verdict is Verdict.CONTRADICTED


def test_unclaimed_numbers_and_unsupported_claims_trigger_the_revision(
    settings: Settings, checker: Checker
) -> None:
    loose = document(12.25)
    loose["sections"][0]["sentences"].append({"text": "It took 7 days."})
    model = ScriptedModel(message(1, use("submit_review", loose)), message(2, submit(12.25, 1)))
    outcome = run(settings, model, checker)

    assert [c["unclaimed_number"] for c in outcome.checks] == [1, 0]
    _, findings = last_user_blocks(model.requests[1])
    assert "unclaimed number '7' in section 1, sentence 2" in findings["text"]


def test_an_invalid_document_goes_back_as_a_tool_error(
    settings: Settings, checker: Checker
) -> None:
    model = ScriptedModel(
        message(1, use("submit_review", {"agent": AGENT, "title": "t"})),
        message(2, submit(12.25)),
    )
    outcome = run(settings, model, checker)

    (error,) = last_user_blocks(model.requests[1])
    assert error["is_error"] and "sections" in error["content"]
    assert outcome.status == "completed" and outcome.checks == [
        {
            "verified": 1,
            "contradicted": 0,
            "unsupported": 0,
            "unverifiable": 0,
            "unclaimed_number": 0,
        }
    ]


def test_a_text_answer_is_asked_to_submit(settings: Settings, checker: Checker) -> None:
    model = ScriptedModel(
        message(1, {"type": "text", "text": "Here is the review."}, stop="end_turn"),
        message(2, submit(12.25)),
    )
    assert run(settings, model, checker).status == "completed"
    assert "submit_review" in model.requests[1]["messages"][-1]["content"]


def test_the_step_budget_stops_the_run(settings: Settings, checker: Checker) -> None:
    calls = [message(n, use("hole_sections", {"wellbore_key": "9001:T2"}, n)) for n in range(6)]
    outcome = run(settings, ScriptedModel(*calls), checker)

    assert (outcome.status, outcome.error, outcome.document) == ("stopped", "max_steps", None)
    end = read_events(outcome.log_path)[-1]
    assert end["type"] == "run_end" and end["data"]["model_calls"] == 6


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_refusal_and_truncation_fail_the_run(
    settings: Settings, checker: Checker, stop: str
) -> None:
    model = ScriptedModel(message(1, submit(12.25), stop=stop))
    outcome = run(settings, model, checker)
    assert (outcome.status, outcome.error, outcome.document) == ("failed", stop, None)


def _prompt_metrics(version: int) -> set[str]:
    text = (REPO / "prompts" / AGENT / f"v{version}.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| ([a-z_]+) \| [a-z0-9_]+ \|", text, re.M))


def test_the_prompts_name_only_checkable_metrics() -> None:
    for frozen in (1, 2):  # earlier prompts are never edited; later metrics are new
        assert _prompt_metrics(frozen) <= set(METRICS) | {"well_duration"}
    assert _prompt_metrics(PROMPT_VERSION) == set(METRICS)


def test_tool_names_must_be_unique() -> None:
    async def open_two() -> None:
        servers = {"a": fake_drilling_reports(), "b": fake_drilling_reports()}
        async with Toolbox(servers):
            pass

    with pytest.raises(ValueError, match="not unique"):
        asyncio.run(open_two())


def test_servers_do_not_get_the_provider_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setenv("WELL_OPS_TOOL_ROW_CAP", "50")
    params = stdio_servers(REPO)
    assert set(params) == {"drilling_reports", "production", "sodir", "realtime"}
    env = params["production"].env or {}
    assert "ANTHROPIC_API_KEY" not in env and env["WELL_OPS_TOOL_ROW_CAP"] == "50"
