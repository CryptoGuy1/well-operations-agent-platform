"""The evaluation harness (evaluation/RULES.md): runs the primary system, the baseline and, if the
budget allows, the secondary model on the scored wellbores, scores every run and writes the
release's results.

A release runs the primary system and the baseline `RUNS_PER_WELLBORE` times per wellbore and
the secondary model `SECONDARY_RUNS_PER_WELLBORE` times, run 1 on every wellbore before run 2.
Every model call goes through the release budget guard. An infrastructure error (provider
credit, network, rate limit, provider 5xx) reruns the run, at most twice, each attempt with its
own run log; any other error stops the harness. A run without a checked first draft is a task
failure and is never rerun.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anthropic
import httpx2

from well_ops.agents.audit_log import Prices, Run, RunLog, read_events
from well_ops.agents.checker import Checker, ClaimResult, UnclaimedNumber
from well_ops.agents.post_well_review import agent as post_well_review
from well_ops.agents.revision import removed_in_revision
from well_ops.agents.runtime import ModelClient, Toolbox, run_agent
from well_ops.evaluation.answer_key import WellboreKey
from well_ops.evaluation.budget import Budget, BudgetExceeded
from well_ops.evaluation.scoring import score_draft
from well_ops.settings import Settings

# Frozen with the rules (evaluation/RULES.md).
RUNS_PER_WELLBORE = 3
SECONDARY_RUNS_PER_WELLBORE = 1
BUDGET_USD = 8.0
MAX_RERUNS = 2
PRIMARY_MODEL = "claude-haiku-5-5"
SECONDARY_MODEL = "claude-sonnet-5-5"
FROZEN_SETTINGS: dict[str, Any] = {
    "effort": None,
    "max_tokens": 128000,
    "max_steps": 20,
    "tool_row_cap": 200,
}
BASELINE_AGENT = "post_well_review_baseline"
BASELINE_PROMPT_VERSION = 1
RELEASE = re.compile(r"r[1-9]\d*")

PRIMARY, BASELINE, SECONDARY = "primary", "baseline", "secondary"
SCORED, TASK_FAILURE, INFRA_FAILURE, BUDGET_STOPPED = (
    "scored",
    "task_failure",
    "infrastructure_failure",
    "budget_stopped",
)


@dataclass(frozen=True)
class System:
    name: str  # primary, baseline or secondary
    agent: str
    prompt_path: Path
    settings: Settings  # model, prices and the system's run-log directory
    tools: bool  # connector tools; a baseline has only submit_review
    revise: bool  # the checker revision turn; baselines get none
    runs: int = RUNS_PER_WELLBORE  # runs per wellbore


def baseline_prompt(settings: Settings) -> Path:
    return settings.prompts_dir / BASELINE_AGENT / f"v{BASELINE_PROMPT_VERSION}.md"


def frozen_setting_errors(settings: Settings, model: str) -> list[str]:
    """Differences between the settings and the frozen evaluation configuration."""
    errors = [] if settings.model == model else [f"model is {settings.model!r}, not {model!r}"]
    errors += [
        f"{name} is {getattr(settings, name)!r}, not {value!r}"
        for name, value in FROZEN_SETTINGS.items()
        if getattr(settings, name) != value
    ]
    if Prices.from_settings(settings) is None:
        errors.append("prices are not set, so the budget cannot be enforced")
    return errors


def classify(error: BaseException) -> str | None:
    """The infrastructure error kind that allows a rerun, or None. A transport error of the HTTP
    library (a read timeout or a dropped connection while a response streams) is not wrapped by
    the SDK, so it is a network error too."""
    if isinstance(error, (anthropic.APIConnectionError, httpx2.TransportError)):
        return "network"
    if isinstance(error, anthropic.RateLimitError):
        return "rate_limit"
    if isinstance(error, anthropic.APIStatusError):
        if error.status_code >= 500:
            return "provider_5xx"
        if "credit balance" in str(error.message).lower():
            return "credit"
    return None


def logged_spend(runs_dir: Path) -> float:
    """USD of every model call logged under a release's run-log directory (earlier attempts of
    the same release count against its budget)."""
    total = 0.0
    for path in sorted(runs_dir.rglob("*.jsonl")) if runs_dir.exists() else []:
        for event in read_events(path):
            if event["type"] == "model_call":
                total += event["data"]["cost_usd"] or 0.0
    return total


class _AttemptFailed(Exception):
    def __init__(self, run_id: str, error: Exception) -> None:
        super().__init__(type(error).__name__)
        self.run_id = run_id
        self.error = error


async def _attempt(
    system: System,
    wellbore_name: str,
    model: ModelClient,
    servers: Mapping[str, Any],
    checker: Checker,
    code_version: str | None,
) -> Path:
    log = RunLog.create(
        system.settings.runs_dir,
        agent=system.agent,
        prompt_path=system.prompt_path,
        model=system.settings.require_model(),
        settings=post_well_review.logged_settings(system.settings),
        code_version=code_version,
        prices=Prices.from_settings(system.settings),
    )
    try:
        async with Toolbox(servers if system.tools else {}) as toolbox:
            await run_agent(
                prompt_path=system.prompt_path,
                task=post_well_review.task(wellbore_name),
                settings=system.settings,
                model=model,
                toolbox=toolbox,
                checker=checker,
                log=log,
                revise=system.revise,
            )
    except Exception as e:
        log.end("failed", error=type(e).__name__)
        raise _AttemptFailed(log.run_id, e) from e
    return log.path


def score_run(path: Path, key: WellboreKey, checker: Checker) -> dict[str, Any]:
    """Scores of one run from its log: the first draft (scored), its value-only check, and the
    final draft after checker feedback with what the revision removed."""
    run = Run.read(path)
    end = run.last("run_end") or {}
    checks = run.of_type("check")
    first = run.first_document
    scored: dict[str, Any] = {
        "run_id": run.run_id,
        "agent_status": end.get("status"),
        "agent_error": end.get("error"),
        "cost_usd": end.get("cost_usd"),
        "elapsed_ms": end.get("elapsed_ms"),
        "model_calls": end.get("model_calls"),
        "tool_calls": end.get("tool_calls"),
        "first_draft": None,
        "value_only": None,
        "final_draft": None,
        "removed": None,
    }
    if first is None or not checks:
        scored["status"] = TASK_FAILURE  # zero answer-key coverage (evaluation.report)
        return scored
    results = [ClaimResult.from_dict(r) for r in checks[0]["results"]]
    unclaimed = [UnclaimedNumber.from_dict(u) for u in checks[0].get("unclaimed", [])]
    scored["status"] = SCORED
    scored["first_draft"] = score_draft(first, results, unclaimed, key, checker).as_dict()
    value_only = checker.check(first, value_only=True)
    scored["value_only"] = score_draft(first, value_only, unclaimed, key, checker).as_dict()
    final = run.document
    if len(checks) > 1 and final is not None:
        last = [ClaimResult.from_dict(r) for r in checks[-1]["results"]]
        left = [UnclaimedNumber.from_dict(u) for u in checks[-1].get("unclaimed", [])]
        scored["final_draft"] = score_draft(final, last, left, key, checker).as_dict()
        removed = removed_in_revision(first, final)
        scored["removed"] = {
            "claims": len(removed.claims),
            "numbers": len(removed.numbers),
            "claim_ids": [c.id for c in removed.claims],
        }
    return scored


@dataclass
class Release:
    """One release's systems, scored wellbores and run settings."""

    name: str
    systems: list[System]
    keys: list[WellboreKey]
    checker: Checker
    servers: Mapping[str, Any]
    model_for: Callable[[System, WellboreKey], ModelClient]  # a budgeted client per run
    budget: Budget
    out_dir: Path
    code_version: str | None
    rerun_waits: Sequence[float] = (30.0, 120.0)
    records: list[dict[str, Any]] = field(default_factory=list)
    stopped: str | None = None  # why the release stopped early, if it did

    async def run_one(self, system: System, key: WellboreKey, n: int) -> dict[str, Any]:
        record: dict[str, Any] = {
            "system": system.name,
            "model": system.settings.model,
            "wellbore_key": key.wellbore_key,
            "wellbore_name": key.wellbore_name,
            "run": n,
            "attempts": [],
        }
        for attempt in range(MAX_RERUNS + 1):
            try:
                path = await _attempt(
                    system,
                    key.wellbore_name,
                    self.model_for(system, key),
                    self.servers,
                    self.checker,
                    self.code_version,
                )
            except _AttemptFailed as failed:
                kind = classify(failed.error)
                if isinstance(failed.error, BudgetExceeded):
                    kind = "budget"
                record["attempts"].append(
                    {"run_id": failed.run_id, "error": type(failed.error).__name__, "kind": kind}
                )
                if kind == "budget":
                    self.stopped = str(failed.error)
                    return record | {"status": BUDGET_STOPPED}
                if kind is None:
                    raise failed.error from None
                if attempt < MAX_RERUNS:
                    await asyncio.sleep(self.rerun_waits[attempt])
                    continue
                return record | {"status": INFRA_FAILURE}
            record["attempts"].append({"run_id": path.stem, "error": None, "kind": None})
            return record | score_run(path, key, self.checker)
        raise AssertionError("unreachable")

    async def run_system(self, system: System) -> None:
        for n in range(1, system.runs + 1):
            for key in self.keys:
                if self.stopped is not None:
                    return
                record = await self.run_one(system, key, n)
                self.records.append(record)
                self._write(record)

    async def run(self) -> None:
        primary_and_baseline = [s for s in self.systems if s.name in (PRIMARY, BASELINE)]
        for system in primary_and_baseline:
            await self.run_system(system)
        for system in self.systems:
            if system.name == SECONDARY and self.stopped is None:
                await self.run_system(system)

    def _write(self, record: Mapping[str, Any]) -> None:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", str(record["wellbore_key"])).strip("_")
        path = self.out_dir / "runs" / str(record["system"]) / f"{slug}-run{record['run']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
