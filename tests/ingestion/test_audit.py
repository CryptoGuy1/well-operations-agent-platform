import zipfile
from datetime import timedelta
from pathlib import Path

import openpyxl
import pytest

from well_ops.ingestion import audit
from well_ops.ingestion.audit import (
    NameObservation,
    SodirWellbore,
    audit_cira_file,
    audit_ddr_activities,
    audit_ddr_codes,
    audit_ddr_coverage,
    audit_ddr_status,
    audit_production,
    audit_sodir_production,
    audit_witsml,
    compare_production,
    decode_witsml_name,
    fill_report,
    match_well_names,
    normalise_well_name,
    parse_drill_report,
    parse_meta_file_info,
    split_code,
    unit_from_column,
)

DDR = """<?xml version="1.0" encoding="ISO-8859-1"?>
<witsml:drillReports xmlns:witsml="http://www.witsml.org/schemas/1series"><witsml:drillReport>
<witsml:nameWellbore>NO 15/9-F-1</witsml:nameWellbore>
<witsml:dTimStart>2010-01-01T00:00:00+01:00</witsml:dTimStart>
<witsml:dTimEnd>2010-01-02T00:00:00+01:00</witsml:dTimEnd>
<witsml:wellboreAlias><witsml:name>7223</witsml:name>
<witsml:namingSystem>NPD number</witsml:namingSystem></witsml:wellboreAlias>
<witsml:wellboreInfo><witsml:dTimSpud>2009-12-01T00:00:00+01:00</witsml:dTimSpud></witsml:wellboreInfo>
<witsml:statusInfo><witsml:md uom="m">-999.99</witsml:md>
<witsml:diaHole uom="in">8.5</witsml:diaHole></witsml:statusInfo>
{activities}
</witsml:drillReport></witsml:drillReports>"""

ACTIVITY = (
    "<witsml:activity><witsml:dTimStart>{start}</witsml:dTimStart>"
    "<witsml:dTimEnd>{end}</witsml:dTimEnd><witsml:md uom='m'>100</witsml:md>"
    "<witsml:proprietaryCode>{code}</witsml:proprietaryCode></witsml:activity>"
)


def _ddr(tmp_path: Path, name: str, activities: list[tuple[str, str, str]]) -> Path:
    body = "".join(ACTIVITY.format(start=s, end=e, code=c) for s, e, c in activities)
    path = tmp_path / name
    path.write_text(DDR.format(activities=body), encoding="latin-1")
    return path


FULL_DAY = [
    ("2010-01-01T00:00:00+01:00", "2010-01-01T06:00:00+01:00", "drilling -- drill"),
    ("2010-01-01T06:00:00+01:00", "2010-01-02T00:00:00+01:00", "interruption -- repair"),
]


def test_parse_drill_report_reads_ids_status_and_activities(tmp_path: Path) -> None:
    report = parse_drill_report(_ddr(tmp_path, "a.xml", FULL_DAY))

    assert report.wellbore == "NO 15/9-F-1"
    assert report.npdid == "7223"
    assert report.status["diaHole"] == ("8.5", "in", None)
    assert report.activities[0].duration == timedelta(hours=6)
    assert report.activities[0].fields["md@uom"] == "m"


def test_activity_facts_detect_gaps_and_full_days(tmp_path: Path) -> None:
    full = parse_drill_report(_ddr(tmp_path, "a.xml", FULL_DAY))
    gap = parse_drill_report(_ddr(tmp_path, "b.xml", [FULL_DAY[0]]))
    empty = parse_drill_report(_ddr(tmp_path, "c.xml", []))

    facts = audit_ddr_activities([full, gap, empty])

    assert facts.activities == 3
    assert facts.reports_without_activities == 1
    assert facts.reports_where_durations_fill_report == 1
    assert facts.negative_durations == 0
    assert facts.timestamps_without_offset == 0
    assert [file for file, _ in facts.examples] == ["a.xml"]


def test_coverage_codes_and_status(tmp_path: Path) -> None:
    reports = [parse_drill_report(_ddr(tmp_path, "a.xml", FULL_DAY))]

    coverage = audit_ddr_coverage(reports)
    codes = audit_ddr_codes(reports)
    status = audit_ddr_status(reports, ["md", "diaHole", "tvd"])

    assert coverage[0].reports == 1
    assert coverage[0].before_spud == []
    assert codes == [("drilling", "drill", 1), ("interruption", "repair", 1)]
    assert [(s.element, s.present, s.sentinel) for s in status] == [
        ("md", 1, 1),
        ("diaHole", 1, 0),
        ("tvd", 0, 0),
    ]


def test_split_code_without_separator() -> None:
    assert split_code("drilling -- trip") == ("drilling", "trip")
    assert split_code("unknown") == ("unknown", "")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("NO 15_$47$_9-F-11 T2", "15/9-F-11 T2"),
        ("NO  15/9-F-1 C", "15/9-F-1 C"),
        ("15/9-F-15A - Main Wellbore", "15/9-F-15 A"),
        ("15/9-F-12", "15/9-F-12"),
    ],
)
def test_normalise_well_name(raw: str, expected: str) -> None:
    assert normalise_well_name(raw) == expected


def test_decode_witsml_name_and_meta_file_info() -> None:
    assert decode_witsml_name("17 1/2_$34$_ Final (abc)(NULL)") == '17 1/2" Final'
    text = "1  NO 15_$47$_9-F-11 T2 (id-1)(NULL)\n2  NO 15_$47$_9-F-11 B (id-2)(NULL)\n"
    assert parse_meta_file_info(text) == {
        "1": "NO 15_$47$_9-F-11 T2 (id-1)(NULL)",
        "2": "NO 15_$47$_9-F-11 B (id-2)(NULL)",
    }


def test_match_well_names_prefers_npdid_and_reports_conflicts() -> None:
    sodir = [SodirWellbore("15/9-F-4", "5693", "VOLVE"), SodirWellbore("15/9-F-5", "5769", "VOLVE")]
    observations = [
        NameObservation("Production daily", "NO 15/9-F-4 AH", "5693"),
        NameObservation("Well picks", "NO 15/9-F-5"),
        NameObservation("DDR", "NO 15/9-F-5", "5693"),
        NameObservation("WITSML", "test"),
    ]

    matches = {(m.source, m.raw): m for m in match_well_names(observations, sodir)}

    assert matches[("Production daily", "NO 15/9-F-4 AH")].canonical == "15/9-F-4"
    assert matches[("Production daily", "NO 15/9-F-4 AH")].method == "NPDID"
    assert matches[("Well picks", "NO 15/9-F-5")].method == "name"
    assert matches[("DDR", "NO 15/9-F-5")].conflict == "name matches 15/9-F-5"
    assert matches[("WITSML", "test")].canonical is None


def test_audit_witsml_counts_zip_and_extracted(tmp_path: Path) -> None:
    root = tmp_path / audit.WITSML_DIR
    root.mkdir(parents=True)
    well = "Norway-NA-15_$47$_9-F-1"
    files = {
        f"{well}/MetaFileInfo.txt": "1  15_$47$_9-F-1 - Main Wellbore (B-1)(NULL)\n",
        f"{well}/1/trajectory/1.xml": "<t/>",
        f"{well}/1/log/1/1/1/00001.xml": "<log>" + "x" * 100 + "</log>",
    }
    with zipfile.ZipFile(tmp_path / audit.WITSML_ZIP, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"server/{name}", content)
    for name in list(files)[:2]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[name], encoding="utf-8")

    inventory = audit_witsml(tmp_path)

    assert inventory.zip_files == 3
    assert inventory.extracted_files == 2
    assert inventory.extracted_missing_from_zip == []
    assert inventory.zip_only_object_types == {"log": 1}
    assert inventory.cells[(well, "15/9-F-1 - Main Wellbore", "log")] == [1, 111]


def _workbook(tmp_path: Path) -> None:
    path = tmp_path / audit.PRODUCTION_XLSX
    path.parent.mkdir(parents=True)
    workbook = openpyxl.Workbook()
    monthly = workbook.active
    assert monthly is not None
    monthly.title = "Monthly Production Data"
    monthly.append(
        ["Wellbore name", "NPDCode", "Year", "Month", "On Stream", "Oil", "Gas", "Water"]
    )
    monthly.append([None, None, None, None, "hrs", "Sm3", "Sm3", "Sm3"])
    monthly.append(["15/9-F-4", 5693, 2010, 1, 700, 100.0, 1000.0, 10.0])
    monthly.append(["15/9-F-5", 5769, 2010, 1, 700, 99.0, 1000.0, 10.0])
    monthly.append(["15/9-F-5", 5769, 2009, 12, 700, 5.0, 0.0, 0.0])
    workbook.save(path)


def test_audit_production_reads_units_row_and_periods(tmp_path: Path) -> None:
    _workbook(tmp_path)

    (sheet,) = audit_production(tmp_path)

    assert sheet.units_row is not None
    assert sheet.units_row[5] == "Sm3"
    assert sheet.data_rows == 3
    assert (sheet.first, sheet.last) == ("2009-12", "2010-01")
    assert sheet.wells == {"15/9-F-4": 1, "15/9-F-5": 2}


def _sodir_tables(tmp_path: Path) -> None:
    (tmp_path / "sodir").mkdir()
    (tmp_path / audit.SODIR_PRODUCTION).write_text(
        "\ufeffprfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,"
        "prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier\n"
        "VOLVE,2010,1,0.00020,0.000001,0.00002,1\n"
        "OTHER,2010,1,9.0,9.0,9.0,2\n",
        encoding="utf-8",
    )
    (tmp_path / audit.SODIR_PRODUCTION_GROSS).write_text(
        "\ufeffprfInformationCarrier,prfYear,prfMonth,prfPrdOilGrossMillSm3,prfPrdGasGrossBillSm3,"
        "prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier\n"
        "VOLVE,2010,1,0.000199,0.000002,0.00002,1\n"
        "VOLVE,2010,2,0.00001,0.0,0.0,1\n",
        encoding="utf-8",
    )


def test_audit_sodir_production_filters_field_and_counts_decimals(tmp_path: Path) -> None:
    _sodir_tables(tmp_path)

    facts = audit_sodir_production(tmp_path, audit.SODIR_PRODUCTION_GROSS)

    assert facts.table == "field_production_gross_monthly"
    assert (facts.rows, facts.first, facts.last) == (2, "2010-01", "2010-02")
    assert facts.decimals["prfPrdOilGrossMillSm3"] == 6
    assert facts.monthly[(2010, 1)]["prfPrdGasGrossBillSm3"] == pytest.approx(0.000002)


def test_compare_production_three_way(tmp_path: Path) -> None:
    _workbook(tmp_path)
    _sodir_tables(tmp_path)
    net = audit_sodir_production(tmp_path, audit.SODIR_PRODUCTION)
    gross = audit_sodir_production(tmp_path, audit.SODIR_PRODUCTION_GROSS)

    result = compare_production(tmp_path, net, gross)

    ratios = {(r.quantity, r.ratio): r for r in result.ratios}
    assert ratios[("Oil", "workbook / gross")].median == pytest.approx(1.0)
    assert ratios[("Oil", "workbook / net")].median == pytest.approx(0.995)
    assert ratios[("Oil", "workbook / net")].months_within_1pct == 1
    assert ratios[("Gas", "workbook / net")].median == pytest.approx(2.0)
    assert ratios[("Gas", "gross / net")].median == pytest.approx(2.0)
    cov = {(c.source, c.quantity): c for c in result.coverage}
    workbook_oil = cov[("Workbook (sum of wells)", "Oil")]
    assert (workbook_oil.first, workbook_oil.last, workbook_oil.months_listed) == (
        "2009-12",
        "2010-01",
        2,
    )
    assert cov[("Sodir gross (sum wellbores)", "Oil")].last == "2010-02"
    oil_rows = result.monthly["Oil"]
    assert oil_rows[0] == ("2009-12", 5.0, None, None)
    assert oil_rows[2][0] == "2010-02"
    assert oil_rows[2][1] is None
    assert "Water" not in result.monthly


def test_audit_cira_file_handles_semicolons_and_gaps(tmp_path: Path) -> None:
    path = tmp_path / "A_2024-10-30.csv"
    path.write_text(
        "Timestamp;A_ACR_Mot.PV;A_Pres.PV\n"
        "2024-10-30T10:00:00Z;0,1;1,0\n"
        "2024-10-30T10:00:01Z;0,1;\n"
        "2024-10-30T10:00:06Z;0,2;1,1\n"
        ";;\n",
        encoding="utf-8",
    )

    facts = audit_cira_file(path)

    assert facts.delimiter == ";"
    assert facts.decimal_comma is True
    assert facts.rows == 3
    assert facts.empty_rows == 1
    assert facts.incomplete_rows == 1
    assert facts.blanks_by_column == {"A_Pres.PV": 1}
    assert facts.intervals == {1: 1, 5: 1}
    assert "A_Pres.SV" in facts.missing_readme_columns
    assert facts.extra_columns == ["A_Pres.PV"]


def test_unit_from_column() -> None:
    assert unit_from_column("prfPrdGasNetBillSm3") == "billion Sm3"
    assert unit_from_column("prfYear") == ""


def test_fill_report_replaces_only_marked_sections() -> None:
    template = "# Title\n\n<!-- audit:a -->\nold\n<!-- /audit:a -->\n\nhand text\n"

    filled = fill_report(template, {"a": "new"})

    assert filled == "# Title\n\n<!-- audit:a -->\nnew\n<!-- /audit:a -->\n\nhand text\n"
    assert fill_report(filled, {"a": "new"}) == filled


def test_fill_report_rejects_missing_or_unknown_sections() -> None:
    with pytest.raises(KeyError, match="no markers"):
        fill_report("text", {"a": "x"})
    with pytest.raises(KeyError, match="no audit section"):
        fill_report("<!-- audit:b -->\n<!-- /audit:b -->", {})
