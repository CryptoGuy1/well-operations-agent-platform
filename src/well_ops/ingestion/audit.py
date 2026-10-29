"""Phase 1 data audit: facts computed from data/raw/, one function per audit question.

Each `audit_*` function reads raw files and returns plain data. `render_*` functions turn that
data into Markdown for docs/data/data-audit-report.md. Nothing here writes to data/raw/.
"""

from __future__ import annotations

import csv
import itertools
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from well_ops.ingestion.identifiers import NameMatch, collect_well_names, match_well_names
from well_ops.ingestion.sodir_factpages import SodirWellbore, load_sodir_wellbores
from well_ops.ingestion.volve_ddr import SENTINEL, DrillReport, load_drill_reports, split_code
from well_ops.ingestion.volve_production import PRODUCTION_XLSX, sheet_rows
from well_ops.ingestion.volve_witsml import (
    WITSML_DIR,
    WITSML_ZIP,
    decode_witsml_name,
    parse_meta_file_info,
)

SODIR_PRODUCTION = Path("sodir/field_production_monthly.csv")
SODIR_PRODUCTION_GROSS = Path("sodir/field_production_gross_monthly.csv")
CIRA_DIR = Path("cira")


# --------------------------------------------------------------------------------------------
# Volve daily drilling reports (questions 1-4)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WellboreCoverage:
    wellbore: str
    npdid: str | None
    reports: int
    first: date
    last: date
    before_spud: list[str]


def audit_ddr_coverage(reports: list[DrillReport]) -> list[WellboreCoverage]:
    """Question 1: reports per wellbore and the date range of report start times."""
    grouped: dict[str, list[DrillReport]] = defaultdict(list)
    for report in reports:
        grouped[report.wellbore].append(report)
    rows = []
    for wellbore, items in grouped.items():
        npdids = {r.npdid for r in items}
        rows.append(
            WellboreCoverage(
                wellbore=wellbore,
                npdid=npdids.pop() if len(npdids) == 1 else ",".join(sorted(map(str, npdids))),
                reports=len(items),
                first=min(r.start for r in items).date(),
                last=max(r.start for r in items).date(),
                before_spud=sorted(r.file for r in items if r.spud and r.end <= r.spud),
            )
        )
    return sorted(rows, key=lambda r: r.wellbore)


@dataclass
class ActivityFacts:
    activities: int = 0
    reports_without_activities: int = 0
    field_presence: Counter[str] = field(default_factory=Counter)
    negative_durations: int = 0
    zero_durations: int = 0
    timestamps_without_offset: int = 0
    reports_where_durations_fill_report: int = 0
    reports_with_overlap_or_gap: int = 0
    examples: list[tuple[str, dict[str, str]]] = field(default_factory=list)


def audit_ddr_activities(reports: list[DrillReport], n_examples: int = 3) -> ActivityFacts:
    """Question 2: activity fields, whether durations can be computed, and examples.

    Examples are the first activity of the first reports (by file name) whose first activity
    has a code not already shown.
    """
    facts = ActivityFacts()
    shown_codes: set[str] = set()
    for report in reports:
        if not report.activities:
            facts.reports_without_activities += 1
            continue
        facts.activities += len(report.activities)
        for activity in report.activities:
            facts.field_presence.update(activity.fields.keys())
            facts.timestamps_without_offset += sum(
                t.tzinfo is None for t in (activity.start, activity.end)
            )
            if activity.duration < timedelta(0):
                facts.negative_durations += 1
            elif activity.duration == timedelta(0):
                facts.zero_durations += 1
        ordered = sorted(report.activities, key=lambda a: a.start)
        total = sum((a.duration for a in ordered), timedelta(0))
        if total == report.end - report.start:
            facts.reports_where_durations_fill_report += 1
        if any(b.start != a.end for a, b in itertools.pairwise(ordered)):
            facts.reports_with_overlap_or_gap += 1
        first = report.activities[0]
        code = first.fields.get("proprietaryCode", "")
        if len(facts.examples) < n_examples and code not in shown_codes:
            shown_codes.add(code)
            facts.examples.append((report.file, first.fields))
    return facts


def audit_ddr_codes(reports: list[DrillReport]) -> list[tuple[str, str, int]]:
    """Question 3: every (category, subcategory) in activity proprietaryCode, with counts."""
    counts = Counter(
        split_code(a.fields.get("proprietaryCode", "")) for r in reports for a in r.activities
    )
    return sorted(((c, s, n) for (c, s), n in counts.items()), key=lambda t: (t[0], -t[2], t[1]))


@dataclass(frozen=True)
class StatusField:
    element: str
    present: int
    sentinel: int
    uoms: tuple[str, ...]
    datums: tuple[str, ...]


def audit_ddr_status(reports: list[DrillReport], elements: Iterable[str]) -> list[StatusField]:
    """Question 4: presence, units and -999.99 placeholders of statusInfo depth/hole elements."""
    rows = []
    for element in elements:
        values = [r.status[element] for r in reports if element in r.status]
        rows.append(
            StatusField(
                element=element,
                present=len(values),
                sentinel=sum(text == SENTINEL for text, _, _ in values),
                uoms=tuple(sorted({uom for _, uom, _ in values if uom})),
                datums=tuple(sorted({datum for _, _, datum in values if datum})),
            )
        )
    return rows


DEPTH_AND_HOLE_ELEMENTS = (
    "md",
    "tvd",
    "mdPlanned",
    "distDrill",
    "diaHole",
    "dTimDiaHoleStart",
    "mdDiaHoleStart",
    "diaPilot",
    "mdCsgLast",
    "tvdCsgLast",
    "mdKickoff",
    "mdPlugTop",
    "elevKelly",
    "waterDepth",
)


# --------------------------------------------------------------------------------------------
# Volve WITSML real-time data (question 5)
# --------------------------------------------------------------------------------------------


@dataclass
class WitsmlInventory:
    zip_files: int = 0
    zip_bytes: int = 0
    extracted_files: int = 0
    extracted_bytes: int = 0
    # (well folder, wellbore name, object type) -> [files, uncompressed bytes]
    cells: dict[tuple[str, str, str], list[int]] = field(default_factory=dict)
    extracted_missing_from_zip: list[str] = field(default_factory=list)
    zip_only_object_types: Counter[str] = field(default_factory=Counter)


def audit_witsml(raw_dir: Path) -> WitsmlInventory:
    """Question 5: wellbores and object types in the WITSML zip, with file counts and sizes.

    The zip is read from its central directory only; nothing is extracted. The extracted
    folders next to it are compared path by path with the zip.
    """
    inventory = WitsmlInventory()
    with zipfile.ZipFile(raw_dir / WITSML_ZIP) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        wellbore_names: dict[tuple[str, str], str] = {}
        for info in infos:
            parts = info.filename.split("/")
            if len(parts) == 3 and parts[2] == "MetaFileInfo.txt":
                text = archive.read(info).decode("utf-8", errors="replace")
                for index, name in parse_meta_file_info(text).items():
                    wellbore_names[(parts[1], index)] = decode_witsml_name(name)
        zip_paths = set()
        for info in infos:
            parts = info.filename.split("/")
            inventory.zip_files += 1
            inventory.zip_bytes += info.file_size
            zip_paths.add("/".join(parts[1:]))
            if len(parts) >= 5:
                well, index, object_type = parts[1], parts[2], parts[3]
                wellbore = wellbore_names.get((well, index), f"{well}/{index} (unnamed)")
                cell = inventory.cells.setdefault((well, wellbore, object_type), [0, 0])
                cell[0] += 1
                cell[1] += info.file_size
    extracted_root = raw_dir / WITSML_DIR
    extracted_paths = set()
    for path in extracted_root.rglob("*"):
        if path.is_file() and path.suffix != ".zip":
            inventory.extracted_files += 1
            inventory.extracted_bytes += path.stat().st_size
            extracted_paths.add(path.relative_to(extracted_root).as_posix())
    inventory.extracted_missing_from_zip = sorted(extracted_paths - zip_paths)
    for zip_path in zip_paths - extracted_paths:
        parts = zip_path.split("/")
        inventory.zip_only_object_types[parts[2] if len(parts) >= 4 else "(top level)"] += 1
    return inventory


# --------------------------------------------------------------------------------------------
# Volve production workbook (question 6)
# --------------------------------------------------------------------------------------------


@dataclass
class SheetFacts:
    name: str
    columns: list[str]
    units_row: list[str] | None
    data_rows: int
    wells: Counter[str]
    first: str
    last: str
    coded_values: dict[str, Counter[str]] = field(default_factory=dict)
    null_text: dict[str, int] = field(default_factory=dict)


def audit_production(raw_dir: Path) -> list[SheetFacts]:
    """Question 6: per sheet, columns, units (if the sheet states them), wells and date range."""
    facts = []
    for name, rows in sheet_rows(raw_dir / PRODUCTION_XLSX).items():
        header = [str(c) for c in rows[0]]
        body = rows[1:]
        units_row = None
        coded: dict[str, Counter[str]] = {}
        if body and body[0][0] is None:  # a row of units under the header, first cell empty
            units_row = ["" if c is None else str(c) for c in body[0]]
            body = body[1:]
        if "DATEPRD" in header:
            dates = [r[header.index("DATEPRD")] for r in body]
            first, last = min(dates).date().isoformat(), max(dates).date().isoformat()
            well_col = header.index("WELL_BORE_CODE")
            coded = {
                c: Counter(str(r[header.index(c)]) for r in body)
                for c in ("AVG_CHOKE_UOM", "FLOW_KIND", "WELL_TYPE")
                if c in header
            }
        else:
            periods = [(int(r[header.index("Year")]), int(r[header.index("Month")])) for r in body]
            first, last = (f"{y}-{m:02d}" for y, m in (min(periods), max(periods)))
            well_col = header.index("Wellbore name")
        facts.append(
            SheetFacts(
                name=name,
                columns=header,
                units_row=units_row,
                data_rows=len(body),
                wells=Counter(str(r[well_col]) for r in body),
                first=first,
                last=last,
                coded_values=coded,
                null_text={
                    c: n
                    for i, c in enumerate(header)
                    if (n := sum(r[i] == "NULL" for r in body)) > 0
                },
            )
        )
    return facts


# --------------------------------------------------------------------------------------------
# Identifiers (question 7)
# --------------------------------------------------------------------------------------------


def audit_identifiers(
    raw_dir: Path, reports: list[DrillReport]
) -> tuple[list[NameMatch], list[SodirWellbore]]:
    """Question 7: all well names in Volve sources and Volve-field wellbores in Sodir."""
    sodir = load_sodir_wellbores(raw_dir)
    volve = sorted((w for w in sodir if w.field.upper() == "VOLVE"), key=lambda w: w.name)
    return match_well_names(collect_well_names(raw_dir, reports), sodir), volve


# --------------------------------------------------------------------------------------------
# Sodir monthly production for VOLVE (questions 8 and 9)
# --------------------------------------------------------------------------------------------

UNIT_SUFFIXES = {
    "MillSm3": "million Sm3",
    "BillSm3": "billion Sm3",
    "MillTons": "million tonnes",
}


def unit_from_column(column: str) -> str:
    for suffix, unit in UNIT_SUFFIXES.items():
        if column.endswith(suffix):
            return unit
    return ""


Period = tuple[int, int]


def _period(period: Period) -> str:
    return f"{period[0]}-{period[1]:02d}"


@dataclass
class SodirProductionFacts:
    table: str
    columns: list[str]
    rows: int
    first: str
    last: str
    monthly: dict[Period, dict[str, float]]
    decimals: dict[str, int] = field(default_factory=dict)


def audit_sodir_production(
    raw_dir: Path, path: Path = SODIR_PRODUCTION, field_name: str = "VOLVE"
) -> SodirProductionFacts:
    """Question 8: monthly rows for one field in a Sodir field production table.

    `decimals` is the largest number of decimal places used in each volume column, which sets
    the resolution of the published figures.
    """
    with (raw_dir / path).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or [])
        rows = [r for r in reader if r["prfInformationCarrier"] == field_name]
    volume_columns = [c for c in columns if c.startswith("prfPrd")]
    monthly = {
        (int(r["prfYear"]), int(r["prfMonth"])): {
            c: float(r[c]) for c in volume_columns if r[c] != ""
        }
        for r in rows
    }
    decimals = {
        c: max((len(r[c].partition(".")[2]) for r in rows if r[c]), default=0)
        for c in volume_columns
    }
    periods = sorted(monthly)
    return SodirProductionFacts(
        table=path.stem,
        columns=columns,
        rows=len(rows),
        first=_period(periods[0]),
        last=_period(periods[-1]),
        monthly=monthly,
        decimals=decimals,
    )


def workbook_monthly_sums(raw_dir: Path) -> tuple[set[Period], dict[str, dict[Period, float]]]:
    """Months listed in the workbook's monthly sheet, and Oil, Gas and Water summed over wells.

    Cells that are not numbers (the text 'NULL') contribute nothing.
    """
    rows = sheet_rows(raw_dir / PRODUCTION_XLSX)["Monthly Production Data"]
    header = [str(c) for c in rows[0]]
    listed: set[Period] = set()
    sums: dict[str, dict[Period, float]] = {"Oil": {}, "Gas": {}, "Water": {}}
    for row in rows[2:]:
        period = (int(row[header.index("Year")]), int(row[header.index("Month")]))
        listed.add(period)
        for quantity, values in sums.items():
            value = row[header.index(quantity)]
            if isinstance(value, int | float):
                values[period] = values.get(period, 0.0) + float(value)
    return listed, sums


# Sodir column and scale to Sm3 per quantity. Produced water has the same column in both tables.
SODIR_COLUMNS = {
    ("Oil", "net"): ("prfPrdOilNetMillSm3", 1e6),
    ("Gas", "net"): ("prfPrdGasNetBillSm3", 1e9),
    ("Water", "net"): ("prfPrdProducedWaterInFieldMillSm3", 1e6),
    ("Oil", "gross"): ("prfPrdOilGrossMillSm3", 1e6),
    ("Gas", "gross"): ("prfPrdGasGrossBillSm3", 1e9),
    ("Water", "gross"): ("prfPrdProducedWaterInFieldMillSm3", 1e6),
}


def sodir_series(facts: SodirProductionFacts, quantity: str, basis: str) -> dict[Period, float]:
    column, scale = SODIR_COLUMNS[(quantity, basis)]
    return {p: v[column] * scale for p, v in facts.monthly.items() if column in v}


@dataclass(frozen=True)
class Coverage:
    source: str
    quantity: str
    first: str
    last: str
    months_listed: int
    months_nonzero: int
    total_sm3: float


def coverage(
    source: str, quantity: str, listed: Iterable[Period], values: dict[Period, float]
) -> Coverage:
    periods = sorted(listed)
    return Coverage(
        source=source,
        quantity=quantity,
        first=_period(periods[0]),
        last=_period(periods[-1]),
        months_listed=len(periods),
        months_nonzero=sum(v > 0 for v in values.values()),
        total_sm3=sum(values.values()),
    )


@dataclass(frozen=True)
class RatioSummary:
    quantity: str
    ratio: str
    months_compared: int
    months_within_1pct: int
    median: float | None
    minimum: float | None
    maximum: float | None


def ratio_summary(
    quantity: str, ratio: str, numerator: dict[Period, float], denominator: dict[Period, float]
) -> RatioSummary:
    """numerator / denominator over months where both are non-zero."""
    ratios = [
        numerator[p] / denominator[p]
        for p in numerator
        if numerator[p] > 0 and denominator.get(p, 0.0) > 0
    ]
    return RatioSummary(
        quantity=quantity,
        ratio=ratio,
        months_compared=len(ratios),
        months_within_1pct=sum(abs(r - 1) <= 0.01 for r in ratios),
        median=statistics.median(ratios) if ratios else None,
        minimum=min(ratios) if ratios else None,
        maximum=max(ratios) if ratios else None,
    )


@dataclass
class ProductionComparison:
    coverage: list[Coverage]
    ratios: list[RatioSummary]
    # quantity -> rows of (month, workbook, gross, net); None where a source has no row
    monthly: dict[str, list[tuple[str, float | None, float | None, float | None]]]
    decimals: dict[str, int]


def compare_production(
    raw_dir: Path, net: SodirProductionFacts, gross: SodirProductionFacts
) -> ProductionComparison:
    """Question 9: workbook sum of wells versus Sodir gross (sum wellbores) and net (saleable)."""
    listed, workbook = workbook_monthly_sums(raw_dir)
    result = ProductionComparison(
        coverage=[], ratios=[], monthly={}, decimals={**net.decimals, **gross.decimals}
    )
    for quantity in ("Oil", "Gas", "Water"):
        wb = workbook[quantity]
        g = sodir_series(gross, quantity, "gross")
        n = sodir_series(net, quantity, "net")
        result.coverage += [
            coverage("Workbook (sum of wells)", quantity, listed, wb),
            coverage("Sodir gross (sum wellbores)", quantity, gross.monthly, g),
            coverage("Sodir net (saleable)", quantity, net.monthly, n),
        ]
        result.ratios += [
            ratio_summary(quantity, "workbook / gross", wb, g),
            ratio_summary(quantity, "workbook / net", wb, n),
            ratio_summary(quantity, "gross / net", g, n),
        ]
        if quantity != "Water":
            months = sorted(set(listed) | set(gross.monthly) | set(net.monthly))
            result.monthly[quantity] = [
                (
                    _period(p),
                    wb.get(p, 0.0) if p in listed else None,
                    g.get(p),
                    n.get(p),
                )
                for p in months
            ]
    return result


# --------------------------------------------------------------------------------------------
# CIRA pumps (question 10)
# --------------------------------------------------------------------------------------------

CIRA_README_COLUMNS = (
    "Timestamp",
    "X_ACR_Mot.PV",
    "X_ACR_Mot.SV",
    "X_ACR_Mot.TV",
    "X_ACR_Pmp.PV",
    "X_ACR_Pmp.SV",
    "X_ACR_Pmp.TV",
    "X_Temp.SV",
    "X_Pres.SV",
    "Barometer",
    "Temperature",
)


@dataclass
class CiraFileFacts:
    file: str
    delimiter: str
    decimal_comma: bool
    columns: list[str]
    rows: int
    empty_rows: int
    incomplete_rows: int
    blanks_by_column: dict[str, int]
    first: datetime
    last: datetime
    intervals: Counter[int]
    missing_readme_columns: list[str]
    extra_columns: list[str]


def _cira_rows(path: Path) -> tuple[str, list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        header_line = fh.readline()
        delimiter = ";" if header_line.count(";") > header_line.count(",") else ","
        fh.seek(0)
        return delimiter, list(csv.reader(fh, delimiter=delimiter))


def audit_cira_file(path: Path) -> CiraFileFacts:
    delimiter, rows = _cira_rows(path)
    header, body = rows[0], rows[1:]
    data = [r for r in body if any(cell.strip() for cell in r)]
    stamps = [datetime.fromisoformat(r[0].replace("Z", "+00:00")) for r in data]
    intervals = Counter(int((b - a).total_seconds()) for a, b in itertools.pairwise(stamps))
    pump = path.name.split("_", 1)[0]
    expected = [c.replace("X_", f"{pump}_") for c in CIRA_README_COLUMNS]
    return CiraFileFacts(
        file=path.name,
        delimiter=delimiter,
        decimal_comma=delimiter == ";" and any("," in c for r in data[:10] for c in r[1:]),
        columns=header,
        rows=len(data),
        empty_rows=len(body) - len(data),
        incomplete_rows=sum(any(not cell.strip() for cell in r) for r in data),
        blanks_by_column={
            c: n
            for i, c in enumerate(header)
            if (n := sum(i >= len(r) or not r[i].strip() for r in data)) > 0
        },
        first=min(stamps),
        last=max(stamps),
        intervals=intervals,
        missing_readme_columns=[c for c in expected if c not in header],
        extra_columns=[c for c in header if c not in expected],
    )


def audit_cira(raw_dir: Path) -> list[CiraFileFacts]:
    """Question 10: rows, time span, sampling interval and columns per CIRA file."""
    return [audit_cira_file(p) for p in sorted((raw_dir / CIRA_DIR).glob("*.csv"))]


# --------------------------------------------------------------------------------------------
# Markdown rendering
# --------------------------------------------------------------------------------------------


def _table(header: list[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _source(*functions: str) -> str:
    return "Computed by " + ", ".join(f"`well_ops.ingestion.audit.{f}`" for f in functions) + "."


def _mb(n: int) -> str:
    return f"{n / 1e6:,.1f}"


def file_date_matches(reports: list[DrillReport]) -> Counter[str]:
    """Which report timestamp the YYYY_MM_DD in each file name equals: end, start or neither."""
    counts: Counter[str] = Counter()
    for report in reports:
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})\.xml$", report.file)
        stamp = "-".join(match.groups()) if match else ""
        if stamp == report.end.date().isoformat():
            counts["end"] += 1
        elif stamp == report.start.date().isoformat():
            counts["start"] += 1
        else:
            counts["neither"] += 1
    return counts


def render_ddr_coverage(rows: list[WellboreCoverage], file_dates: Counter[str]) -> str:
    total = sum(r.reports for r in rows)
    return "\n\n".join(
        [
            f"{total:,} reports covering {len(rows)} wellbores. The date in the file name equals "
            f"the date of the report's `dTimEnd` in {file_dates['end']:,} files, of `dTimStart` "
            f"in {file_dates['start']:,}, and neither in {file_dates['neither']:,}. Dates below "
            "are the report `dTimStart` dates.",
            _table(
                [
                    "Wellbore (nameWellbore)",
                    "NPD number",
                    "Reports",
                    "First report",
                    "Last report",
                    "Reports ending on or before spud",
                ],
                [
                    (
                        r.wellbore,
                        r.npdid or "",
                        r.reports,
                        r.first,
                        r.last,
                        ", ".join(f"`{f}`" for f in r.before_spud) or "0",
                    )
                    for r in rows
                ],
            ),
            _source("load_drill_reports", "audit_ddr_coverage", "file_date_matches"),
        ]
    )


def render_ddr_activities(facts: ActivityFacts) -> str:
    presence = sorted(facts.field_presence.items(), key=lambda kv: (-kv[1], kv[0]))
    fields = _table(["Element", "Activities with it"], presence)
    examples = []
    for file, fields_ in facts.examples:
        body = "\n".join(f"{k}: {v}" for k, v in fields_.items())
        examples.append(f"From `{file}`:\n\n```\n{body}\n```")
    summary = (
        f"{facts.activities:,} activities; {facts.reports_without_activities} reports have none. "
        f"Every activity has `dTimStart` and `dTimEnd`, so a duration can be computed for each: "
        f"{facts.negative_durations} are negative and {facts.zero_durations} are zero; "
        f"{facts.timestamps_without_offset} activity timestamps lack a UTC offset. "
        f"In {facts.reports_where_durations_fill_report:,} reports the activity durations add "
        f"up exactly to the report period (`dTimEnd` - `dTimStart` of the report); "
        f"{facts.reports_with_overlap_or_gap:,} reports have at least one gap or overlap "
        f"between consecutive activities."
    )
    return "\n\n".join([summary, fields, "Examples:", *examples, _source("audit_ddr_activities")])


def render_ddr_codes(rows: list[tuple[str, str, int]]) -> str:
    categories = Counter[str]()
    for category, _, n in rows:
        categories[category] += n
    return "\n\n".join(
        [
            f"{len(rows)} distinct codes in {len(categories)} categories. The code is the "
            "`proprietaryCode` element, written as `category -- subcategory`.",
            _table(["Category", "Activities"], categories.most_common()),
            _table(["Category", "Subcategory", "Activities"], rows),
            _source("audit_ddr_codes"),
        ]
    )


def render_ddr_status(rows: list[StatusField], reports: int) -> str:
    return "\n\n".join(
        [
            f"Elements of `statusInfo` related to depth and hole size, over {reports:,} reports. "
            f"'-999.99' is the value used where nothing was recorded.",
            _table(
                ["Element", "Reports with it", "Value -999.99", "Unit (uom)", "datum attribute"],
                [
                    (
                        r.element,
                        r.present,
                        r.sentinel,
                        ", ".join(r.uoms),
                        ", ".join(r.datums) or "none",
                    )
                    for r in rows
                ],
            ),
            _source("audit_ddr_status"),
        ]
    )


def render_witsml(inv: WitsmlInventory) -> str:
    object_types = sorted({k[2] for k in inv.cells})
    by_wellbore: dict[tuple[str, str], dict[str, list[int]]] = defaultdict(dict)
    for (well, wellbore, object_type), cell in inv.cells.items():
        by_wellbore[(well, wellbore)][object_type] = cell
    rows = []
    for (well, wellbore), cells in sorted(by_wellbore.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        rows.append(
            [wellbore, decode_witsml_name(well)]
            + [f"{cells[t][0]:,} / {_mb(cells[t][1])}" if t in cells else "" for t in object_types]
        )
    totals: dict[str, list[int]] = {t: [0, 0] for t in object_types}
    for (_, _, object_type), cell in inv.cells.items():
        totals[object_type][0] += cell[0]
        totals[object_type][1] += cell[1]
    zip_only = ", ".join(f"{k}: {v:,}" for k, v in inv.zip_only_object_types.most_common())
    return "\n\n".join(
        [
            f"The zip `{WITSML_ZIP.name}` lists {inv.zip_files:,} files, "
            f"{_mb(inv.zip_bytes)} MB uncompressed. The extracted folders next to it hold "
            f"{inv.extracted_files:,} files, {_mb(inv.extracted_bytes)} MB. "
            f"{len(inv.extracted_missing_from_zip)} extracted files are absent from the zip. "
            f"Files only in the zip, by object type: {zip_only}.",
            "Totals by object type (zip):",
            _table(
                ["Object type", "Files", "MB"],
                [(t, f"{totals[t][0]:,}", _mb(totals[t][1])) for t in object_types],
            ),
            f"Per wellbore ({len(rows)} wellbore folders; cells are files / MB, uncompressed). "
            "Wellbore names come from each well folder's `MetaFileInfo.txt`.",
            _table(["Wellbore", "Well folder", *object_types], rows),
            _source("audit_witsml"),
        ]
    )


def render_production(sheets: list[SheetFacts]) -> str:
    parts = []
    for sheet in sheets:
        if sheet.units_row:
            units = [
                (c, u or "(none)") for c, u in zip(sheet.columns, sheet.units_row, strict=False)
            ]
            units_text = "Units, from the row under the header:\n\n" + _table(
                ["Column", "Unit"], units
            )
        else:
            units_text = (
                "This sheet has no units row and no unit in its column names; units are "
                "**unknown** from the workbook itself."
            )
        coded = "".join(
            f"\n- `{c}` values: " + ", ".join(f"{v!r} ({n:,})" for v, n in counts.most_common())
            for c, counts in sheet.coded_values.items()
        )
        parts.append(
            "\n\n".join(
                [
                    f"**Sheet '{sheet.name}'**: {sheet.data_rows:,} data rows, "
                    f"{sheet.first} to {sheet.last}.",
                    "Columns: " + ", ".join(f"`{c}`" for c in sheet.columns) + coded,
                    _table(["Well", "Rows"], sorted(sheet.wells.items())),
                    "Cells holding the text 'NULL': "
                    + (
                        ", ".join(f"`{c}` {n:,}" for c, n in sheet.null_text.items())
                        if sheet.null_text
                        else "none"
                    )
                    + ".",
                    units_text,
                ]
            )
        )
    return "\n\n".join([*parts, _source("audit_production")])


def render_identifiers(matches: list[NameMatch], volve: list[SodirWellbore]) -> str:
    grouped: dict[str, list[NameMatch]] = defaultdict(list)
    for m in matches:
        if m.canonical:
            grouped[m.canonical].append(m)
    volve_names = {w.name for w in volve}
    canonical_rows = []
    for name in sorted(volve_names | set(grouped)):
        raws = "; ".join(
            sorted(
                {
                    f"{m.source}: {m.raw}" + (f" ({m.method})" if m.method != "name" else "")
                    for m in grouped.get(name, [])
                }
            )
        )
        canonical_rows.append(
            (name, "yes" if name in volve_names else "no", raws or "(Sodir only)")
        )
    unmatched: dict[str, set[str]] = defaultdict(set)
    for m in matches:
        if m.canonical is None:
            unmatched[m.raw].add(m.source)
    conflicts = [m for m in matches if m.conflict]
    n_raw = len({(m.source, m.raw) for m in matches})
    return "\n\n".join(
        [
            f"{n_raw} distinct (source, name) pairs in Volve sources; "
            f"{len(volve)} Sodir wellbores have `wlbField` VOLVE. "
            "Proposed canonical name: the Sodir `wlbWellboreName`. Matching uses the Sodir "
            "NPDID when the source carries one (drilling reports: `wellboreAlias` 'NPD number'; "
            "production: `NPD_WELL_BORE_CODE` / `NPDCode`), otherwise the normalised name "
            "(`normalise_well_name`: decode `$NN$`, drop a leading 'NO ' and a trailing "
            "' - Main Wellbore', single spaces, split a glued suffix such as 'F-15A'). "
            "Raw names matched by NPDID are marked (NPDID).",
            f"NPDID and name disagree for {len(conflicts)} names"
            + (
                ": "
                + "; ".join(
                    f"{m.source} {m.raw!r} -> {m.canonical}, {m.conflict}" for m in conflicts
                )
                if conflicts
                else "."
            ),
            _table(
                ["Canonical (Sodir)", "Volve field in Sodir", "Names in Volve sources"],
                canonical_rows,
            ),
            f"**Cannot be matched** to any Sodir wellbore ({len(unmatched)} names):",
            _table(
                ["Raw name", "Sources"],
                [(raw, ", ".join(sorted(src))) for raw, src in sorted(unmatched.items())],
            ),
            _source("audit_identifiers", "match_well_names", "normalise_well_name"),
        ]
    )


def render_sodir_production(tables: list[SodirProductionFacts]) -> str:
    parts = []
    for facts in tables:
        production_columns = [c for c in facts.columns if c.startswith("prfPrd")]
        parts += [
            f"**Table `{facts.table}`**, rows with `prfInformationCarrier` = VOLVE: "
            f"{facts.rows} months, {facts.first} to {facts.last}.",
            "Columns: " + ", ".join(f"`{c}`" for c in facts.columns),
            _table(
                ["Column", "Unit (from the column name)", "Decimal places"],
                [
                    (c, unit_from_column(c) or "unknown", facts.decimals.get(c, ""))
                    for c in production_columns
                ],
            ),
        ]
    return "\n\n".join([*parts, _source("audit_sodir_production")])


def _ratio(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def _sm3(value: float | None) -> str:
    return "no row" if value is None else f"{value:,.0f}"


def _month_ratio(a: float | None, b: float | None) -> str:
    return f"{a / b:.4f}" if a and b else ""


def render_comparison(cmp: ProductionComparison) -> str:
    scales = {"MillSm3": 1e6, "BillSm3": 1e9}
    resolution = ", ".join(
        f"`{c}` {d} decimals = {scale * 10**-d:,.0f} Sm3"
        for c, d in sorted(cmp.decimals.items())
        for suffix, scale in scales.items()
        if c.endswith(suffix) and ("Oil" in c or "Gas" in c)
    )
    monthly_tables = []
    for quantity, rows in cmp.monthly.items():
        table = _table(
            [
                "Month",
                "Workbook Sm3",
                "Sodir gross Sm3",
                "Sodir net Sm3",
                "Workbook / gross",
                "Workbook / net",
                "Gross / net",
            ],
            [
                (
                    month,
                    _sm3(wb),
                    _sm3(g),
                    _sm3(n),
                    _month_ratio(wb, g),
                    _month_ratio(wb, n),
                    _month_ratio(g, n),
                )
                for month, wb, g, n in rows
            ],
        )
        monthly_tables.append(
            f"<details>\n<summary>{quantity}: ratios per month</summary>\n\n{table}\n\n</details>"
        )
    return "\n\n".join(
        [
            "Three sources, VOLVE, converted to Sm3: the workbook's monthly sheet summed over "
            "wellbores; Sodir `field_production_gross_monthly` (sum wellbores, gross); Sodir "
            "`field_production_monthly` (saleable, net). Produced water has the same column in "
            "both Sodir tables.",
            "Months with data per source ('listed' = the source has a row for the month):",
            _table(
                [
                    "Source",
                    "Quantity",
                    "First",
                    "Last",
                    "Months listed",
                    "Months non-zero",
                    "Total Sm3",
                ],
                [
                    (
                        c.source,
                        c.quantity,
                        c.first,
                        c.last,
                        c.months_listed,
                        c.months_nonzero,
                        f"{c.total_sm3:,.0f}",
                    )
                    for c in cmp.coverage
                ],
            ),
            "Ratios, over months where both sides are non-zero:",
            _table(
                ["Quantity", "Ratio", "Months compared", "Within 1 %", "Median", "Min", "Max"],
                [
                    (
                        r.quantity,
                        r.ratio,
                        r.months_compared,
                        r.months_within_1pct,
                        _ratio(r.median),
                        _ratio(r.minimum),
                        _ratio(r.maximum),
                    )
                    for r in cmp.ratios
                ],
            ),
            f"Resolution of the Sodir figures (largest number of decimals used, as Sm3): "
            f"{resolution}.",
            *monthly_tables,
            _source("workbook_monthly_sums", "sodir_series", "compare_production"),
        ]
    )


def render_cira(files: list[CiraFileFacts]) -> str:
    rows = []
    for f in files:
        span = f.last - f.first
        intervals = ", ".join(f"{s} s x {n:,}" for s, n in f.intervals.most_common(4))
        if len(f.intervals) > 4:
            intervals += f", +{len(f.intervals) - 4} other values"
        rows.append(
            (
                f.file,
                f"`{f.delimiter}`" + (" (decimal comma)" if f.decimal_comma else ""),
                f"{f.rows:,}",
                f.empty_rows,
                f"{f.incomplete_rows:,}",
                f.first.strftime("%Y-%m-%d %H:%M:%S"),
                f.last.strftime("%H:%M:%S"),
                str(span),
                intervals,
            )
        )
    column_rows = [
        (
            f.file,
            ", ".join(f.missing_readme_columns) or "none",
            ", ".join(f.extra_columns) or "none",
        )
        for f in files
    ]
    return "\n\n".join(
        [
            _table(
                [
                    "File",
                    "Delimiter",
                    "Rows",
                    "Empty rows",
                    "Rows with a blank value",
                    "First (UTC)",
                    "Last",
                    "Span",
                    "Sampling intervals (most common)",
                ],
                rows,
            ),
            "Blank values by column:",
            _table(
                ["File", "Blank values by column"],
                [
                    (
                        f.file,
                        ", ".join(f"{c} {n:,}" for c, n in f.blanks_by_column.items()) or "none",
                    )
                    for f in files
                ],
            ),
            "Columns compared with the dataset README (with `X` replaced by the pump letter):",
            _table(
                ["File", "README columns not in file", "File columns not in README"], column_rows
            ),
            "Header of each file: "
            + "; ".join(f"`{f.file}`: {', '.join(f.columns)}" for f in files[:1])
            + (" (other files use their own pump letter)." if len(files) > 1 else ""),
            _source("audit_cira", "audit_cira_file"),
        ]
    )


# --------------------------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------------------------


def build_sections(raw_dir: Path) -> dict[str, str]:
    reports = load_drill_reports(raw_dir)
    sheets = audit_production(raw_dir)
    matches, volve = audit_identifiers(raw_dir, reports)
    net = audit_sodir_production(raw_dir, SODIR_PRODUCTION)
    gross = audit_sodir_production(raw_dir, SODIR_PRODUCTION_GROSS)
    return {
        "ddr-coverage": render_ddr_coverage(
            audit_ddr_coverage(reports), file_date_matches(reports)
        ),
        "ddr-activities": render_ddr_activities(audit_ddr_activities(reports)),
        "ddr-codes": render_ddr_codes(audit_ddr_codes(reports)),
        "ddr-status": render_ddr_status(
            audit_ddr_status(reports, DEPTH_AND_HOLE_ELEMENTS), len(reports)
        ),
        "witsml": render_witsml(audit_witsml(raw_dir)),
        "production": render_production(sheets),
        "identifiers": render_identifiers(matches, volve),
        "sodir-production": render_sodir_production([net, gross]),
        "production-comparison": render_comparison(compare_production(raw_dir, net, gross)),
        "cira": render_cira(audit_cira(raw_dir)),
    }


_MARKER = re.compile(r"(<!-- audit:([a-z-]+) -->\n)(?:.*?\n)?(<!-- /audit:\2 -->)", re.S)


def fill_report(template: str, sections: dict[str, str]) -> str:
    """Replace the text between `<!-- audit:NAME -->` and `<!-- /audit:NAME -->` markers."""
    found = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        if name not in sections:
            raise KeyError(f"no audit section named {name!r}")
        found.add(name)
        return f"{match.group(1)}{sections[name]}\n{match.group(3)}"

    filled = _MARKER.sub(replace, template)
    missing = set(sections) - found
    if missing:
        raise KeyError(f"report has no markers for {sorted(missing)}")
    return filled
