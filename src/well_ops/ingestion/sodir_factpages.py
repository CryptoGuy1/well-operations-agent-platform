"""Sodir FactPages: download table exports as CSV and check their headers."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from well_ops.ingestion._download import DownloadResult, fetch
from well_ops.ingestion.manifest import build_entry, utc_now

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
