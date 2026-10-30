from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from well_ops.ingestion.volve_production import (
    DAILY_COLUMNS,
    DAILY_FIELDS,
    MONTHLY_COLUMNS,
    MONTHLY_FIELDS,
    cell_value,
    check_monthly_units,
    daily_record,
    monthly_record,
)

DAILY_HEADER = ["DATEPRD", "NPD_WELL_BORE_CODE", *(source for _, source, _ in DAILY_FIELDS)]
MONTHLY_HEADER = ["Wellbore name", "NPDCode", "Year", "Month", "On Stream", "Oil", "Gas", "Water",
                  "GI", "WI"]  # fmt: skip
MONTHLY_UNITS = [None, None, None, None, "hrs", "Sm3", "Sm3", "Sm3", "Sm3", "Sm3"]


def daily_row(**cells: object) -> list[object]:
    defaults: dict[str, object] = {source: None for source in DAILY_HEADER}
    defaults |= {"DATEPRD": datetime(2014, 4, 7), "NPD_WELL_BORE_CODE": "90001"}
    defaults |= {"WELL_BORE_CODE": "NO 15/9-X-1", "BORE_OIL_VOL": 1200.5, "FLOW_KIND": "production"}
    defaults |= cells
    return [defaults[c] for c in DAILY_HEADER]


@pytest.mark.parametrize("value", [None, "", " ", "NULL"])
def test_cell_value_nulls(value: object) -> None:
    assert cell_value(value) is None


def test_cell_value_keeps_zero_and_text() -> None:
    assert cell_value(0) == 0
    assert cell_value("%") == "%"


def test_daily_record_keys_types_and_nulls() -> None:
    record = daily_record(DAILY_HEADER, daily_row(BORE_GAS_VOL=0, AVG_CHOKE_UOM=""))
    row = dict(zip([name for name, _ in DAILY_COLUMNS], record, strict=True))

    assert row["production_date"] == date(2014, 4, 7)
    assert row["wellbore_key"] == "90001"
    assert row["npdid"] == 90001
    assert row["oil_volume"] == 1200.5
    assert row["gas_volume"] == 0.0
    assert row["avg_choke_uom"] is None
    nulled = row["nulled_columns"]
    assert isinstance(nulled, list)
    assert "AVG_CHOKE_UOM" in nulled and "BORE_GAS_VOL" not in nulled


def test_daily_record_rejects_text_in_number_column() -> None:
    with pytest.raises(ValueError, match="expected a number"):
        daily_record(DAILY_HEADER, daily_row(BORE_OIL_VOL="12,5"))


def test_daily_record_rejects_time_of_day() -> None:
    with pytest.raises(ValueError, match="whole date"):
        daily_record(DAILY_HEADER, daily_row(DATEPRD=datetime(2014, 4, 7, 6)))


def test_monthly_record_null_text() -> None:
    row_in = ["15/9-X-1", 90001, 2014, 4, 700.25, 31000.0, "NULL", 1500, "NULL", "NULL"]
    record = monthly_record(MONTHLY_HEADER, row_in)
    row = dict(zip([name for name, _ in MONTHLY_COLUMNS], record, strict=True))

    assert (row["wellbore_key"], row["year"], row["month"]) == ("90001", 2014, 4)
    assert row["oil_sm3"] == 31000.0
    assert row["water_sm3"] == 1500.0
    assert row["gas_sm3"] is None
    assert row["nulled_columns"] == ["Gas", "GI", "WI"]


def test_check_monthly_units() -> None:
    check_monthly_units(MONTHLY_HEADER, MONTHLY_UNITS)
    with pytest.raises(ValueError, match="Oil"):
        check_monthly_units(MONTHLY_HEADER, [*MONTHLY_UNITS[:5], "bbl", *MONTHLY_UNITS[6:]])


def test_staged_column_names_match_fields() -> None:
    assert len(MONTHLY_COLUMNS) == 6 + len(MONTHLY_FIELDS)
    assert len(DAILY_COLUMNS) == 4 + len(DAILY_FIELDS)


def test_records_write_to_parquet(tmp_path: Path) -> None:
    from well_ops.ingestion.staging import write_parquet

    path = tmp_path / "daily.parquet"
    write_parquet(path, DAILY_COLUMNS, [daily_record(DAILY_HEADER, daily_row())])
    con = duckdb.connect()
    got = con.execute(
        f"select wellbore_key, list_contains(nulled_columns, 'BORE_GAS_VOL') from '{path}'"
    ).fetchall()
    assert got == [("90001", True)]
