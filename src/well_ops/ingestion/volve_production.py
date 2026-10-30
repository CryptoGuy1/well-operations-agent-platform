"""Volve production workbook (daily and monthly sheets), staged to data/staging/production/."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

import openpyxl

from well_ops.ingestion.staging import Column, write_parquet
from well_ops.keys import wellbore_key

PRODUCTION_XLSX = Path("volve/Production_data/Volve production data.xlsx")
DAILY_SHEET = "Daily Production Data"
MONTHLY_SHEET = "Monthly Production Data"


@cache
def sheet_rows(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return {ws.title: list(ws.iter_rows(values_only=True)) for ws in workbook.worksheets}
    finally:
        workbook.close()


def cell_value(value: object) -> object:
    """D3: the text 'NULL' and empty cells are null; everything else is kept as read."""
    if value is None or (isinstance(value, str) and value.strip() in ("", "NULL")):
        return None
    return value


def number(value: object) -> float | None:
    value = cell_value(value)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    raise ValueError(f"expected a number, got {value!r}")


def text(value: object) -> str | None:
    value = cell_value(value)
    return None if value is None else str(value)


# --------------------------------------------------------------------------------------------
# Daily sheet. The workbook states no units for it; the volume unit is decided in dbt
# (int_production__daily_units_check, ADR 0002 D9), so volume columns carry no unit suffix.
# --------------------------------------------------------------------------------------------

# (staged column, workbook column, DuckDB type)
DAILY_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("source_wellbore_code", "WELL_BORE_CODE", "VARCHAR"),
    ("source_wellbore_name", "NPD_WELL_BORE_NAME", "VARCHAR"),
    ("field_code", "NPD_FIELD_CODE", "VARCHAR"),
    ("field_name", "NPD_FIELD_NAME", "VARCHAR"),
    ("facility_code", "NPD_FACILITY_CODE", "VARCHAR"),
    ("facility_name", "NPD_FACILITY_NAME", "VARCHAR"),
    ("on_stream_hours", "ON_STREAM_HRS", "DOUBLE"),
    ("avg_downhole_pressure", "AVG_DOWNHOLE_PRESSURE", "DOUBLE"),
    ("avg_downhole_temperature", "AVG_DOWNHOLE_TEMPERATURE", "DOUBLE"),
    ("avg_dp_tubing", "AVG_DP_TUBING", "DOUBLE"),
    ("avg_annulus_pressure", "AVG_ANNULUS_PRESS", "DOUBLE"),
    ("avg_choke_size", "AVG_CHOKE_SIZE_P", "DOUBLE"),
    ("avg_choke_uom", "AVG_CHOKE_UOM", "VARCHAR"),
    ("avg_whp", "AVG_WHP_P", "DOUBLE"),
    ("avg_wht", "AVG_WHT_P", "DOUBLE"),
    ("dp_choke_size", "DP_CHOKE_SIZE", "DOUBLE"),
    ("oil_volume", "BORE_OIL_VOL", "DOUBLE"),
    ("gas_volume", "BORE_GAS_VOL", "DOUBLE"),
    ("water_volume", "BORE_WAT_VOL", "DOUBLE"),
    ("water_injected_volume", "BORE_WI_VOL", "DOUBLE"),
    ("flow_kind", "FLOW_KIND", "VARCHAR"),
    ("well_type", "WELL_TYPE", "VARCHAR"),
)

DAILY_COLUMNS: tuple[Column, ...] = (
    ("production_date", "DATE"),
    ("wellbore_key", "VARCHAR"),
    ("npdid", "BIGINT"),
    *((name, sql_type) for name, _, sql_type in DAILY_FIELDS),
    ("nulled_columns", "VARCHAR[]"),  # workbook columns given as 'NULL' or empty (D3)
)


def daily_record(header: Sequence[str], row: Sequence[object]) -> tuple[object, ...]:
    cells = dict(zip(header, row, strict=True))
    produced = cells["DATEPRD"]
    if not isinstance(produced, datetime) or produced.time() != datetime.min.time():
        raise ValueError(f"DATEPRD is not a whole date: {produced!r}")
    npdid = str(cells["NPD_WELL_BORE_CODE"])
    values = [
        text(cells[source]) if sql_type == "VARCHAR" else number(cells[source])
        for _, source, sql_type in DAILY_FIELDS
    ]
    nulled = [source for _, source, _ in DAILY_FIELDS if cell_value(cells[source]) is None]
    return (produced.date(), wellbore_key(npdid), int(npdid), *values, nulled)


# --------------------------------------------------------------------------------------------
# Monthly sheet. A units row under the header states hrs and Sm3.
# --------------------------------------------------------------------------------------------

MONTHLY_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("on_stream_hours", "On Stream", "hrs"),
    ("oil_sm3", "Oil", "Sm3"),
    ("gas_sm3", "Gas", "Sm3"),
    ("water_sm3", "Water", "Sm3"),
    ("gas_injected_sm3", "GI", "Sm3"),
    ("water_injected_sm3", "WI", "Sm3"),
)

MONTHLY_COLUMNS: tuple[Column, ...] = (
    ("wellbore_key", "VARCHAR"),
    ("npdid", "BIGINT"),
    ("source_wellbore_name", "VARCHAR"),
    ("year", "INTEGER"),
    ("month", "INTEGER"),
    *((name, "DOUBLE") for name, _, _ in MONTHLY_FIELDS),
    ("nulled_columns", "VARCHAR[]"),
)


def check_monthly_units(header: Sequence[str], units: Sequence[object]) -> None:
    """Fail unless the units row states the units the staged column names promise."""
    stated = dict(zip(header, units, strict=True))
    for _, source, unit in MONTHLY_FIELDS:
        if stated[source] != unit:
            raise ValueError(f"{MONTHLY_SHEET} {source}: unit {stated[source]!r}, expected {unit}")


def monthly_record(header: Sequence[str], row: Sequence[object]) -> tuple[object, ...]:
    cells = dict(zip(header, row, strict=True))
    npdid = str(cells["NPDCode"])
    values = [number(cells[source]) for _, source, _ in MONTHLY_FIELDS]
    nulled = [source for _, source, _ in MONTHLY_FIELDS if cell_value(cells[source]) is None]
    return (
        wellbore_key(npdid),
        int(npdid),
        text(cells["Wellbore name"]),
        int(str(cells["Year"])),
        int(str(cells["Month"])),
        *values,
        nulled,
    )


def stage_production(raw_dir: Path, staging_dir: Path) -> tuple[int, int]:
    """Write the daily and monthly sheets; return their row counts."""
    sheets = sheet_rows(raw_dir / PRODUCTION_XLSX)
    out = staging_dir / "production"

    daily = sheets[DAILY_SHEET]
    header = [str(c) for c in daily[0]]
    daily_n = write_parquet(
        out / "daily.parquet", DAILY_COLUMNS, (daily_record(header, r) for r in daily[1:])
    )

    monthly = sheets[MONTHLY_SHEET]
    header = [str(c) for c in monthly[0]]
    check_monthly_units(header, monthly[1])
    monthly_n = write_parquet(
        out / "monthly.parquet", MONTHLY_COLUMNS, (monthly_record(header, r) for r in monthly[2:])
    )
    return daily_n, monthly_n
