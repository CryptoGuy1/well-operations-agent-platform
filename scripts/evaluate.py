"""Run one evaluation release (evaluation/RULES.md).

    uv run python scripts/evaluate.py --release r1
    uv run python scripts/evaluate.py --release r1 --dry-run --wellbores "15/9-F-11 T2" \\
        --out <directory>

A release runs the primary system, the baseline and, if the budget allows, the secondary model on
the held-out wellbores in evaluation mode, and writes `evaluation/results/<release>/`: one JSON
file per run and `summary.md`. It refuses settings that differ from the frozen configuration, a
working tree with uncommitted changes, an answer key whose rebuilt SHA-256 differs from the
committed `evaluation/answers/answer_key.sha256`, and a release that already has results.
Only counts are printed: results name held-out wellbores.

A dry run uses a stub model (no provider calls) on development wellbores only, outside evaluation
mode, and writes to `--out`.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
from pathlib import Path

from anthropic import AsyncAnthropic

from well_ops.agents.audit_log import Prices, code_version, sha256_file
from well_ops.agents.checker import Checker
from well_ops.agents.post_well_review import agent as post_well_review
from well_ops.agents.runtime import MessagesApiModel, stdio_servers
from well_ops.connectors.base import connect
from well_ops.evaluation import answer_key, harness, report
from well_ops.evaluation.budget import Budget, BudgetedModel
from well_ops.evaluation.stub import StubModel
from well_ops.settings import SecondarySettings, Settings

REPO = Path(__file__).resolve().parents[1]
KEY_PATH = Path("evaluation/answers/answer_key.jsonl")
HASH_PATH = Path("evaluation/answers/answer_key.sha256")
RULES_PATH = Path("evaluation/RULES.md")
RESULTS_DIR = Path("evaluation/results")


def fail(message: str) -> int:
    print(f"refused: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True, help="release name, r1, r2, ...")
    parser.add_argument("--dry-run", action="store_true", help="stub model, development wellbores")
    parser.add_argument("--wellbores", nargs="+", help="dry run only: development wellbores")
    parser.add_argument("--out", type=Path, help="dry run only: output directory")
    args = parser.parse_args(argv)
    if not harness.RELEASE.fullmatch(args.release):
        return fail("a release is named r1, r2, ...")
    if args.dry_run != bool(args.wellbores) or args.dry_run != (args.out is not None):
        return fail("--wellbores and --out are for a dry run, and a dry run needs both")

    base = Settings()
    if base.evaluation_mode:
        return fail("evaluation mode is set by the harness, not by the environment")
    version = code_version(REPO)
    if not args.dry_run:
        errors = harness.frozen_setting_errors(base, harness.PRIMARY_MODEL)
        if version is None or version.endswith("-dirty"):
            errors.append("the working tree has uncommitted changes")
        if errors:
            return fail("; ".join(errors))
    out_dir: Path = args.out if args.dry_run else RESULTS_DIR / args.release
    if out_dir.exists():
        return fail(f"{out_dir} exists; every release is run once")
    runs_dir = out_dir / "logs" if args.dry_run else base.runs_dir / "evaluation" / args.release

    # The answer key: the local file must have the committed hash, and the key rebuilt from the
    # warehouse must have it too (a dry run, outside evaluation mode, rebuilds its wellbores only).
    if not KEY_PATH.exists() or not HASH_PATH.exists():
        return fail(f"{KEY_PATH} or {HASH_PATH} is missing; run make answer-key")
    committed = answer_key.KeyHash.read(HASH_PATH)
    keys = answer_key.read(KEY_PATH)
    if sha256_file(KEY_PATH) != committed.sha256:
        return fail(f"{KEY_PATH} does not have the SHA-256 in {HASH_PATH}")
    split = "development" if args.dry_run else "held_out"
    key_settings = base.model_copy(update={"evaluation_mode": not args.dry_run})
    checker = Checker.from_settings(key_settings)
    con = connect(base.warehouse_path)
    if args.dry_run:
        wanted = [checker.wellbore_key(name) for name in args.wellbores]
        scored = [k for w in wanted for k in keys if k.wellbore_key == w and k.split == split]
        if len(scored) != len(args.wellbores):
            return fail("a dry run takes development wellbores of the answer key only")
        now = answer_key.compute(
            con, checker, [(k.wellbore_key, k.wellbore_name, k.split) for k in scored]
        )
        stale = answer_key.dumps(now) != answer_key.dumps(scored)
    else:
        scored = [k for k in keys if k.split == split]
        rebuilt = answer_key.compute(con, checker, answer_key.population(base.splits_path))
        stale = answer_key.sha256(rebuilt) != committed.sha256
    con.close()
    if stale:
        return fail(f"the rebuilt answer key does not have the SHA-256 in {HASH_PATH}")

    # The systems.
    def system_settings(settings: Settings, name: str) -> Settings:
        update = {"evaluation_mode": not args.dry_run, "runs_dir": runs_dir / name}
        if args.dry_run:
            update["model"] = f"stub-{name}"
        return settings.model_copy(update=update)

    primary = system_settings(base, harness.PRIMARY)
    systems = [
        harness.System(
            harness.PRIMARY,
            post_well_review.AGENT,
            post_well_review.prompt_path(base),
            primary,
            tools=True,
            revise=True,
        ),
        harness.System(
            harness.BASELINE,
            harness.BASELINE_AGENT,
            harness.baseline_prompt(base),
            system_settings(base, harness.BASELINE),
            tools=False,
            revise=False,
        ),
    ]
    secondary = base if args.dry_run else SecondarySettings().apply(base)
    if secondary is not None:
        if not args.dry_run:
            errors = harness.frozen_setting_errors(secondary, harness.SECONDARY_MODEL)
            if errors:
                return fail("secondary: " + "; ".join(errors))
        systems.append(
            harness.System(
                harness.SECONDARY,
                post_well_review.AGENT,
                post_well_review.prompt_path(base),
                system_settings(secondary, harness.SECONDARY),
                tools=True,
                revise=True,
                runs=harness.SECONDARY_RUNS_PER_WELLBORE,
            )
        )

    budget = Budget(harness.BUDGET_USD, harness.logged_spend(runs_dir))
    client = (
        None
        if args.dry_run
        else MessagesApiModel(
            AsyncAnthropic(api_key=base.provider_api_key.get_secret_value())
            if base.provider_api_key is not None
            else None
        )
    )

    def model_for(system: harness.System, key: answer_key.WellboreKey) -> BudgetedModel:
        prices = Prices.from_settings(system.settings)
        assert prices is not None
        if client is None:
            stub = StubModel(key, checker, agent=system.agent, with_evidence=system.tools)
            return BudgetedModel(stub, stub, budget, prices, system.settings.max_tokens)
        return BudgetedModel(client, client, budget, prices, system.settings.max_tokens)

    release = harness.Release(
        name=args.release,
        systems=systems,
        keys=scored,
        checker=checker,
        servers=stdio_servers(REPO, evaluation_mode=not args.dry_run),
        model_for=model_for,
        budget=budget,
        out_dir=out_dir,
        code_version=version,
        rerun_waits=(0.0, 0.0) if args.dry_run else (30.0, 120.0),
    )
    out_dir.mkdir(parents=True)
    asyncio.run(release.run())

    title = f"Evaluation release {args.release}"
    if args.dry_run:
        title = f"DRY RUN with a stub model, not a result: {title}"
    setup = [
        f"- Date: {dt.datetime.now(dt.UTC).date().isoformat()}; code version: `{version}`",
        f"- Rules: `{RULES_PATH}` (SHA-256 `{sha256_file(RULES_PATH)[:12]}`)",
        f"- Answer key: SHA-256 `{committed.sha256}`, built from commit "
        f"`{committed.built_from or 'unknown'}` (`{HASH_PATH}`)",
        f"- Scored wellbores: {len(scored)} ({split})",
        *(
            f"- {s.name}: model `{s.settings.model}`, prompt `{s.prompt_path}` (SHA-256 "
            f"`{sha256_file(s.prompt_path)[:12]}`), "
            + ("connector tools and one revision turn" if s.tools else "no tools, no revision")
            + f"; {s.runs} runs per wellbore"
            for s in systems
        ),
        f"- Settings: effort {primary.effort or 'default'}, max_tokens {primary.max_tokens}, "
        f"max_steps {primary.max_steps}, tool_row_cap {primary.tool_row_cap}",
        f"- Budget: USD {harness.BUDGET_USD} cap; USD {budget.spent_usd:.4f} spent",
    ]
    text = report.summary(
        title=title,
        setup=setup,
        records=release.records,
        keys=scored,
        planned={s.name: len(scored) * s.runs for s in systems},
        stopped=release.stopped,
    )
    (out_dir / "summary.md").write_text(text, encoding="utf-8")
    for system in systems:
        records = [r for r in release.records if r["system"] == system.name]
        counts = ", ".join(f"{sum(r['status'] == s for r in records)} {s}" for s in report.STATUSES)
        print(f"{system.name}: {len(records)} runs ({counts})")
    print(f"spent: USD {budget.spent_usd:.4f} of {harness.BUDGET_USD}")
    if release.stopped:
        print(f"stopped early: {release.stopped}")
    print(f"summary: {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
