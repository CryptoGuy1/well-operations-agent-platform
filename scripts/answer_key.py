"""Compute the evaluation answer key (evaluation/RULES.md) for every wellbore of the evaluation
population into `evaluation/answers/answer_key.jsonl`.

    uv run python scripts/answer_key.py

The key holds held-out facts: the file stays local and only counts are printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from well_ops.agents.checker import Checker
from well_ops.connectors.base import connect
from well_ops.evaluation import answer_key
from well_ops.settings import Settings

KEY_PATH = Path("evaluation/answers/answer_key.jsonl")


def main() -> int:
    settings = Settings().model_copy(update={"evaluation_mode": True})
    con = connect(settings.warehouse_path)
    keys = answer_key.compute(
        con, Checker.from_settings(settings), answer_key.population(settings.splits_path)
    )
    con.close()
    sha256 = answer_key.write(keys, KEY_PATH)
    for split in ("development", "held_out"):
        of = [k for k in keys if k.split == split]
        print(
            f"{split}: {len(of)} wellbores, {sum(len(k.facts) for k in of)} facts; left out: "
            f"{sum(k.unknown for k in of)} unknown, {sum(k.zero for k in of)} zero"
        )
    print(f"written: {KEY_PATH} (SHA-256 {sha256})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
