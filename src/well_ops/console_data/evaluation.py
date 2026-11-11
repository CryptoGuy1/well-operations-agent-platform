"""evaluation/<release>.json from the committed results of one evaluation release."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export(results_dir: Path) -> dict[str, Any]:
    """The release's summary (None when the release stopped before writing one) and every run
    result, sorted by system, wellbore name, run number and run id."""
    summary = results_dir / "summary.md"
    runs = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(results_dir.glob("runs/*/*.json"))
    ]
    runs.sort(key=lambda r: (r["system"], r["wellbore_name"], r["run"], r["run_id"]))
    return {
        "release": results_dir.name,
        "summary_md": summary.read_text(encoding="utf-8") if summary.exists() else None,
        "runs": runs,
    }
