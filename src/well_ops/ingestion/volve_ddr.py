"""Volve daily drilling reports: WITSML 1.4 drillReport XML files, one report per file."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

WITSML_NS = "{http://www.witsml.org/schemas/1series}"
DDR_DIR = Path("volve/Well_technical_data/Daily Drilling Report - XML Version")


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
