"""Run the post-well review agent on one development wellbore (ADR 0004).

    uv run python scripts/review.py --wellbore "15/9-F-11 T2"

Writes the run log to `<runs_dir>/<run_id>.jsonl` and the checked review, each claim marked with
its check result, to `<runs_dir>/<run_id>.review.md`; prints their paths, the check summaries,
what the revision removed from the first draft and the run's cost. Resolves the wellbore and
applies the held-out guard before any model call, and refuses to run in evaluation mode, which
only the evaluation harness sets.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from anthropic import AsyncAnthropic

from well_ops.agents.audit_log import Run, canonical_json, code_version
from well_ops.agents.checker import Checker, summary
from well_ops.agents.post_well_review.agent import review
from well_ops.agents.render import render_document
from well_ops.agents.revision import Removed, removed_in_revision, removed_lines
from well_ops.agents.runtime import MessagesApiModel, Outcome, stdio_servers
from well_ops.connectors.base import connect, resolve_wellbore
from well_ops.connectors.errors import ToolError
from well_ops.connectors.guard import HeldOutGuard
from well_ops.settings import Settings

REPO = Path(__file__).resolve().parents[1]


def run_section(outcome: Outcome, end: dict[str, object]) -> str:
    checks = "; ".join(
        f"check {n}: " + ", ".join(f"{c} {v}" for v, c in counts.items())
        for n, counts in enumerate(outcome.checks, 1)
    )
    cost = "unknown" if end.get("cost_usd") is None else f"USD {end['cost_usd']}"
    return "\n".join(
        [
            "",
            "## Run",
            "",
            f"- Run id: `{outcome.run_id}`; status: {outcome.status}"
            + (f" ({outcome.error})" if outcome.error else ""),
            f"- Checks: {checks or 'none'}",
            f"- Model calls: {end.get('model_calls')}; tool calls: {end.get('tool_calls')}; "
            f"tokens: {canonical_json(end.get('usage'))}; cost: {cost}",
            "",
        ]
    )


def removed(outcome: Outcome) -> Removed | None:
    """What the revision removed, when the run has a revised final draft."""
    first, final = outcome.first_document, outcome.document
    if first is None or final is None or len(outcome.checks) < 2:
        return None
    return removed_in_revision(first, final)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wellbore", required=True, help="wellbore key or name")
    args = parser.parse_args(argv)
    settings = Settings()
    if settings.evaluation_mode:
        print("refused: evaluation mode is set only by the evaluation harness", file=sys.stderr)
        return 2
    try:
        settings.require_model()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    con = connect(settings.warehouse_path)
    try:
        key = resolve_wellbore(con, args.wellbore)
        HeldOutGuard.from_settings(settings).check(key)
    except ToolError as e:
        print(f"refused: {e.detail}", file=sys.stderr)
        return 2
    (name,) = con.execute(
        "select wellbore_name from marts.dim_wellbore where wellbore_key = ?", [key]
    ).fetchone() or (key,)
    con.close()

    outcome = asyncio.run(
        review(
            str(name),
            settings,
            model=MessagesApiModel(
                AsyncAnthropic(api_key=settings.provider_api_key.get_secret_value())
                if settings.provider_api_key is not None
                else None
            ),
            servers=stdio_servers(REPO),
            checker=Checker.from_settings(settings),
            code_version=code_version(REPO),
        )
    )
    end = Run.read(outcome.log_path).last("run_end") or {}
    print(f"run log: {outcome.log_path}")
    if outcome.document is not None and outcome.results is not None:
        out = outcome.log_path.with_suffix(".review.md")
        text = render_document(outcome.document, outcome.results, outcome.unclaimed)
        gone = removed(outcome)
        if gone is not None:
            text += "\n" + "\n".join(removed_lines(gone)) + "\n"
        text += run_section(outcome, end)
        out.write_text(text, encoding="utf-8")
        print(f"review: {out}")
        print("final check: " + ", ".join(f"{n} {v}" for v, n in summary(outcome.results).items()))
    for n, counts in enumerate(outcome.checks, 1):
        print(f"check {n}: " + ", ".join(f"{c} {v}" for v, c in counts.items()))
    gone = removed(outcome)
    if gone is not None:
        print(
            f"removed during revision: {len(gone.claims)} claims, {len(gone.numbers)} numbers"
            + (f" ({', '.join(gone.numbers)})" if gone.numbers else "")
        )
    print(f"status: {outcome.status}" + (f" ({outcome.error})" if outcome.error else ""))
    cost = end.get("cost_usd")
    print(
        f"tokens: {canonical_json(end.get('usage'))}; cost: "
        + ("unknown (set the WELL_OPS_PRICE_* settings)" if cost is None else f"USD {cost}")
    )
    return 0 if outcome.status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
