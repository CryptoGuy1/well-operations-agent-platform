from datetime import date
from pathlib import Path

import duckdb
import pytest

from well_ops.ingestion.sodir_factpages import (
    TABLES,
    WELLBORE_TABLES,
    HeaderError,
    check_header,
    stage_wellbores,
)


def test_check_header_accepts_bom_and_extra_columns(tmp_path: Path) -> None:
    path = tmp_path / "field.csv"
    path.write_bytes("﻿fldName,extra,fldNpdidField\nA,b,1\n".encode())

    check_header(path, ("fldName", "fldNpdidField"))


def test_check_header_rejects_error_page(tmp_path: Path) -> None:
    path = tmp_path / "field.csv"
    path.write_text("<html><body>Service unavailable</body></html>", encoding="utf-8")

    with pytest.raises(HeaderError, match="fldName"):
        check_header(path, ("fldName",))


def test_tables_are_the_phase1_exports() -> None:
    assert [t.filename for t in TABLES] == [
        "field.csv",
        "field_production_monthly.csv",
        "field_production_gross_monthly.csv",
        "wellbore_development_all.csv",
        "wellbore_exploration_all.csv",
    ]
    assert all("rs:Format=CSV" in t.url and "Top100=false" in t.url for t in TABLES)


DEVELOPMENT_CSV = (
    "﻿wlbWellboreName,wlbWell,wlbField,wlbPurpose,wlbStatus,wlbEntryDate,"
    "wlbCompletionDate,wlbTotalDepth,wlbNpdidWellbore\n"
    "15/9-F-11,15/9-F-11,VOLVE,OBSERVATION,P&A,07.03.2013,12.05.2013,4562.0,7078\n"
)
EXPLORATION_CSV = (
    "﻿wlbWellboreName,wlbWell,wlbField,wlbPurpose,wlbStatus,wlbEntryDate,"
    "wlbCompletionDate,wlbTotalDepth,wlbNpdidWellbore\n"
    "1/1-X,1/1-X,,WILDCAT,P&A,,,,90009\n"
)


def test_stage_wellbores_parses_dates_numbers_and_blanks(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    for table, text in (("development", DEVELOPMENT_CSV), ("exploration", EXPLORATION_CSV)):
        path = raw / WELLBORE_TABLES[table]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    assert stage_wellbores(raw, tmp_path / "staging") == 2

    staged = tmp_path / "staging" / "sodir" / "wellbore.parquet"
    rows = duckdb.execute(f"SELECT * FROM '{staged}' ORDER BY npdid").fetchall()
    assert rows == [
        (
            7078,
            "15/9-F-11",
            "15/9-F-11",
            "VOLVE",
            "OBSERVATION",
            "P&A",
            date(2013, 3, 7),
            date(2013, 5, 12),
            4562.0,
            "development",
        ),
        (90009, "1/1-X", "1/1-X", None, "WILDCAT", "P&A", None, None, None, "exploration"),
    ]
