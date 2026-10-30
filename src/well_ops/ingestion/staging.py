"""Write typed Parquet files to data/staging/ (ADR 0003).

Each staging table declares its columns and DuckDB types up front, so the Parquet schema never
depends on the values that happen to be present.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

Column = tuple[str, str]  # (name, DuckDB type)


def write_parquet(path: Path, columns: Sequence[Column], rows: Iterable[Sequence[Any]]) -> int:
    """Write rows to a Parquet file with the declared schema and return the row count.

    The file is written next to its destination and renamed into place, so a failed write
    leaves any previous file untouched.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    definition = ", ".join(f'"{name}" {sql_type}' for name, sql_type in columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [list(row) for row in rows]
    target = part.as_posix().replace("'", "''")
    with duckdb.connect() as con:
        con.execute(f"CREATE TABLE staged ({definition})")
        if values:
            con.executemany(f"INSERT INTO staged VALUES ({placeholders})", values)
        con.execute(f"COPY staged TO '{target}' (FORMAT parquet)")
    os.replace(part, path)
    return len(values)


def to_utc(moment: datetime | None) -> tuple[datetime | None, str | None]:
    """(naive UTC timestamp, original offset as '+HH:MM'). Timestamps without an offset are
    rejected: their UTC time is unknown (D5)."""
    if moment is None:
        return None, None
    offset = moment.utcoffset()
    if offset is None:
        raise ValueError(f"timestamp without a UTC offset: {moment.isoformat()}")
    minutes = int(offset.total_seconds()) // 60
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return moment.astimezone(UTC).replace(tzinfo=None), f"{sign}{hours:02d}:{rest:02d}"
