"""Export the whole bundle (ADR 0005)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from well_ops.agents.audit_log import Run
from well_ops.connectors.base import connect
from well_ops.connectors.redaction import Redactor
from well_ops.console_data import evaluation, health, reconciliation, runs, wells
from well_ops.console_data.bundle import Bundle
from well_ops.settings import Settings

RUN_RELEASES = ("r2",)  # evaluation releases whose runs the console shows
EVALUATION_RELEASES = ("r1", "r2")  # evaluation releases whose results the console shows


def run_sources(runs_dir: Path, releases: Sequence[str]) -> list[runs.Source]:
    """Development run logs (the top level of the run-log directory), then each release's."""
    found = [runs.Source(runs.DEVELOPMENT, p) for p in sorted(runs_dir.glob("*.jsonl"))]
    for release in releases:
        found += [
            runs.Source(release, p)
            for p in sorted((runs_dir / "evaluation" / release).rglob("*.jsonl"))
        ]
    return found


def build(settings: Settings, bundle: Bundle, results_dir: Path) -> None:
    redactor = Redactor.from_file(settings.redaction_denylist_path)
    roles = wells.split_roles(settings.splits_path)
    manifest, run_results = health.load_dbt(settings.warehouse_path.parent)
    con = connect(settings.warehouse_path)
    try:
        held_out = wells.held_out_keys(con, roles)
        bundle.reset()

        entries, details = wells.export(con, roles)
        bundle.write("wells.json", entries)
        for name, value in details.items():
            bundle.write(name, value)

        placed = {r: runs.evaluation_runs(results_dir / r) for r in RUN_RELEASES}
        index = []
        for source in run_sources(settings.runs_dir, RUN_RELEASES):
            run = Run.read(source.path)
            where = None
            if source.name != runs.DEVELOPMENT:
                where = placed[source.name].get(run.run_id)
                if where is None:
                    raise ValueError(f"run {run.run_id} is not in the {source.name} results")
            exported = runs.export_run(run, source.name, con.cursor(), redactor, held_out, where)
            bundle.write(f"runs/{run.run_id}.json", exported)
            index.append(runs.index_entry(exported))
        index.sort(key=lambda e: (e["source"] != runs.DEVELOPMENT, e["source"], e["run_id"]))
        bundle.write("runs/index.json", index)

        for release in EVALUATION_RELEASES:
            bundle.write(f"evaluation/{release}.json", evaluation.export(results_dir / release))
        bundle.write("reconciliation.json", reconciliation.export(con, held_out))
        bundle.write("data_health.json", health.export(con, manifest, run_results))
    finally:
        con.close()
