from datetime import date
from pathlib import Path

import duckdb

from well_ops.ingestion.staging import write_parquet


def read(path: Path) -> duckdb.DuckDBPyRelation:
    relation = duckdb.sql(f"SELECT * FROM '{path}' ORDER BY ALL")
    assert relation is not None
    return relation


def test_write_parquet_keeps_declared_types_and_nulls(tmp_path: Path) -> None:
    path = tmp_path / "source" / "table.parquet"
    columns = (("key", "VARCHAR"), ("day", "DATE"), ("depth", "DOUBLE"))

    count = write_parquet(path, columns, [("a", date(2013, 3, 7), 4562.0), ("b", None, None)])

    assert count == 2
    assert not path.with_name("table.parquet.part").exists()
    relation = read(path)
    assert [str(t) for t in relation.types] == ["VARCHAR", "DATE", "DOUBLE"]
    assert relation.fetchall() == [("a", date(2013, 3, 7), 4562.0), ("b", None, None)]


def test_write_parquet_empty_table_keeps_schema(tmp_path: Path) -> None:
    path = tmp_path / "empty.parquet"

    assert write_parquet(path, (("key", "VARCHAR"), ("n", "BIGINT")), []) == 0
    assert [str(t) for t in read(path).types] == ["VARCHAR", "BIGINT"]
