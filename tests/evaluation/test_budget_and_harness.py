"""Budget guard, error classification, reruns and the summary, with fictional prices and
scripted attempts (no provider calls)."""

from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import anthropic
import httpx2 as httpx
import pytest
from anthropic.types import Message

from well_ops.agents.audit_log import Prices
from well_ops.evaluation import harness, report
from well_ops.evaluation.answer_key import WellboreKey
from well_ops.evaluation.budget import Budget, BudgetedModel, BudgetExceeded, call_bound
from well_ops.settings import SecondarySettings, Settings


@pytest.fixture(autouse=True)
def no_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)  # settings read no .env file


# Fictional prices: 1/5 per million tokens, 2/10 above 1000 prompt tokens, cache 1.25/0.1.
PRICES = Prices(1.0, 5.0, dt.date(2020, 1, 1), 1.25, 0.1, 1000, 2.0, 10.0, 2.5, 0.2)


def test_the_call_bound_takes_the_highest_prices() -> None:
    # 1000 prompt tokens + 10 % at USD 2.5, 100 output tokens at USD 10, per million.
    assert call_bound(PRICES, 1000, 100) == pytest.approx((1100 * 2.5 + 100 * 10) / 1e6)


def _message(input_tokens: int, output_tokens: int) -> Message:
    return Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "test-model",
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }
    )


class CountingModel:
    def __init__(self, prompt: int) -> None:
        self.prompt = prompt
        self.calls = 0

    async def count_tokens(self, params: Mapping[str, Any]) -> int:
        return self.prompt

    async def create(self, params: Mapping[str, Any]) -> Message:
        self.calls += 1
        return _message(self.prompt, 100)


def test_the_budget_stops_before_a_call_that_could_exceed_it() -> None:
    inner = CountingModel(500)
    # Bound: (550 * 2.5 + 1000 * 10) / 1e6 = 0.011375.
    budget = Budget(cap_usd=0.02)
    model = BudgetedModel(inner, inner, budget, PRICES, max_tokens=1000)
    asyncio.run(model.create({}))
    assert inner.calls == 1 and budget.spent_usd == pytest.approx((500 * 1 + 100 * 5) / 1e6)
    budget.spent_usd = 0.01
    with pytest.raises(BudgetExceeded):
        asyncio.run(model.create({}))
    assert inner.calls == 1  # the call was not made


REQUEST = httpx.Request("POST", "https://example.invalid/v1/messages")


def _status_error(cls: type[anthropic.APIStatusError], status: int, text: str) -> Exception:
    response = httpx.Response(status, request=REQUEST)
    return cls(text, response=response, body=None)


def test_infrastructure_errors_are_classified() -> None:
    assert harness.classify(anthropic.APIConnectionError(request=REQUEST)) == "network"
    assert harness.classify(_status_error(anthropic.RateLimitError, 429, "slow")) == "rate_limit"
    server = _status_error(anthropic.InternalServerError, 503, "down")
    assert harness.classify(server) == "provider_5xx"
    credit = _status_error(anthropic.BadRequestError, 400, "Your credit balance is too low")
    assert harness.classify(credit) == "credit"
    assert harness.classify(_status_error(anthropic.BadRequestError, 400, "bad input")) is None
    assert harness.classify(ValueError("x")) is None


def test_transport_errors_while_streaming_are_network_errors() -> None:
    errors = [
        httpx.ReadTimeout("timed out", request=REQUEST),
        httpx.ConnectTimeout("timed out", request=REQUEST),
        httpx.RemoteProtocolError("incomplete chunked read", request=REQUEST),
        httpx.ReadError("connection reset", request=REQUEST),
    ]
    assert [harness.classify(e) for e in errors] == ["network"] * 4


KEY = WellboreKey("9001:T2", "XX/1-A-1 T2", "development", [1], [])


def _release(tmp_path: Path, **overrides: Any) -> harness.Release:
    settings = Settings(model="test-model", runs_dir=tmp_path / "runs")
    system = harness.System(
        "primary", "post_well_review", tmp_path / "v.md", settings, tools=True, revise=True, runs=2
    )
    values: dict[str, Any] = {
        "name": "r1",
        "systems": [system],
        "keys": [KEY],
        "checker": None,
        "servers": {},
        "model_for": lambda s, k: None,
        "budget": Budget(1.0),
        "out_dir": tmp_path / "out",
        "code_version": None,
        "rerun_waits": (0.0, 0.0),
    }
    return harness.Release(**(values | overrides))


def _script(monkeypatch: pytest.MonkeyPatch, errors: list[Exception | None]) -> list[int]:
    """Attempts raise the scripted errors in order (None: the attempt succeeds)."""
    attempts: list[int] = []

    async def attempt(*args: Any) -> Path:
        attempts.append(1)
        error = errors.pop(0)
        if error is not None:
            raise harness._AttemptFailed(f"run{len(attempts)}", error)
        return Path(f"run{len(attempts)}.jsonl")

    monkeypatch.setattr(harness, "_attempt", attempt)
    monkeypatch.setattr(harness, "score_run", lambda path, key, checker: {"status": "scored"})
    return attempts


def test_an_infrastructure_error_is_rerun_at_most_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    network = anthropic.APIConnectionError(request=REQUEST)
    _script(monkeypatch, [network, network, None, network, network, network])
    release = _release(tmp_path)
    asyncio.run(release.run())
    first, second = release.records
    assert first["status"] == "scored" and [a["kind"] for a in first["attempts"]] == [
        "network",
        "network",
        None,
    ]
    assert second["status"] == "infrastructure_failure" and len(second["attempts"]) == 3
    assert (tmp_path / "out" / "runs" / "primary" / "9001_T2-run2.json").exists()


def test_the_budget_stops_the_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = _script(monkeypatch, [None, BudgetExceeded("cap")])
    release = _release(tmp_path)
    asyncio.run(release.run())
    assert [r["status"] for r in release.records] == ["scored", "budget_stopped"]
    assert release.stopped == "cap" and len(attempts) == 2


def test_an_unknown_error_stops_the_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script(monkeypatch, [ValueError("bug")])
    with pytest.raises(ValueError, match="bug"):
        asyncio.run(_release(tmp_path).run())


def test_frozen_settings_are_enforced(tmp_path: Path) -> None:
    settings = Settings(model="claude-haiku-5-5", effort="high", runs_dir=tmp_path)
    errors = harness.frozen_setting_errors(settings, harness.PRIMARY_MODEL)
    assert errors == [
        "effort is 'high', not None",
        "prices are not set, so the budget cannot be enforced",
    ]


def test_the_secondary_settings_replace_model_and_prices(tmp_path: Path) -> None:
    base = Settings(
        model="primary-model",
        price_input_per_mtok_usd=1.0,
        price_output_per_mtok_usd=5.0,
        price_checked_on=dt.date(2020, 1, 1),
        runs_dir=tmp_path,
    )
    assert SecondarySettings(model=None).apply(base) is None
    secondary = SecondarySettings(
        model="secondary-model",
        price_input_per_mtok_usd=3.0,
        price_output_per_mtok_usd=15.0,
        price_checked_on=dt.date(2020, 1, 2),
    ).apply(base)
    assert secondary is not None and secondary.model == "secondary-model"
    assert secondary.price_output_per_mtok_usd == 15.0 and secondary.runs_dir == tmp_path
    with pytest.raises(ValueError, match="together"):
        SecondarySettings(model="m", price_input_per_mtok_usd=3.0).apply(base)


def test_a_task_failure_counts_as_zero_coverage() -> None:
    draft = {"coverage": {"rate": 0.5}}
    records: list[dict[str, Any]] = [
        {"status": "scored", "first_draft": draft},
        {"status": "task_failure", "first_draft": None},
    ]
    get = report.draft_rows("first_draft")[4][1]
    assert report.cell(records, get, report.PERCENT) == "25.0 % (0.0 % to 50.0 %)"
    accuracy = report.draft_rows("first_draft")[0][1]
    scored: list[dict[str, Any]] = [
        {"status": "scored", "first_draft": {"accuracy": 0.9}},
        records[1],
    ]
    assert report.cell(scored, accuracy, report.PERCENT) == "90.0 %, n=1"
