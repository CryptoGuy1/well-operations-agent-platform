"""Phase 2 data-quality report, computed from the built warehouse and the last `dbt build`.

Every section is aggregate: counts per model, column, flag or test, never per wellbore, so no
held-out wellbore can appear (ADR 0002 D8).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from well_ops.markdown import table

LAYERS = ("staging", "intermediate", "marts", "reference")  # report order
WIDE_MODEL_COLUMNS = 100  # models wider than this get a summary row instead of one per column
UNDECLARED_ARRAY_VALUE = -9999  # seen in array curves that declare -999.25 as their null value


@dataclass(frozen=True)
class Node:
    schema: str
    name: str
    resource_type: str  # model or seed

    @property
    def relation(self) -> str:
        return f'"{self.schema}"."{self.name}"'


def _source(*functions: str) -> str:
    return "Computed by " + ", ".join(f"`well_ops.warehouse.quality.{f}`" for f in functions) + "."


def _int(n: int | None) -> str:
    return f"{n or 0:,}"


def load_nodes(manifest: dict[str, Any]) -> list[Node]:
    """The models and seeds dbt builds, ordered by layer and name."""
    nodes = [
        Node(n["schema"], n.get("alias") or n["name"], n["resource_type"])
        for n in manifest["nodes"].values()
        if n["resource_type"] in ("model", "seed")
    ]
    return sorted(nodes, key=lambda n: (LAYERS.index(n.schema), n.name))


def _columns(con: duckdb.DuckDBPyConnection, node: Node) -> list[tuple[str, str]]:
    return [
        (name, dtype)
        for name, dtype in con.execute(
            "select column_name, data_type from information_schema.columns "
            "where table_schema = ? and table_name = ? order by ordinal_position",
            [node.schema, node.name],
        ).fetchall()
    ]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def null_counts(con: duckdb.DuckDBPyConnection, node: Node) -> tuple[int, dict[str, int]]:
    """Row count and null count per column of one model."""
    columns = [name for name, _ in _columns(con, node)]
    counts = ", ".join(f"count({_quote(c)})" for c in columns)
    row = con.execute(f"select count(*), {counts} from {node.relation}").fetchall()[0]
    rows = int(row[0])
    return rows, {c: rows - int(n) for c, n in zip(columns, row[1:], strict=True)}


def render_models(nodes: Sequence[Node], counts: dict[Node, tuple[int, dict[str, int]]]) -> str:
    rows = [
        (n.schema, f"`{n.name}`", n.resource_type, _int(counts[n][0]), len(counts[n][1]))
        for n in nodes
    ]
    return (
        table(["Layer", "Model", "Type", "Rows", "Columns"], rows)
        + "\n\n"
        + _source("load_nodes", "null_counts")
    )


def render_nulls(nodes: Sequence[Node], counts: dict[Node, tuple[int, dict[str, int]]]) -> str:
    rows = []
    wide = []
    for node in nodes:
        total, nulls = counts[node]
        if len(nulls) > WIDE_MODEL_COLUMNS:
            all_null = sum(1 for n in nulls.values() if n == total)
            cells = total * len(nulls)
            wide.append(
                (
                    f"`{node.name}`",
                    len(nulls),
                    _int(cells),
                    _int(sum(nulls.values())),
                    all_null,
                )
            )
            continue
        clean = sum(1 for n in nulls.values() if n == 0)
        with_nulls = [(c, n) for c, n in nulls.items() if n]
        if not with_nulls:
            rows.append((f"`{node.name}`", f"all {clean} columns", "0", ""))
        for column, n in with_nulls:
            share = f"{n / total:.1%}" if total else ""
            rows.append((f"`{node.name}`", f"`{column}`", _int(n), share))
    text = (
        "Columns with at least one null, per model; a model without nulls is listed once.\n\n"
        + table(["Model", "Column", "Nulls", "Share of rows"], rows)
    )
    if wide:
        text += (
            f"\n\nModels with more than {WIDE_MODEL_COLUMNS} columns, summarised (a curve "
            "absent from a log is null in that log's rows):\n\n"
            + table(["Model", "Columns", "Cells", "Null cells", "Columns wholly null"], wide)
        )
    return text + "\n\n" + _source("null_counts", "render_nulls")


def flag_counts(con: duckdb.DuckDBPyConnection, nodes: Sequence[Node]) -> list[tuple[Any, ...]]:
    """Rows and distinct wellbores per flag, for every model with a `flag` column."""
    result: list[tuple[Any, ...]] = []
    for node in nodes:
        names = {c for c, _ in _columns(con, node)}
        if "flag" not in names:
            continue
        wellbores = "count(distinct wellbore_key)" if "wellbore_key" in names else "null"
        result += [
            (node.name, *row)
            for row in con.execute(
                f"select flag, count(*), {wellbores} from {node.relation} group by flag "
                "order by flag"
            ).fetchall()
        ]
    return result


def render_flags(flags: Sequence[tuple[Any, ...]]) -> str:
    rows = [
        (f"`{model}`", f"`{flag}`", _int(n), "" if wb is None else _int(wb))
        for model, flag, n, wb in flags
    ]
    return (
        "Flags mark doubtful records; flagged records are kept as published.\n\n"
        + table(["Model", "Flag", "Rows", "Wellbores"], rows)
        + "\n\n"
        + _source("flag_counts")
    )


def null_value_counts(
    con: duckdb.DuckDBPyConnection, staging_dir: Path
) -> list[tuple[str, str, int]]:
    """Source values read as null at staging or in dbt (ADR 0002 D3, as amended).

    - Drilling reports: elements equal to -999.99, as listed in `nulled_elements`.
    - Production workbook: cells holding the text NULL or empty, as listed in `nulled_columns`.
    - WITSML objects: -999.25 in the staged numeric columns (dbt reads them as null).
    - WITSML log values: values equal to a declared null value or -999.25, counted at staging.
    """
    rows: list[tuple[str, str, int]] = []

    def total(sql: str) -> int:
        return int(con.execute(sql).fetchall()[0][0] or 0)

    rows.append(
        (
            "drilling reports",
            "-999.99",
            total('select sum(len(nulled_elements)) from "staging"."stg_ddr__report"'),
        )
    )
    for sheet in ("daily", "monthly"):
        rows.append(
            (
                f"production workbook, {sheet}",
                "NULL or empty",
                total(f'select sum(len(nulled_columns)) from "staging"."stg_production__{sheet}"'),
            )
        )
    for path in sorted((staging_dir / "witsml").glob("*.parquet")):
        described = con.execute(f"describe select * from '{path}'").fetchall()
        doubles = [row[0] for row in described if row[1] == "DOUBLE"]
        hits = " + ".join(f"count_if({_quote(c)} = -999.25)" for c in doubles) or "0"
        rows.append((f"WITSML {path.stem}", "-999.25", total(f"select {hits} from '{path}'")))
    counts = staging_dir / "witsml_log" / "log_value_count.parquet"
    if counts.exists():
        rows.append(
            (
                "WITSML log values (extracted wellbores)",
                "declared null or -999.25",
                total(f"select sum(values_nulled) from '{counts}'"),
            )
        )
    return rows


def undeclared_array_values(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int, int]]:
    """Array-curve elements equal to -9999, which the curves do not declare as null.

    They are kept as published; this counts them per curve, over all extracted wellbores.
    """
    node = Node("staging", "stg_witsml__log_value", "model")
    arrays = [name for name, dtype in _columns(con, node) if dtype.endswith("[]")]
    result = []
    for name in arrays:
        q = _quote(name)
        n, rows = con.execute(
            f"select sum(len(list_filter({q}, lambda x: x = {UNDECLARED_ARRAY_VALUE}))), "
            f"count_if(list_contains({q}, {UNDECLARED_ARRAY_VALUE})) from {node.relation}"
        ).fetchall()[0]
        result.append((name, int(n or 0), int(rows or 0)))
    return result


def render_null_values(
    nulled: Sequence[tuple[str, str, int]], arrays: Sequence[tuple[str, int, int]]
) -> str:
    text = table(
        ["Source", "Value read as null", "Values"], [(s, f"`{v}`", _int(n)) for s, v, n in nulled]
    )
    text += (
        f"\n\nArray-curve elements equal to {UNDECLARED_ARRAY_VALUE:,}, which the curves do not "
        "declare as null. They are kept as published.\n\n"
        + table(
            ["Curve", "Elements", "Rows containing one"],
            [(f"`{c}`", _int(n), _int(r)) for c, n, r in arrays],
        )
    )
    return text + "\n\n" + _source("null_value_counts", "undeclared_array_values")


def units_check(con: duckdb.DuckDBPyConnection) -> tuple[list[tuple[str, int, int]], str]:
    """The daily volume unit decision (ADR 0002 D9): agreeing and non-zero months per quantity."""
    relation = '"intermediate"."int_production__daily_units_check"'
    rows = []
    for q in ("oil", "gas", "water"):
        agree, nonzero = con.execute(
            f"select count_if({q}_agrees), count_if({q}_nonzero) from {relation}"
        ).fetchall()[0]
        rows.append((q, int(agree), int(nonzero)))
    units = con.execute(f"select distinct daily_volume_unit from {relation}").fetchall()
    return rows, ", ".join(sorted(u for (u,) in units))


def render_units_check(rows: Sequence[tuple[str, int, int]], unit: str) -> str:
    return (
        table(
            ["Quantity", "Agreeing wellbore-months", "Non-zero wellbore-months", "Share"],
            [(q, _int(a), _int(n), f"{a / n:.1%}" if n else "") for q, a, n in rows],
        )
        + f"\n\nResult: `daily_volume_unit` = `{unit}`.\n\n"
        + _source("units_check")
    )


def dbt_test_results(run_results: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """dbt build results: statuses of models, seeds and tests, and tests by type."""
    if run_results.get("args", {}).get("which") != "build":
        raise ValueError("run_results.json is not from `dbt build`; run `make dbt-build` first")
    nodes = manifest["nodes"]
    by_type: Counter[tuple[str, str]] = Counter()
    statuses: Counter[tuple[str, str]] = Counter()
    failing = []
    for result in run_results["results"]:
        node = nodes[result["unique_id"]]
        kind = node["resource_type"]
        statuses[(kind, result["status"])] += 1
        if kind == "test":
            name = (node.get("test_metadata") or {}).get("name", "singular")
            by_type[(name, result["status"])] += 1
            if result["status"] != "pass":
                failing.append((node["name"], result["status"], result.get("failures")))
    return {
        "dbt_version": run_results["metadata"]["dbt_version"],
        "statuses": sorted(statuses.items()),
        "by_type": sorted(by_type.items()),
        "failing": sorted(failing),
    }


def render_tests(results: dict[str, Any]) -> str:
    text = (
        f"From the last `dbt build` (dbt {results['dbt_version']}).\n\n"
        + table(
            ["Node type", "Status", "Count"],
            [(k, s, _int(n)) for (k, s), n in results["statuses"]],
        )
        + "\n\nTests by type:\n\n"
        + table(
            ["Test", "Status", "Count"],
            [(f"`{t}`", s, _int(n)) for (t, s), n in results["by_type"]],
        )
    )
    if results["failing"]:
        text += "\n\nTests not passing:\n\n" + table(
            ["Test", "Status", "Failing rows"],
            [(f"`{n}`", s, _int(f)) for n, s, f in results["failing"]],
        )
    else:
        text += "\n\nEvery test passed."
    return text + "\n\n" + _source("dbt_test_results")


def build_sections(database: Path, staging_dir: Path, target_dir: Path) -> dict[str, str]:
    manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    run_results = json.loads((target_dir / "run_results.json").read_text(encoding="utf-8"))
    tests = dbt_test_results(run_results, manifest)
    nodes = load_nodes(manifest)
    con = duckdb.connect(str(database), read_only=True)
    try:
        counts = {node: null_counts(con, node) for node in nodes}
        return {
            "models": render_models(nodes, counts),
            "nulls": render_nulls(nodes, counts),
            "null-values": render_null_values(
                null_value_counts(con, staging_dir), undeclared_array_values(con)
            ),
            "flags": render_flags(flag_counts(con, nodes)),
            "units-check": render_units_check(*units_check(con)),
            "tests": render_tests(tests),
        }
    finally:
        con.close()
