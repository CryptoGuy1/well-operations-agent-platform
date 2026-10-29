from pathlib import Path

import pytest

from well_ops.ingestion.sodir_factpages import TABLES, HeaderError, check_header


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
