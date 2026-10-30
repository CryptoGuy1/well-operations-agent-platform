"""Volve WITSML real-time drilling data (ADR 0002 D6).

Non-log objects (already extracted next to the zip) are staged for all wellbores to
data/staging/witsml/. Real-time logs stay in the zip and are extracted on demand, one wellbore at
a time, to data/raw/volve/witsml_logs/<key>/, then summarised to data/staging/witsml_log/.

Only the fields listed in OBJECTS and LOG_FIELDS are read. WITSML commonData also carries user
names, IP addresses and job numbers (priv_* elements); they are never staged.
"""

from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import duckdb

from well_ops.ingestion.manifest import (
    ManifestEntry,
    build_entry,
    load_manifest,
    utc_now,
)
from well_ops.ingestion.staging import Column, to_utc, write_parquet

WITSML_DIR = Path("volve/WITSML Realtime drilling data")
WITSML_ZIP = WITSML_DIR / "Volve - Real Time drilling data 13.05.2018.zip"
LOG_DIR = Path("volve/witsml_logs")
SOURCE = "Equinor Volve Data Village"
LICENCE = "Equinor Open Data Licence"


def parse_meta_file_info(text: str) -> dict[str, str]:
    """MetaFileInfo.txt lines are '<folder>  <name>  <id>' separated by two spaces."""
    mapping = {}
    for line in text.splitlines():
        parts = [p for p in line.split("  ") if p]
        if len(parts) >= 2:
            mapping[parts[0].strip()] = parts[1].strip()
    return mapping


def decode_witsml_name(name: str) -> str:
    """Folder and file names encode a character as '_$NN$_' (NN = its code, e.g. 47 = '/').
    Trailing '(id)' groups are dropped."""
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"_?\$(\d+)\$_?", lambda m: chr(int(m.group(1))), name).strip()


# --------------------------------------------------------------------------------------------
# Field specifications
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    """One staged value. `path` is relative to the row element, '/'-separated, without
    namespaces; '@attr' at the end reads an attribute.

    Kinds: 'text'; 'number' (DOUBLE); 'measure' (DOUBLE plus <column>_uom from the uom
    attribute); 'time' (<column>_utc plus <column>_offset, D5)."""

    column: str
    path: str
    kind: str = "text"

    def columns(self) -> tuple[Column, ...]:
        if self.kind == "measure":
            return ((self.column, "DOUBLE"), (f"{self.column}_uom", "VARCHAR"))
        if self.kind == "time":
            return ((f"{self.column}_utc", "TIMESTAMP"), (f"{self.column}_offset", "VARCHAR"))
        if self.kind == "number":
            return ((self.column, "DOUBLE"),)
        return ((self.column, "VARCHAR"),)


@dataclass(frozen=True)
class ObjectSpec:
    """A WITSML object folder staged to one table. With `row_tag`, each child element of that
    name is a row (for example each trajectoryStation); otherwise each object is a row."""

    folder: str
    table: str
    fields: tuple[Field, ...]
    row_tag: str | None = None
    object_fields: tuple[Field, ...] = ()

    def columns(self) -> tuple[Column, ...]:
        context: tuple[Column, ...] = (
            ("source_file", "VARCHAR"),  # relative to the WITSML folder
            ("source_wellbore_name", "VARCHAR"),  # decoded MetaFileInfo name, as in the aliases
            ("object_uid", "VARCHAR"),
            ("object_name", "VARCHAR"),
        )
        if self.row_tag:
            context += (("row_uid", "VARCHAR"),)
        return (
            *context,
            *(c for f in self.object_fields for c in f.columns()),
            *(c for f in self.fields for c in f.columns()),
        )


OBJECTS: tuple[ObjectSpec, ...] = (
    ObjectSpec(
        "trajectory",
        "trajectory_station",
        row_tag="trajectoryStation",
        fields=(
            Field("station", "dTimStn", "time"),
            Field("type_traj_station", "typeTrajStation"),
            Field("type_survey_tool", "typeSurveyTool"),
            Field("md", "md", "measure"),
            Field("tvd", "tvd", "measure"),
            Field("incl", "incl", "measure"),
            Field("azi", "azi", "measure"),
            Field("disp_ns", "dispNs", "measure"),
            Field("disp_ew", "dispEw", "measure"),
            Field("dls", "dls", "measure"),
            Field("status_traj_station", "statusTrajStation"),
        ),
    ),
    ObjectSpec(
        "bhaRun",
        "bha_run",
        fields=(
            Field("tubular_uid", "tubular/@uidRef"),
            Field("run_start", "dTimStart", "time"),
            Field("run_stop", "dTimStop", "time"),
            Field("drilling_start", "dTimStartDrilling", "time"),
            Field("drilling_stop", "dTimStopDrilling", "time"),
            Field("num_bit_run", "numBitRun"),
            Field("num_string_run", "numStringRun"),
            Field("md_hole_start", "drillingParams/mdHoleStart", "measure"),
            Field("md_hole_stop", "drillingParams/mdHoleStop", "measure"),
        ),
    ),
    ObjectSpec(
        "tubular",
        "tubular_component",
        row_tag="tubularComponent",
        object_fields=(Field("type_tubular_assy", "typeTubularAssy"),),
        fields=(
            Field("type_tubular_comp", "typeTubularComp"),
            Field("sequence", "sequence", "number"),
            Field("id", "id", "measure"),
            Field("od", "od", "measure"),
            Field("len", "len", "measure"),
            Field("dia_bit", "bitRecord/diaBit", "measure"),
            Field("vendor", "vendor"),
        ),
    ),
    ObjectSpec(
        "wbGeometry",
        "wb_geometry_section",
        row_tag="wbGeometrySection",
        object_fields=(Field("report", "dTimReport", "time"),),
        fields=(
            Field("type_hole_casing", "typeHoleCasing"),
            Field("md_top", "mdTop", "measure"),
            Field("md_bottom", "mdBottom", "measure"),
            Field("tvd_top", "tvdTop", "measure"),
            Field("tvd_bottom", "tvdBottom", "measure"),
            Field("id_section", "idSection", "measure"),
            Field("od_section", "odSection", "measure"),
            Field("grade", "grade"),
        ),
    ),
    ObjectSpec(
        "mudLog",
        "mud_log_interval",
        row_tag="geologyInterval",
        object_fields=(Field("mud_log_company", "mudLogCompany"),),
        fields=(
            Field("interval", "dTim", "time"),
            Field("type_lithology", "typeLithology"),
            Field("md_top", "mdTop", "measure"),
            Field("md_bottom", "mdBottom", "measure"),
            Field("rop_av", "ropAv", "measure"),
            Field("wob_av", "wobAv", "measure"),
            Field("tq_av", "tqAv", "measure"),
            Field("rpm_av", "rpmAv", "measure"),
            Field("wt_mud_av", "wtMudAv", "measure"),
            Field("ecd_td_av", "ecdTdAv", "measure"),
        ),
    ),
    ObjectSpec(
        "rig",
        "rig",
        fields=(
            Field("owner", "owner"),
            Field("type_rig", "typeRig"),
        ),
    ),
    ObjectSpec(
        "message",
        "message",
        fields=(
            Field("message", "dTim", "time"),
            Field("md", "md", "measure"),
            Field("type_message", "typeMessage"),
            Field("severity", "severity"),
            Field("message_text", "messageText"),
        ),
    ),
)


def _ns(element: ET.Element) -> str:
    return element.tag[: element.tag.index("}") + 1] if element.tag.startswith("{") else ""


def _find(element: ET.Element, path: str, ns: str) -> ET.Element | None:
    found: ET.Element | None = element
    for part in path.split("/"):
        found = found.find(ns + part) if found is not None else None
    return found


def field_values(element: ET.Element, spec: Field, ns: str) -> tuple[object, ...]:
    path, _, attribute = spec.path.partition("/@")
    found = _find(element, path, ns)
    if attribute:
        return ((found.get(attribute) or None) if found is not None else None,)
    text = (found.text or "").strip() if found is not None else ""
    if spec.kind == "measure":
        uom = found.get("uom") if found is not None else None
        return (float(text) if text else None, uom if text else None)
    if spec.kind == "number":
        return (float(text) if text else None,)
    if spec.kind == "time":
        return to_utc(datetime.fromisoformat(text) if text else None)
    return (text or None,)


def object_rows(
    root: ET.Element, spec: ObjectSpec, source_file: str, wellbore_name: str
) -> Iterator[tuple[object, ...]]:
    ns = _ns(root)
    for obj in root.findall(ns + spec.folder):
        context = (source_file, wellbore_name, obj.get("uid"), obj.findtext(ns + "name"))
        shared = tuple(v for f in spec.object_fields for v in field_values(obj, f, ns))
        rows = obj.findall(ns + spec.row_tag) if spec.row_tag else [obj]
        for row in rows:
            uid = (row.get("uid"),) if spec.row_tag else ()
            values = tuple(v for f in spec.fields for v in field_values(row, f, ns))
            yield (*context, *uid, *shared, *values)


# --------------------------------------------------------------------------------------------
# Non-log objects: data/staging/witsml/<table>.parquet
# --------------------------------------------------------------------------------------------


def wellbore_folders(witsml_dir: Path) -> Iterator[tuple[Path, str]]:
    """(wellbore folder, decoded wellbore name) from each well folder's MetaFileInfo.txt."""
    for meta in sorted(witsml_dir.glob("*/MetaFileInfo.txt")):
        text = meta.read_text(encoding="utf-8", errors="replace")
        for index, name in parse_meta_file_info(text).items():
            folder = meta.parent / index
            if folder.is_dir():
                yield folder, decode_witsml_name(name)


def stage_witsml_objects(raw_dir: Path, staging_dir: Path) -> dict[str, int]:
    """Write one table per object type for all wellbores; return row counts by table."""
    witsml_dir = raw_dir / WITSML_DIR
    folders = list(wellbore_folders(witsml_dir))
    counts = {}
    for spec in OBJECTS:
        rows: list[tuple[object, ...]] = []
        for folder, name in folders:
            for path in sorted((folder / spec.folder).glob("*.xml")):
                source_file = path.relative_to(witsml_dir).as_posix()
                try:
                    root = ET.parse(path).getroot()
                    rows.extend(object_rows(root, spec, source_file, name))
                except (ET.ParseError, ValueError) as exc:
                    raise ValueError(f"{source_file}: {exc}") from exc
        counts[spec.table] = write_parquet(
            staging_dir / "witsml" / f"{spec.table}.parquet", spec.columns(), rows
        )
    return counts


# --------------------------------------------------------------------------------------------
# Logs on demand (D6): extract one wellbore's logs from the zip
# --------------------------------------------------------------------------------------------


def witsml_names(staging_dir: Path, key: str) -> set[str]:
    """WITSML wellbore names that the staged alias table resolves to `key` (D1, D2)."""
    path = (staging_dir / "identifiers" / "wellbore_alias.parquet").as_posix()
    with duckdb.connect() as con:
        rows = con.execute(
            "select source_name from read_parquet(?) where source = 'WITSML' and wellbore_key = ?",
            [path, key],
        ).fetchall()
    return {r[0] for r in rows}


def heldout_keys(splits: Path) -> set[str]:
    return {w["key"] for w in json.loads(splits.read_text(encoding="utf-8"))["held_out"]}


def zip_log_members(archive: zipfile.ZipFile, names: set[str]) -> list[zipfile.ZipInfo]:
    """Log files under every zip wellbore folder whose MetaFileInfo name is in `names`."""
    folders = set()
    for info in archive.infolist():
        parts = info.filename.split("/")
        if len(parts) == 3 and parts[2] == "MetaFileInfo.txt":
            text = archive.read(info).decode("utf-8", errors="replace")
            for index, name in parse_meta_file_info(text).items():
                if decode_witsml_name(name) in names:
                    folders.add((parts[1], index))
    return [
        info
        for info in archive.infolist()
        if not info.is_dir()
        and len(parts := info.filename.split("/")) > 4
        and (parts[1], parts[2]) in folders
        and parts[3] == "log"
    ]


def extract_logs(data_dir: Path, key: str, names: set[str]) -> list[ManifestEntry]:
    """Copy one wellbore's log files from the zip to raw/volve/witsml_logs/<key>/, keeping the
    zip's folder layout below its root folder. Files already present with the right size are
    kept. Returns manifest entries for every file."""
    if not names:
        raise ValueError(f"no WITSML wellbore name resolves to {key}")
    raw_dir = data_dir / "raw"
    zip_entry = {e.file: e for e in load_manifest(data_dir / "manifest.json")}.get(
        (Path("raw") / WITSML_ZIP).as_posix()
    )
    zip_url = zip_entry.source_url if zip_entry else WITSML_ZIP.as_posix()
    target_root = raw_dir / LOG_DIR / key
    retrieved = utc_now()
    entries = []
    with zipfile.ZipFile(raw_dir / WITSML_ZIP) as archive:
        members = zip_log_members(archive, names)
        if not members:
            raise ValueError(f"no log files in the zip for {key}")
        for info in members:
            target = target_root / info.filename.split("/", 1)[1]
            if not (target.exists() and target.stat().st_size == info.file_size):
                target.parent.mkdir(parents=True, exist_ok=True)
                part = target.with_name(target.name + ".part")
                with archive.open(info) as src, part.open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                part.replace(target)
            entries.append(
                build_entry(
                    target, data_dir, SOURCE, f"{zip_url}!/{info.filename}", LICENCE, retrieved
                )
            )
    return entries


# --------------------------------------------------------------------------------------------
# Log summaries: data/staging/witsml_log/log.parquet and log_curve.parquet
# Curve values are not staged here; each log keeps its index range and row count.
# --------------------------------------------------------------------------------------------

LOG_COLUMNS: tuple[Column, ...] = (
    ("log_id", "VARCHAR"),  # <key>#<index folder>/<log folder>/<run folder>
    ("wellbore_key", "VARCHAR"),
    ("source_wellbore_name", "VARCHAR"),
    ("log_name", "VARCHAR"),
    ("index_type", "VARCHAR"),
    ("index_curve", "VARCHAR"),
    ("index_uom", "VARCHAR"),
    ("start_index", "VARCHAR"),  # depth as text, or a UTC time ending in Z
    ("end_index", "VARCHAR"),
    ("direction", "VARCHAR"),
    ("service_company", "VARCHAR"),
    ("run_number", "VARCHAR"),
    ("chunks", "INTEGER"),
    ("rows", "BIGINT"),
)

CURVE_COLUMNS: tuple[Column, ...] = (
    ("log_id", "VARCHAR"),
    ("mnemonic", "VARCHAR"),
    ("unit", "VARCHAR"),
    ("type_log_data", "VARCHAR"),
    ("curve_description", "VARCHAR"),
    ("chunks", "INTEGER"),  # chunks of the log that list this curve
)


@dataclass
class LogSummary:
    header: dict[str, str | None]
    chunks: int = 0
    rows: int = 0
    starts: list[str] = field(default_factory=list)
    ends: list[str] = field(default_factory=list)
    # (mnemonic, unit) -> (typeLogData, description, chunks listing it)
    curves: dict[tuple[str, str | None], tuple[str | None, str | None, int]] = field(
        default_factory=dict
    )


def parse_log_chunk(
    path: Path,
) -> tuple[dict[str, str | None], list[tuple[str, str | None, str | None, str | None]], int]:
    """(header fields, curves as (mnemonic, unit, type, description), data row count)."""
    root = ET.parse(path).getroot()
    ns = _ns(root)
    log = root.find(ns + "log")
    if log is None:
        raise ValueError(f"{path.name}: no log element")
    start = log.find(ns + "startIndex")
    header = {
        "source_wellbore_name": log.findtext(ns + "nameWellbore"),
        "log_name": log.findtext(ns + "name"),
        "index_type": log.findtext(ns + "indexType"),
        "index_curve": log.findtext(ns + "indexCurve"),
        "index_uom": start.get("uom") if start is not None else None,
        # Depth logs use startIndex/endIndex; time logs startDateTimeIndex/endDateTimeIndex.
        "start_index": log.findtext(ns + "startIndex") or log.findtext(ns + "startDateTimeIndex"),
        "end_index": log.findtext(ns + "endIndex") or log.findtext(ns + "endDateTimeIndex"),
        "direction": log.findtext(ns + "direction"),
        "service_company": log.findtext(ns + "serviceCompany"),
        "run_number": log.findtext(ns + "runNumber"),
    }
    curves = [
        (
            info.findtext(ns + "mnemonic") or "",
            info.findtext(ns + "unit"),
            info.findtext(ns + "typeLogData"),
            info.findtext(ns + "curveDescription"),
        )
        for info in log.findall(ns + "logCurveInfo")
    ]
    data = log.find(ns + "logData")
    rows = len(data.findall(ns + "data")) if data is not None else 0
    return header, curves, rows


def _index_key(index_type: str | None, value: str) -> float | str:
    return value if index_type == "date time" else float(value)


def summarise_logs(
    key_dir: Path, key: str
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    """Group chunk files by <index folder>/<log folder>/<run folder> below each log/ folder."""
    logs: dict[str, LogSummary] = {}
    for path in sorted(key_dir.rglob("*.xml")):
        parts = path.relative_to(key_dir).parts
        position = parts.index("log")
        log_id = f"{key}#{'/'.join(parts[position + 1 : -1])}"
        header, curves, rows = parse_log_chunk(path)
        summary = logs.setdefault(log_id, LogSummary(header))
        if summary.header["source_wellbore_name"] != header["source_wellbore_name"]:
            raise ValueError(f"{log_id}: chunks name different wellbores")
        summary.chunks += 1
        summary.rows += rows
        if header["start_index"]:
            summary.starts.append(header["start_index"])
        if header["end_index"]:
            summary.ends.append(header["end_index"])
        for mnemonic, unit, kind, description in curves:
            old = summary.curves.get((mnemonic, unit))
            summary.curves[(mnemonic, unit)] = (kind, description, (old[2] if old else 0) + 1)
    log_rows: list[tuple[object, ...]] = []
    curve_rows: list[tuple[object, ...]] = []
    for log_id, s in sorted(logs.items()):
        kind = s.header["index_type"]
        h = s.header
        log_rows.append(
            (
                log_id,
                key,
                h["source_wellbore_name"],
                h["log_name"],
                kind,
                h["index_curve"],
                h["index_uom"],
                min(s.starts, key=lambda v: _index_key(kind, v)) if s.starts else None,
                max(s.ends, key=lambda v: _index_key(kind, v)) if s.ends else None,
                h["direction"],
                h["service_company"],
                h["run_number"],
                s.chunks,
                s.rows,
            )
        )
        for (mnemonic, unit), (curve_kind, description, n) in sorted(
            s.curves.items(), key=lambda item: (item[0][0], item[0][1] or "")
        ):
            curve_rows.append((log_id, mnemonic, unit, curve_kind, description, n))
    return log_rows, curve_rows


def stage_witsml_logs(raw_dir: Path, staging_dir: Path) -> tuple[int, int]:
    """Summarise every extracted wellbore under raw/volve/witsml_logs/; return row counts."""
    log_rows: list[tuple[object, ...]] = []
    curve_rows: list[tuple[object, ...]] = []
    root = raw_dir / LOG_DIR
    for key_dir in sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []:
        logs, curves = summarise_logs(key_dir, key_dir.name)
        log_rows += logs
        curve_rows += curves
    out = staging_dir / "witsml_log"
    return (
        write_parquet(out / "log.parquet", LOG_COLUMNS, log_rows),
        write_parquet(out / "log_curve.parquet", CURVE_COLUMNS, curve_rows),
    )


# --------------------------------------------------------------------------------------------
# Log values: data/staging/witsml_log_values/<key>/<index>_<log>_<run>.parquet, one file per log
# with the index column and every curve. Units are in the curve summary (log_curve.parquet).
# A curve's declared nullValue, the log's nullValue and -999.25 (D3, amended) become null.
# --------------------------------------------------------------------------------------------

LOG_VALUES_DIR = "witsml_log_values"
WITSML_NULL = -999.25
VALUE_TYPES = {"double": "DOUBLE", "long": "BIGINT", "date time": "TIMESTAMP", "string": "VARCHAR"}


def values_file_name(log_id: str) -> str:
    """'7078:T2#1/16/1' -> '1_16_1.parquet'."""
    return log_id.split("#", 1)[1].replace("/", "_") + ".parquet"


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _null_set(*declared: str | None) -> list[float]:
    values = {WITSML_NULL}
    for text in declared:
        if text and text.strip():
            values.add(float(text))
    return sorted(values)


@dataclass(frozen=True)
class LogChunk:
    columns: list[str]
    types: dict[str, str]  # mnemonic -> DuckDB type
    nulls: dict[str, list[float]]  # mnemonic -> values read as null
    lines: list[str]


def read_log_chunk(path: Path) -> LogChunk:
    root = ET.parse(path).getroot()
    ns = _ns(root)
    log = root.find(ns + "log")
    data = log.find(ns + "logData") if log is not None else None
    if log is None or data is None:
        raise ValueError(f"{path.name}: no log data")
    columns = (data.findtext(ns + "mnemonicList") or "").split(",")
    infos = {i.findtext(ns + "mnemonic"): i for i in log.findall(ns + "logCurveInfo")}
    missing = [c for c in columns if c not in infos]
    if missing:
        raise ValueError(f"{path.name}: no logCurveInfo for {missing}")
    if len({c.lower() for c in columns}) != len(columns):
        raise ValueError(f"{path.name}: mnemonics differ only by case")
    types, nulls = {}, {}
    for column in columns:
        info = infos[column]
        kind = info.findtext(ns + "typeLogData") or ""
        if kind not in VALUE_TYPES:
            raise ValueError(f"{path.name}: {column} has typeLogData {kind!r}")
        # A curve with an axisDefinition holds an array per row (space-separated values).
        is_array = info.find(ns + "axisDefinition") is not None
        types[column] = VALUE_TYPES[kind] + ("[]" if is_array else "")
        nulls[column] = _null_set(log.findtext(ns + "nullValue"), info.findtext(ns + "nullValue"))
    lines = [d.text or "" for d in data.findall(ns + "data")]
    return LogChunk(columns, types, nulls, lines)


def _typed(column: str, sql_type: str, nulls: list[float]) -> str:
    name = _quote(column)
    listed = ", ".join(repr(v) for v in nulls)
    if sql_type == "DOUBLE[]":
        return (
            f"list_transform(string_split(trim({name}), ' '), lambda x: case when cast(x as DOUBLE)"
            f" in ({listed}) then null else cast(x as DOUBLE) end)"
        )
    if sql_type in ("DOUBLE", "BIGINT"):
        number = f"cast({name} as DOUBLE)"
        return f"cast(case when {number} in ({listed}) then null else {number} end as {sql_type})"
    if sql_type == "TIMESTAMP":
        return f"cast({name} as TIMESTAMPTZ) at time zone 'UTC'"
    return name


def _null_count(column: str, sql_type: str, nulls: list[float]) -> str | None:
    """SQL counting the values of one column that are read as null."""
    name = _quote(column)
    listed = ", ".join(repr(v) for v in nulls)
    if sql_type == "DOUBLE[]":
        return (
            f"coalesce(sum(len(list_filter(string_split(trim({name}), ' '),"
            f" lambda x: cast(x as DOUBLE) in ({listed})))), 0)"
        )
    if sql_type in ("DOUBLE", "BIGINT"):
        return f"count_if(cast({name} as DOUBLE) in ({listed}))"
    return None


def stage_log_values(key_dir: Path, key: str, out_dir: Path) -> tuple[int, int, int]:
    """Write one Parquet file per log of one wellbore; return (files, rows, values nulled)."""
    chunks: dict[str, list[Path]] = {}
    for path in sorted(key_dir.rglob("*.xml")):
        parts = path.relative_to(key_dir).parts
        position = parts.index("log")
        chunks.setdefault(f"{key}#{'/'.join(parts[position + 1 : -1])}", []).append(path)
    part_dir = out_dir.with_name(out_dir.name + ".part")
    shutil.rmtree(part_dir, ignore_errors=True)
    part_dir.mkdir(parents=True)
    rows = nulled = 0
    with duckdb.connect() as con:
        con.execute("SET TimeZone = 'UTC'")
        for log_id, paths in sorted(chunks.items()):
            pieces = []
            for n, path in enumerate(paths):
                chunk = read_log_chunk(path)
                csv_path = part_dir / "chunk.csv"
                csv_path.write_text("\n".join(chunk.lines) + "\n", encoding="utf-8")
                definition = ", ".join(f"{_quote(c)} VARCHAR" for c in chunk.columns)
                con.execute(f"CREATE OR REPLACE TABLE raw_chunk ({definition})")
                if chunk.lines:
                    target = csv_path.as_posix().replace("'", "''")
                    con.execute(f"COPY raw_chunk FROM '{target}' (HEADER false, DELIMITER ',')")
                counts = [_null_count(c, chunk.types[c], chunk.nulls[c]) for c in chunk.columns]
                if any(counts):
                    total = " + ".join(c for c in counts if c)
                    nulled += con.execute(f"select coalesce({total}, 0) from raw_chunk").fetchall()[
                        0
                    ][0]
                select = ", ".join(
                    f"{_typed(c, chunk.types[c], chunk.nulls[c])} as {_quote(c)}"
                    for c in chunk.columns
                )
                piece = (part_dir / f"piece_{n:05d}.parquet").as_posix()
                con.execute(f"COPY (select {select} from raw_chunk) TO '{piece}' (FORMAT parquet)")
                pieces.append(piece)
            target = (part_dir / values_file_name(log_id)).as_posix()
            listed = ", ".join(f"'{p}'" for p in pieces)
            con.execute(
                f"COPY (select * from read_parquet([{listed}], union_by_name = true)) "
                f"TO '{target}' (FORMAT parquet)"
            )
            rows += con.execute(f"select count(*) from '{target}'").fetchall()[0][0]
            for piece in pieces:
                Path(piece).unlink()
        (part_dir / "chunk.csv").unlink(missing_ok=True)
    shutil.rmtree(out_dir, ignore_errors=True)
    part_dir.replace(out_dir)
    return len(chunks), rows, nulled


def stage_witsml_log_values(raw_dir: Path, staging_dir: Path) -> dict[str, tuple[int, int, int]]:
    """Stage values for every extracted wellbore; return (files, rows, nulled) by key."""
    root = raw_dir / LOG_DIR
    result = {}
    for key_dir in sorted(p for p in root.glob("*") if p.is_dir()) if root.exists() else []:
        out_dir = staging_dir / LOG_VALUES_DIR / key_dir.name
        result[key_dir.name] = stage_log_values(key_dir, key_dir.name, out_dir)
    return result
