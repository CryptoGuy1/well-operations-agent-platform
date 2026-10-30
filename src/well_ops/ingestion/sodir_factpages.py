"""Sodir FactPages: download table exports as CSV, check their headers, and stage wellbores."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from functools import partial
from pathlib import Path

from well_ops.ingestion._download import DownloadResult, fetch
from well_ops.ingestion.manifest import build_entry, utc_now
from well_ops.ingestion.staging import Column, write_parquet

SOURCE = "Sodir FactPages"
LICENCE = "NLOD 2.0"

_EXPORT = (
    "https://factpages.sodir.no/public?/Factpages/external/tableview/{report}"
    "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used"
    "&CultureCode=en&rs:Format=CSV&Top100=false"
)


@dataclass(frozen=True)
class Table:
    report: str
    required_columns: tuple[str, ...]

    @property
    def url(self) -> str:
        return _EXPORT.format(report=self.report)

    @property
    def filename(self) -> str:
        return f"{self.report}.csv"


# CSV export links, taken from the "Export: CSV" button on each FactPages table view.
TABLES: tuple[Table, ...] = (
    # Field > Table view > Overview
    # https://factpages.sodir.no/en/field/TableView/Overview
    Table("field", ("fldName", "fldCurrentActivitySatus", "fldNpdidField", "fldHcType")),
    # Field > Table view > Production > Saleable > Monthly
    # https://factpages.sodir.no/en/field/tableview/production/saleable/monthly
    Table(
        "field_production_monthly",
        (
            "prfInformationCarrier",
            "prfYear",
            "prfMonth",
            "prfPrdOilNetMillSm3",
            "prfPrdGasNetBillSm3",
            "prfPrdProducedWaterInFieldMillSm3",
            "prfNpdidInformationCarrier",
        ),
    ),
    # Field > Table view > Production > Sum wellbores > Monthly - by field
    # https://factpages.sodir.no/en/field/tableview/production/SumWellbores/Monthly
    Table(
        "field_production_gross_monthly",
        (
            "prfInformationCarrier",
            "prfYear",
            "prfMonth",
            "prfPrdOilGrossMillSm3",
            "prfPrdGasGrossBillSm3",
            "prfPrdProducedWaterInFieldMillSm3",
            "prfNpdidInformationCarrier",
        ),
    ),
    # Wellbore > Table view > Development
    # https://factpages.sodir.no/en/wellbore/TableView/Development
    Table(
        "wellbore_development_all",
        ("wlbWellboreName", "wlbField", "wlbStatus", "wlbPurpose", "wlbTotalDepth"),
    ),
    # Wellbore > Table view > Exploration > All - long list
    # https://factpages.sodir.no/en/wellbore/TableView/Exploration/All
    Table(
        "wellbore_exploration_all",
        ("wlbWellboreName", "wlbField", "wlbStatus", "wlbPurpose", "wlbTotalDepth"),
    ),
)

log = logging.getLogger(__name__)


class HeaderError(ValueError):
    pass


def check_header(path: Path, required: tuple[str, ...]) -> None:
    """Fail unless the first CSV row contains every required column. Exports start with a BOM."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh), [])
    missing = [column for column in required if column not in header]
    if missing:
        raise HeaderError(f"{path.name}: missing columns {missing}; header was {header[:10]}")


def download(data_dir: Path, tables: tuple[Table, ...] = TABLES) -> DownloadResult:
    raw_dir = data_dir / "raw" / "sodir"
    result = DownloadResult()
    for table in tables:
        dest = raw_dir / table.filename
        try:
            fetch(table.url, dest, partial(check_header, required=table.required_columns))
        except Exception as exc:
            log.error("Sodir %s failed, previous copy kept: %s", table.report, exc)
            result.failures.append(f"sodir/{table.filename}: {exc}")
            continue
        result.entries.append(build_entry(dest, data_dir, SOURCE, table.url, LICENCE, utc_now()))
        log.info("Sodir %s ok (header checked)", table.report)
    return result


# --------------------------------------------------------------------------------------------
# Wellbores (ADR 0002 D1): staged to data/staging/sodir/wellbore.parquet
# --------------------------------------------------------------------------------------------

WELLBORE_TABLES = {
    "development": Path("sodir/wellbore_development_all.csv"),
    "exploration": Path("sodir/wellbore_exploration_all.csv"),
}

WELLBORE_COLUMNS: tuple[Column, ...] = (
    ("npdid", "BIGINT"),  # wlbNpdidWellbore
    ("wellbore_name", "VARCHAR"),  # wlbWellboreName
    ("well_name", "VARCHAR"),  # wlbWell
    ("field_name", "VARCHAR"),  # wlbField; null when the wellbore belongs to no field
    ("purpose", "VARCHAR"),  # wlbPurpose
    ("status", "VARCHAR"),  # wlbStatus
    ("entry_date", "DATE"),  # wlbEntryDate
    ("completion_date", "DATE"),  # wlbCompletionDate
    ("total_depth_m", "DOUBLE"),  # wlbTotalDepth, metres as published
    ("source_table", "VARCHAR"),  # 'development' or 'exploration'
)


def read_wellbore_rows(raw_dir: Path) -> Iterator[tuple[str, dict[str, str]]]:
    """Yield (table, row) for every row of the development and exploration wellbore exports."""
    for table, path in WELLBORE_TABLES.items():
        with (raw_dir / path).open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                yield table, row


@dataclass(frozen=True)
class SodirWellbore:
    name: str
    npdid: str
    field: str


def load_sodir_wellbores(raw_dir: Path) -> list[SodirWellbore]:
    return [
        SodirWellbore(row["wlbWellboreName"], row["wlbNpdidWellbore"], row["wlbField"])
        for _, row in read_wellbore_rows(raw_dir)
    ]


def parse_date(text: str) -> date | None:
    """FactPages exports dates as dd.mm.yyyy; a blank cell is unknown."""
    return datetime.strptime(text, "%d.%m.%Y").date() if text.strip() else None


def parse_number(text: str) -> float | None:
    return float(text) if text.strip() else None


def wellbore_record(table: str, row: dict[str, str]) -> tuple[object, ...]:
    return (
        int(row["wlbNpdidWellbore"]),
        row["wlbWellboreName"],
        row["wlbWell"],
        row["wlbField"] or None,
        row["wlbPurpose"] or None,
        row["wlbStatus"] or None,
        parse_date(row["wlbEntryDate"]),
        parse_date(row["wlbCompletionDate"]),
        parse_number(row["wlbTotalDepth"]),
        table,
    )


def stage_wellbores(raw_dir: Path, staging_dir: Path) -> int:
    """Write every Sodir wellbore (all fields, not only Volve) and return the row count."""
    records = [wellbore_record(table, row) for table, row in read_wellbore_rows(raw_dir)]
    return write_parquet(staging_dir / "sodir" / "wellbore.parquet", WELLBORE_COLUMNS, records)


# --------------------------------------------------------------------------------------------
# Field production (ADR 0002 D9): staged to data/staging/sodir/field_production_*_monthly.parquet
# Volumes keep Sodir's published units in their names.
# --------------------------------------------------------------------------------------------

# Staged table -> (raw export, ((staged column, Sodir column), ...))
FIELD_PRODUCTION_TABLES: dict[str, tuple[Path, tuple[tuple[str, str], ...]]] = {
    # Saleable (net): fuel and flare deducted.
    "field_production_net_monthly": (
        Path("sodir/field_production_monthly.csv"),
        (
            ("oil_net_mill_sm3", "prfPrdOilNetMillSm3"),
            ("gas_net_bill_sm3", "prfPrdGasNetBillSm3"),
            ("ngl_net_mill_sm3", "prfPrdNGLNetMillSm3"),
            ("condensate_net_mill_sm3", "prfPrdCondensateNetMillSm3"),
            ("oe_net_mill_sm3", "prfPrdOeNetMillSm3"),
            ("produced_water_in_field_mill_sm3", "prfPrdProducedWaterInFieldMillSm3"),
        ),
    ),
    # Sum wellbores (gross).
    "field_production_gross_monthly": (
        Path("sodir/field_production_gross_monthly.csv"),
        (
            ("oil_gross_mill_sm3", "prfPrdOilGrossMillSm3"),
            ("gas_gross_bill_sm3", "prfPrdGasGrossBillSm3"),
            ("condensate_gross_mill_sm3", "prfPrdCondensateGrossMillSm3"),
            ("oe_gross_mill_sm3", "prfPrdOeGrossMillSm3"),
            ("produced_water_in_field_mill_sm3", "prfPrdProducedWaterInFieldMillSm3"),
        ),
    ),
}


def field_production_columns(volumes: tuple[tuple[str, str], ...]) -> tuple[Column, ...]:
    return (
        ("field_npdid", "BIGINT"),  # prfNpdidInformationCarrier
        ("field_name", "VARCHAR"),  # prfInformationCarrier
        ("year", "INTEGER"),
        ("month", "INTEGER"),
        *((name, "DOUBLE") for name, _ in volumes),
    )


def field_production_record(
    row: dict[str, str], volumes: tuple[tuple[str, str], ...]
) -> tuple[object, ...]:
    return (
        int(row["prfNpdidInformationCarrier"]),
        row["prfInformationCarrier"],
        int(row["prfYear"]),
        int(row["prfMonth"]),
        *(parse_number(row[source]) for _, source in volumes),
    )


def stage_field_production(raw_dir: Path, staging_dir: Path) -> dict[str, int]:
    """Write both monthly field production tables (all fields); return row counts by table."""
    counts = {}
    for table, (path, volumes) in FIELD_PRODUCTION_TABLES.items():
        with (raw_dir / path).open(encoding="utf-8-sig", newline="") as fh:
            records = [field_production_record(row, volumes) for row in csv.DictReader(fh)]
        counts[table] = write_parquet(
            staging_dir / "sodir" / f"{table}.parquet", field_production_columns(volumes), records
        )
    return counts
