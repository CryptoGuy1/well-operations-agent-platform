"""Run logs (ADR 0004): build the runs database, or replay one run to Markdown.

    uv run python scripts/runs.py load
    uv run python scripts/runs.py replay <run_id> [--recheck]

Replay writes `<runs_dir>/<run_id>.md` and prints only its path and the claim counts: a log from
an evaluation run can name held-out wellbores. `--recheck` also checks the logged draft against
the current warehouse.
"""

from __future__ import annotations

import argparse
import sys

from well_ops.agents.audit_log import Run, load, replay
from well_ops.agents.checker import Checker, summary
from well_ops.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("load", help="rebuild the runs database from the run logs")
    replay_parser = commands.add_parser("replay", help="render one run to Markdown")
    replay_parser.add_argument("run_id")
    replay_parser.add_argument("--recheck", action="store_true")
    args = parser.parse_args(argv)
    settings = Settings()

    if args.command == "load":
        counts = load(settings.runs_dir, settings.runs_db_path)
        print(f"{settings.runs_db_path}: " + ", ".join(f"{n} {t}" for t, n in counts.items()))
        return 0

    log = settings.runs_dir / f"{args.run_id}.jsonl"
    if not log.is_file():
        print("no run log with this id", file=sys.stderr)
        return 1
    checker = Checker.from_settings(settings) if args.recheck else None
    out = log.with_suffix(".md")
    out.write_text(replay(log, checker), encoding="utf-8")
    results = Run.read(log).results
    counts = summary(results) if results is not None else {}
    print(f"{out}: " + (", ".join(f"{n} {v}" for v, n in counts.items()) or "no check results"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
