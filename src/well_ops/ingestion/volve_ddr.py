"""Volve daily drilling reports: WITSML 1.4 drillReport XML files, one report per file.

`stage_drill_reports` writes two tables to data/staging/ddr/ (ADR 0002 D3, D5): report (one
row per file) and activity (one row per activity). Values stay as the report states them, with
two conversions only: timestamps are stored in UTC with the original offset kept beside them,
and -999.99 becomes null, with the nulled elements listed per report. The D4 flags are computed
in dbt (int_ddr__report_flag).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from well_ops.ingestion.identifiers import NameObservation, build_aliases
from well_ops.ingestion.sodir_factpages import load_sodir_wellbores
from well_ops.ingestion.staging import Column, to_utc, write_parquet

WITSML_NS = "{http://www.witsml.org/schemas/1series}"
DDR_DIR = Path("volve/Well_technical_data/Daily Drilling Report - XML Version")
SENTINEL = "-999.99"  # statusInfo value meaning "not recorded" (D3)


def _tag(element: ET.Element) -> str:
    return element.tag.replace(WITSML_NS, "")


def _text(element: ET.Element, name: str) -> str | None:
    return element.findtext(f"{WITSML_NS}{name}")


@dataclass(frozen=True)
class Activity:
    start: datetime
    end: datetime
    fields: dict[str, str]

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


@dataclass(frozen=True)
class DrillReport:
    file: str
    wellbore: str
    npdid: str | None
    start: datetime
    end: datetime
    spud: datetime | None
    status: dict[str, tuple[str, str | None, str | None]]  # element -> (text, uom, datum)
    activities: list[Activity]


def parse_drill_report(path: Path) -> DrillReport:
    root = ET.parse(path).getroot()
    report = root.find(f"{WITSML_NS}drillReport")
    if report is None:
        raise ValueError(f"{path.name}: no drillReport element")
    npdid = None
    for alias in report.findall(f"{WITSML_NS}wellboreAlias"):
        if _text(alias, "namingSystem") == "NPD number":
            npdid = _text(alias, "name")
    status: dict[str, tuple[str, str | None, str | None]] = {}
    status_element = report.find(f"{WITSML_NS}statusInfo")
    if status_element is not None:
        for child in status_element:
            status[_tag(child)] = ((child.text or "").strip(), child.get("uom"), child.get("datum"))
    spud_text = report.findtext(f"{WITSML_NS}wellboreInfo/{WITSML_NS}dTimSpud")
    activities = []
    for element in report.findall(f"{WITSML_NS}activity"):
        fields = {_tag(child): (child.text or "").strip() for child in element}
        for child in element:
            if child.get("uom"):
                fields[f"{_tag(child)}@uom"] = child.get("uom", "")
        activities.append(
            Activity(
                start=datetime.fromisoformat(fields["dTimStart"]),
                end=datetime.fromisoformat(fields["dTimEnd"]),
                fields=fields,
            )
        )
    return DrillReport(
        file=path.name,
        wellbore=_text(report, "nameWellbore") or "",
        npdid=npdid,
        start=datetime.fromisoformat(_text(report, "dTimStart") or ""),
        end=datetime.fromisoformat(_text(report, "dTimEnd") or ""),
        spud=datetime.fromisoformat(spud_text) if spud_text else None,
        status=status,
        activities=activities,
    )


def load_drill_reports(raw_dir: Path) -> list[DrillReport]:
    return [parse_drill_report(p) for p in sorted((raw_dir / DDR_DIR).glob("*.xml"))]


def split_code(code: str) -> tuple[str, str]:
    category, sep, subcategory = code.partition(" -- ")
    return (category, subcategory) if sep else (code, "")


# --------------------------------------------------------------------------------------------
# Staging (data/staging/ddr/)
# --------------------------------------------------------------------------------------------

# statusInfo depth and hole elements (audit section 1.4): element -> (column, expected uom).
STATUS_FIELDS: dict[str, tuple[str, str]] = {
    "md": ("md_m", "m"),
    "tvd": ("tvd_m", "m"),
    "mdPlanned": ("md_planned_m", "m"),
    "distDrill": ("dist_drill_m", "m"),
    "diaHole": ("dia_hole_in", "in"),
    "mdDiaHoleStart": ("md_dia_hole_start_m", "m"),
    "diaPilot": ("dia_pilot_in", "in"),
    "mdCsgLast": ("md_csg_last_m", "m"),
    "tvdCsgLast": ("tvd_csg_last_m", "m"),
    "mdKickoff": ("md_kickoff_m", "m"),
    "mdPlugTop": ("md_plug_top_m", "m"),
    "elevKelly": ("elev_kelly_m", "m"),
    "waterDepth": ("water_depth_m", "m"),
}
REPORT_COLUMNS: tuple[Column, ...] = (
    ("report_file", "VARCHAR"),
    ("wellbore_key", "VARCHAR"),
    ("source_wellbore_name", "VARCHAR"),  # nameWellbore as written in the report
    ("start_utc", "TIMESTAMP"),
    ("start_offset", "VARCHAR"),  # original UTC offset, e.g. '+02:00'
    ("end_utc", "TIMESTAMP"),
    ("end_offset", "VARCHAR"),
    ("report_spud_utc", "TIMESTAMP"),  # wellboreInfo/dTimSpud as stated in the report
    ("report_spud_offset", "VARCHAR"),
    ("dia_hole_start_utc", "TIMESTAMP"),  # statusInfo/dTimDiaHoleStart
    ("dia_hole_start_offset", "VARCHAR"),
    *((column, "DOUBLE") for column, _ in STATUS_FIELDS.values()),
    ("activities", "INTEGER"),
    ("nulled_elements", "VARCHAR"),  # elements above given as -999.99, comma-separated (D3)
)

ACTIVITY_COLUMNS: tuple[Column, ...] = (
    ("report_file", "VARCHAR"),
    ("activity_number", "INTEGER"),  # position in the report, from 1
    ("wellbore_key", "VARCHAR"),
    ("start_utc", "TIMESTAMP"),
    ("start_offset", "VARCHAR"),
    ("end_utc", "TIMESTAMP"),
    ("end_offset", "VARCHAR"),
    ("duration_hours", "DOUBLE"),
    ("md_m", "DOUBLE"),
    ("phase", "VARCHAR"),
    ("proprietary_code", "VARCHAR"),
    ("category", "VARCHAR"),
    ("subcategory", "VARCHAR"),
    ("state", "VARCHAR"),
    ("state_detail", "VARCHAR"),
    ("comments", "VARCHAR"),
)


def optional_timestamp(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def status_value(report: DrillReport, element: str, uom: str) -> float | None:
    """A statusInfo number, or null when absent or -999.99 (D3). A unit other than the one
    the audit found stops the run rather than mixing units."""
    if element not in report.status:
        return None
    text, found_uom, _ = report.status[element]
    if found_uom != uom:
        raise ValueError(f"{report.file}: {element} in {found_uom!r}, expected {uom!r}")
    return None if text in (SENTINEL, "") else float(text)


def report_record(report: DrillReport, key: str) -> tuple[object, ...]:
    start, end = to_utc(report.start), to_utc(report.end)
    dia_hole_start = optional_timestamp(report.status.get("dTimDiaHoleStart", ("",))[0])
    return (
        report.file,
        key,
        report.wellbore,
        *start,
        *end,
        *to_utc(report.spud),
        *to_utc(dia_hole_start),
        *(status_value(report, e, uom) for e, (_, uom) in STATUS_FIELDS.items()),
        len(report.activities),
        ", ".join(e for e in STATUS_FIELDS if report.status.get(e, ("",))[0] == SENTINEL) or None,
    )


def activity_records(report: DrillReport, key: str) -> list[tuple[object, ...]]:
    records: list[tuple[object, ...]] = []
    for number, activity in enumerate(report.activities, start=1):
        fields = activity.fields
        if fields.get("md@uom", "m") != "m":
            raise ValueError(f"{report.file}: activity {number} md in {fields['md@uom']!r}")
        code = fields.get("proprietaryCode", "")
        category, subcategory = split_code(code)
        md = fields.get("md", "")
        records.append(
            (
                report.file,
                number,
                key,
                *to_utc(activity.start),
                *to_utc(activity.end),
                activity.duration.total_seconds() / 3600,
                None if md in (SENTINEL, "") else float(md),
                fields.get("phase") or None,
                code or None,
                category or None,
                subcategory or None,
                fields.get("state") or None,
                fields.get("stateDetailActivity") or None,
                fields.get("comments") or None,
            )
        )
    return records


@dataclass(frozen=True)
class StagedReports:
    reports: int
    activities: int
    wellbore_keys: int


def wellbore_keys(
    reports: Iterable[DrillReport], raw_dir: Path
) -> dict[tuple[str, str | None], str]:
    """D1 key per (nameWellbore, NPD number), resolved like the alias table. A report whose
    wellbore cannot be keyed stops the run."""
    observations = {NameObservation("DDR", r.wellbore, r.npdid) for r in reports}
    keys = {}
    for alias in build_aliases(observations, load_sodir_wellbores(raw_dir)):
        if alias.wellbore_key is None:
            raise ValueError(f"drilling report wellbore has no D1 key: {alias.source_name!r}")
        keys[(alias.source_name, str(alias.source_npdid) if alias.source_npdid else None)] = (
            alias.wellbore_key
        )
    return keys


def stage_drill_reports(
    raw_dir: Path, staging_dir: Path, reports: list[DrillReport]
) -> StagedReports:
    keys = wellbore_keys(reports, raw_dir)
    report_rows: list[tuple[object, ...]] = []
    activity_rows: list[tuple[object, ...]] = []
    for report in reports:
        key = keys[(report.wellbore, report.npdid)]
        report_rows.append(report_record(report, key))
        activity_rows.extend(activity_records(report, key))
    out = staging_dir / "ddr"
    write_parquet(out / "report.parquet", REPORT_COLUMNS, report_rows)
    write_parquet(out / "activity.parquet", ACTIVITY_COLUMNS, activity_rows)
    return StagedReports(
        reports=len(report_rows),
        activities=len(activity_rows),
        wellbore_keys=len(set(keys.values())),
    )
