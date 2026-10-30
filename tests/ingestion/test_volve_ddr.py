"""Drilling report staging, on hand-written reports for 15/9-F-11 T2 and a fictional wellbore."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

from well_ops.ingestion.sodir_factpages import WELLBORE_TABLES
from well_ops.ingestion.staging import to_utc
from well_ops.ingestion.volve_ddr import (
    DDR_DIR,
    load_drill_reports,
    parse_drill_report,
    stage_drill_reports,
    status_value,
)

REPORT = """<?xml version="1.0" encoding="ISO-8859-1"?>
<witsml:drillReports xmlns:witsml="http://www.witsml.org/schemas/1series"><witsml:drillReport>
<witsml:nameWellbore>{name}</witsml:nameWellbore>
<witsml:dTimStart>{start}</witsml:dTimStart>
<witsml:dTimEnd>{end}</witsml:dTimEnd>
<witsml:wellboreAlias><witsml:name>{npdid}</witsml:name>
<witsml:namingSystem>NPD number</witsml:namingSystem></witsml:wellboreAlias>
<witsml:wellboreInfo><witsml:dTimSpud>2009-12-01T00:00:00+01:00</witsml:dTimSpud></witsml:wellboreInfo>
<witsml:statusInfo>
<witsml:md uom="m">{md}</witsml:md>
<witsml:mdPlanned uom="m">-999.99</witsml:mdPlanned>
<witsml:diaHole uom="in">8.5</witsml:diaHole>
<witsml:dTimDiaHoleStart>2009-12-20T12:00:00+01:00</witsml:dTimDiaHoleStart>
</witsml:statusInfo>
{activities}
</witsml:drillReport></witsml:drillReports>"""

ACTIVITY = (
    "<witsml:activity><witsml:dTimStart>{start}</witsml:dTimStart>"
    "<witsml:dTimEnd>{end}</witsml:dTimEnd><witsml:md uom='m'>1200</witsml:md>"
    "<witsml:phase>fixed</witsml:phase>"
    "<witsml:proprietaryCode>{code}</witsml:proprietaryCode>"
    "<witsml:state>ok</witsml:state><witsml:stateDetailActivity>success</witsml:stateDetailActivity>"
    "<witsml:comments>Synthetic activity for a test.</witsml:comments></witsml:activity>"
)

DAY = ("2010-01-01T00:00:00+01:00", "2010-01-02T00:00:00+01:00")
FULL_DAY = [
    ("2010-01-01T00:00:00+01:00", "2010-01-01T06:00:00+01:00", "drilling -- drill"),
    ("2010-01-01T06:00:00+01:00", "2010-01-02T00:00:00+01:00", "interruption -- repair"),
]
WITH_GAP = [
    ("2010-01-01T00:00:00+01:00", "2010-01-01T06:00:00+01:00", "drilling -- drill"),
    ("2010-01-01T07:00:00+01:00", "2010-01-02T00:00:00+01:00", "drilling -- trip"),
]


def write_report(
    raw: Path,
    file: str,
    name: str,
    npdid: str,
    activities: list[tuple[str, str, str]],
    md: str = "1500",
    day: tuple[str, str] = DAY,
) -> Path:
    body = "".join(ACTIVITY.format(start=s, end=e, code=c) for s, e, c in activities)
    text = REPORT.format(name=name, npdid=npdid, start=day[0], end=day[1], md=md, activities=body)
    path = raw / DDR_DIR / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="latin-1")
    return path


SODIR_HEADER = (
    "wlbWellboreName,wlbWell,wlbField,wlbPurpose,wlbStatus,wlbEntryDate,"
    "wlbCompletionDate,wlbTotalDepth,wlbNpdidWellbore\n"
)


def write_sodir(raw: Path) -> None:
    rows = {
        "development": (
            "15/9-F-11,15/9-F-11,VOLVE,OBSERVATION,P&A,07.03.2013,12.05.2013,4562.0,7078\n"
            "15/9-X-1,15/9-X-1,VOLVE,PRODUCTION,P&A,02.01.2010,,,90001\n"
        ),
        "exploration": "",
    }
    for table, text in rows.items():
        path = raw / WELLBORE_TABLES[table]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SODIR_HEADER + text, encoding="utf-8")


def test_to_utc_keeps_the_offset() -> None:
    moment = datetime(2010, 1, 1, 6, 0, tzinfo=timezone(timedelta(hours=2)))

    assert to_utc(moment) == (datetime(2010, 1, 1, 4, 0), "+02:00")
    assert to_utc(None) == (None, None)


def test_to_utc_rejects_a_timestamp_without_offset() -> None:
    with pytest.raises(ValueError, match="without a UTC offset"):
        to_utc(datetime(2010, 1, 1))


def test_status_value_nulls_the_placeholder_and_checks_units(tmp_path: Path) -> None:
    report = parse_drill_report(write_report(tmp_path, "a.xml", "NO 15/9-F-11 T2", "7078", []))

    assert status_value(report, "md", "m") == 1500.0
    assert status_value(report, "mdPlanned", "m") is None
    assert status_value(report, "tvd", "m") is None
    with pytest.raises(ValueError, match="expected 'm'"):
        status_value(report, "diaHole", "m")


def test_stage_drill_reports(tmp_path: Path) -> None:
    raw, staging = tmp_path / "raw", tmp_path / "staging"
    write_sodir(raw)
    write_report(raw, "15_9_F_11_T2_2010_01_02.xml", "NO 15/9-F-11 T2", "7078", FULL_DAY)
    write_report(raw, "15_9_X_1_2010_01_02.xml", "NO 15/9-X-1", "90001", WITH_GAP, md="-999.99")
    write_report(raw, "15_9_X_1_2010_01_03.xml", "NO 15/9-X-1", "90001", [])

    staged = stage_drill_reports(raw, staging, load_drill_reports(raw))

    assert (staged.reports, staged.activities, staged.wellbore_keys) == (3, 4, 2)
    con = duckdb.connect()
    ddr = staging / "ddr"
    report = con.execute(
        f"SELECT wellbore_key, start_utc, start_offset, md_m, md_planned_m, dia_hole_in, "
        f"dia_hole_start_utc, activities, nulled_elements FROM '{ddr / 'report.parquet'}' "
        f"ORDER BY report_file"
    ).fetchall()
    assert report[0] == (
        "7078:T2",
        datetime(2009, 12, 31, 23, 0),
        "+01:00",
        1500.0,
        None,
        8.5,
        datetime(2009, 12, 20, 11, 0),
        2,
        "mdPlanned",
    )
    assert report[1][-1] == "md, mdPlanned"  # the report written with md = -999.99
    activity = con.execute(
        f"SELECT activity_number, wellbore_key, start_utc, end_offset, duration_hours, md_m, "
        f"category, subcategory, state_detail FROM '{ddr / 'activity.parquet'}' "
        f"ORDER BY report_file, activity_number"
    ).fetchall()
    assert activity[1] == (
        2,
        "7078:T2",
        datetime(2010, 1, 1, 5, 0),
        "+01:00",
        18.0,
        1200.0,
        "interruption",
        "repair",
        "success",
    )


def test_stage_drill_reports_rejects_an_unknown_wellbore(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    write_sodir(raw)
    write_report(raw, "x.xml", "NO 15/9-X-99", "99999", FULL_DAY)

    with pytest.raises(ValueError, match="no D1 key"):
        stage_drill_reports(raw, tmp_path / "staging", load_drill_reports(raw))
