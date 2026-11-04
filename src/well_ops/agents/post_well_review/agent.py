"""The post-well review agent (ADR 0004).

It writes the end-of-well review of one wellbore from the connector tools, with the versioned
prompt `prompts/post_well_review/v<N>.md`. The run, its drafts and their check results are written
to the run's audit log.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from well_ops.agents.audit_log import Clock, Prices, RunLog, utc_now
from well_ops.agents.checker import Checker
from well_ops.agents.runtime import ModelClient, Outcome, Toolbox, run_agent
from well_ops.settings import Settings

AGENT = "post_well_review"
PROMPT_VERSION = 2


def prompt_path(settings: Settings) -> Path:
    return settings.prompts_dir / AGENT / f"v{PROMPT_VERSION}.md"


def task(wellbore_name: str) -> str:
    return f"Write the end-of-well review for wellbore {wellbore_name}."


def logged_settings(settings: Settings) -> dict[str, Any]:
    """The settings that shape a run (prices are logged separately)."""
    return {
        "model": settings.model,
        "effort": settings.effort,
        "max_tokens": settings.max_tokens,
        "max_steps": settings.max_steps,
        "tool_row_cap": settings.tool_row_cap,
        "evaluation_mode": settings.evaluation_mode,
    }


async def review(
    wellbore_name: str,
    settings: Settings,
    *,
    model: ModelClient,
    servers: Mapping[str, Any],
    checker: Checker,
    code_version: str | None,
    clock: Clock = utc_now,
) -> Outcome:
    prompt = prompt_path(settings)
    log = RunLog.create(
        settings.runs_dir,
        agent=AGENT,
        prompt_path=prompt,
        model=settings.require_model(),
        settings=logged_settings(settings),
        code_version=code_version,
        prices=Prices.from_settings(settings),
        clock=clock,
    )
    try:
        async with Toolbox(servers) as toolbox:
            return await run_agent(
                prompt_path=prompt,
                task=task(wellbore_name),
                settings=settings,
                model=model,
                toolbox=toolbox,
                checker=checker,
                log=log,
            )
    except Exception as e:
        log.end("failed", error=type(e).__name__)
        raise
