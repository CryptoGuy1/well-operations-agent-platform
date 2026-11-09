"""Compute the evaluation answer key (evaluation/RULES.md) for every wellbore of the evaluation
population into `evaluation/answers/answer_key.jsonl`, and its SHA-256, with the commit it was
built from, into `evaluation/answers/answer_key.sha256`.

    uv run python scripts/answer_key.py

The key holds held-out facts: the key file stays local, only its hash file is committed, and only
counts are printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from well_ops.agents.audit_log import code_version
from well_ops.agents.checker import Checker
from well_ops.connectors.base import connect
from well_ops.evaluation import answer_key
from well_ops.settings import Settings

REPO = Path(__file__).resolve().parents[1]
KEY_PATH = Path("evaluation/answers/answer_key.jsonl")
HASH_PATH = Path("evaluation/answers/answer_key.sha256")


def main() -> int:
    settings = Settings().model_copy(update={"evaluation_mode": True})
    con = connect(settings.warehouse_path)
    keys = answer_key.compute(
        con, Checker.from_settings(settings), answer_key.population(settings.splits_path)
    )
    con.close()
    sha256 = answer_key.write(keys, KEY_PATH)
    record = answer_key.KeyHash(sha256, code_version(REPO))
    HASH_PATH.write_text(record.dumps(KEY_PATH.name), encoding="utf-8")
    for split in ("development", "held_out"):
        of = [k for k in keys if k.split == split]
        print(
            f"{split}: {len(of)} wellbores, {sum(len(k.facts) for k in of)} facts; left out: "
            f"{sum(k.unknown for k in of)} unknown, {sum(k.zero for k in of)} zero"
        )
    print(f"written: {KEY_PATH} and {HASH_PATH} (SHA-256 {sha256}, built from {record.built_from})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
