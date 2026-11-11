import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from well_ops.warehouse.quality import (
    MANIFEST,
    RUN_RESULTS,
    Node,
    build_sections,
    dbt_test_results,
    flag_counts,
    load_dbt,
    load_nodes,
    null_counts,
    null_value_counts,
    render_nulls,
    undeclared_array_values,
)


def node(schema: str, name: str, kind: str = "model") -> dict[str, Any]:
    return {"schema": schema, "name": name, "alias": name, "resource_type": kind}


def test_load_nodes_orders_by_layer_and_skips_tests() -> None:
    manifest = {
        "nodes": {
            "a": node("marts", "dim_a"),
            "b": node("staging", "stg_b"),
            "c": node("reference", "codes", "seed"),
            "d": node("staging", "stg_a"),
            "t": node("staging", "unique_x", "test"),
        }
    }

    assert [n.name for n in load_nodes(manifest)] == ["stg_a", "stg_b", "dim_a", "codes"]


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("create schema staging; create schema intermediate")
    con.execute(
        "create table staging.t as select * from (values (1, null), (2, 'x'), (3, null)) v(a, b)"
    )
    con.execute(
        "create table intermediate.f as select * from (values ('k1', 'late'), ('k1', 'late'), "
        "('k2', 'late'), ('k2', 'early')) v(wellbore_key, flag)"
    )
    return con


def test_null_counts(con: duckdb.DuckDBPyConnection) -> None:
    assert null_counts(con, Node("staging", "t", "model")) == (3, {"a": 0, "b": 2})


def test_render_nulls_lists_only_columns_with_nulls() -> None:
    text = render_nulls(
        [Node("staging", "t", "model"), Node("staging", "u", "model")],
        {
            Node("staging", "t", "model"): (3, {"a": 0, "b": 2}),
            Node("staging", "u", "model"): (1, {"c": 0}),
        },
    )

    assert "| `t` | `b` | 2 | 66.7% |" in text
    assert "`a`" not in text
    assert "| `u` | all 1 columns | 0 |  |" in text


def test_flag_counts(con: duckdb.DuckDBPyConnection) -> None:
    nodes = [Node("staging", "t", "model"), Node("intermediate", "f", "model")]

    assert flag_counts(con, nodes) == [("f", "early", 1, 1), ("f", "late", 3, 2)]


def test_null_value_counts_reads_witsml_sentinels(tmp_path: Path) -> None:
    con = duckdb.connect()
    con.execute("create schema staging")
    con.execute("create view staging.stg_ddr__report as select ['a', 'b'] as nulled_elements")
    for sheet in ("daily", "monthly"):
        con.execute(
            f"create view staging.stg_production__{sheet} as select ['x'] as nulled_columns"
        )
    (tmp_path / "witsml").mkdir()
    con.execute(
        "copy (select * from (values (-999.25::double, 'a'), (1.0, 'b'), (-999.25, 'c')) v(x, y)) "
        f"to '{tmp_path / 'witsml' / 'rig.parquet'}'"
    )

    rows = null_value_counts(con, tmp_path)

    assert rows == [
        ("drilling reports", "-999.99", 2),
        ("production workbook, daily", "NULL or empty", 1),
        ("production workbook, monthly", "NULL or empty", 1),
        ("WITSML rig", "-999.25", 2),
    ]


def test_undeclared_array_values() -> None:
    con = duckdb.connect()
    con.execute("create schema staging")
    con.execute(
        "create view staging.stg_witsml__log_value as select * from "
        "(values ([1.0, -9999, -9999], 2.0), ([3.0], 4.0), (null, 5.0)) v(arr, x)"
    )

    assert undeclared_array_values(con) == [("arr", 2, 1)]


def result(uid: str, status: str) -> dict[str, Any]:
    return {"unique_id": uid, "status": status, "failures": 0 if status == "pass" else 3}


def test_test_results_counts_by_type_and_requires_build() -> None:
    manifest = {
        "nodes": {
            "m": {"resource_type": "model", "name": "m"},
            "t1": {"resource_type": "test", "name": "u1", "test_metadata": {"name": "unique"}},
            "t2": {"resource_type": "test", "name": "s1", "test_metadata": None},
        }
    }
    run = {
        "args": {"which": "build"},
        "metadata": {"dbt_version": "1.0"},
        "results": [result("m", "success"), result("t1", "pass"), result("t2", "fail")],
    }

    got = dbt_test_results(run, manifest)

    assert got["statuses"] == [
        (("model", "success"), 1),
        (("test", "fail"), 1),
        (("test", "pass"), 1),
    ]
    assert got["by_type"] == [(("singular", "fail"), 1), (("unique", "pass"), 1)]
    assert got["failing"] == [("s1", "fail", 3)]
    with pytest.raises(ValueError, match="dbt build"):
        dbt_test_results({**run, "args": {"which": "compile"}}, manifest)


def test_the_report_reads_the_build_copy_not_dbt_target(tmp_path: Path) -> None:
    """A dbt compile rewrites warehouse/target/; the report reads the copy of the last build that
    `make dbt-build` leaves beside the warehouse, and never target's file names."""
    target = tmp_path / "target"
    target.mkdir()
    for name in ("manifest.json", "run_results.json"):
        (target / name).write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="make dbt-build"):
        build_sections(tmp_path / "w.duckdb", tmp_path, target)
    manifest: dict[str, Any] = {"nodes": {}}
    results = {"args": {"which": "build"}}
    (tmp_path / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / RUN_RESULTS).write_text(json.dumps(results), encoding="utf-8")
    assert load_dbt(tmp_path) == (manifest, results)
