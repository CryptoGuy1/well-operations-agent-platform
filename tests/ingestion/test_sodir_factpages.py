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


NET_CSV = (
    "﻿prfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,"
    "prfPrdNGLNetMillSm3,prfPrdCondensateNetMillSm3,prfPrdOeNetMillSm3,"
    "prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier\n"
    "FIELD X,2014,4,0.10301,0.01,0,0,0.11301,0.0215,90100\n"
)
GROSS_CSV = (
    "﻿prfInformationCarrier,prfYear,prfMonth,prfPrdOilGrossMillSm3,prfPrdGasGrossBillSm3,"
    "prfPrdCondensateGrossMillSm3,prfPrdOeGrossMillSm3,prfPrdProducedWaterInFieldMillSm3,"
    "prfNpdidInformationCarrier\n"
    "FIELD X,2014,4,0.10412,0.0151,0,0.11922,0.0215,90100\n"
)


def test_stage_field_production(tmp_path: Path) -> None:
    from well_ops.ingestion.sodir_factpages import FIELD_PRODUCTION_TABLES, stage_field_production

    raw = tmp_path / "raw"
    for table, text in (
        ("field_production_net_monthly", NET_CSV),
        ("field_production_gross_monthly", GROSS_CSV),
    ):
        path = raw / FIELD_PRODUCTION_TABLES[table][0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    counts = stage_field_production(raw, tmp_path / "staging")

    assert counts == {"field_production_net_monthly": 1, "field_production_gross_monthly": 1}
    con = duckdb.connect()
    net = tmp_path / "staging" / "sodir" / "field_production_net_monthly.parquet"
    assert con.execute(
        f"select field_npdid, year, month, oil_net_mill_sm3, gas_net_bill_sm3 from '{net}'"
    ).fetchall() == [(90100, 2014, 4, 0.10301, 0.01)]
