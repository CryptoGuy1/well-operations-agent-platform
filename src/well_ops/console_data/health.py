"""data_health.json: aggregate counts only (row, null and flag counts, dbt test results), the
warehouse build time recorded by dbt and the versions of the tools that built it."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import duckdb

from well_ops.warehouse.quality import (
    WIDE_MODEL_COLUMNS,
    dbt_test_results,
    flag_counts,
    load_nodes,
    null_counts,
)

# Written by `make dbt-build` beside the warehouse; warehouse/target/ is rewritten by every dbt
# command, a compile included, so it is never read here.
RUN_RESULTS, MANIFEST = "dbt_run_results.json", "dbt_manifest.json"


def load_dbt(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """The manifest and run results of the last `dbt build`, from the warehouse directory."""
    paths = [directory / MANIFEST, directory / RUN_RESULTS]
    if not all(p.is_file() for p in paths):
        raise FileNotFoundError(f"{RUN_RESULTS} or {MANIFEST} is missing; run `make dbt-build`")
    manifest, run_results = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    return manifest, run_results


def export(
    con: duckdb.DuckDBPyConnection, manifest: dict[str, Any], run_results: dict[str, Any]
) -> dict[str, Any]:
    nodes = load_nodes(manifest)
    models = []
    for node in nodes:
        rows, nulls = null_counts(con, node)
        entry: dict[str, Any] = {
            "schema": node.schema,
            "name": node.name,
            "type": node.resource_type,
            "rows": rows,
            "columns": len(nulls),
        }
        if len(nulls) > WIDE_MODEL_COLUMNS:  # summarised, as in the data-quality report
            entry["null_cells"] = sum(nulls.values())
            entry["columns_wholly_null"] = sum(n == rows for n in nulls.values()) if rows else 0
        else:
            entry["nulls"] = nulls
        models.append(entry)
    tests = dbt_test_results(run_results, manifest)
    return {
        "warehouse_built_at": run_results["metadata"]["generated_at"],
        "versions": {
            "dbt": tests["dbt_version"],
            "duckdb": version("duckdb"),
            "well_ops": version("well-ops"),
        },
        "models": models,
        "flags": [
            {"model": m, "flag": f, "rows": n, "wellbores": wb}
            for m, f, n, wb in flag_counts(con, nodes)
        ],
        "tests": {
            "statuses": [{"type": k, "status": s, "count": n} for (k, s), n in tests["statuses"]],
            "by_type": [{"test": t, "status": s, "count": n} for (t, s), n in tests["by_type"]],
            "failing": [{"test": t, "status": s, "failures": f} for t, s, f in tests["failing"]],
        },
    }
