"""Wellbore identifiers: source well names, matching to Sodir, D1 keys and D2 statuses.

Every well name found in a Volve source becomes one row of
data/staging/identifiers/wellbore_alias.parquet, with the D1 key of the wellbore it names
(`<npdid>` or `<npdid>:T2`) or the D2 reason it names none. See
docs/adr/0002-phase-2-data-decisions.md.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from well_ops.ingestion.sodir_factpages import SodirWellbore, load_sodir_wellbores
from well_ops.ingestion.staging import Column, write_parquet
from well_ops.ingestion.volve_production import PRODUCTION_XLSX, sheet_rows
from well_ops.ingestion.volve_witsml import WITSML_ZIP, decode_witsml_name, parse_meta_file_info
from well_ops.keys import wellbore_key

PICKS_DAT = Path("volve/Geophysical_Interpretations/Wells/Well_picks_Volve_v1.dat")
PERFORATIONS_DAT = Path("volve/Geophysical_Interpretations/Wells/Well_perforations_Volve.dat")
EDM_XML = Path("volve/Well_technical_data/EDM.XML/Volve F.edm.xml")


class ReportName(Protocol):
    """What the identifiers need from a daily drilling report (volve_ddr.DrillReport)."""

    @property
    def wellbore(self) -> str: ...

    @property
    def npdid(self) -> str | None: ...


# --------------------------------------------------------------------------------------------
# Source names and the Phase 1 match (used by the audit, question 7)
# --------------------------------------------------------------------------------------------


def normalise_well_name(raw: str) -> str:
    """Mechanical normalisation only: decode '$NN$', drop a leading 'NO ' and a trailing
    ' - Main Wellbore', single spaces, and separate a letter suffix glued to the well number
    ('F-15A' -> 'F-15 A')."""
    name = decode_witsml_name(raw)
    name = re.sub(r"^NO\s+", "", name)
    name = re.sub(r"\s+-\s+Main Wellbore$", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return re.sub(r"(?<=\d)([A-Z]{1,3}\d?)$", r" \1", name)


@dataclass(frozen=True)
class NameObservation:
    source: str
    raw: str
    npdid: str | None = None


def well_names_ddr(reports: Iterable[ReportName]) -> set[NameObservation]:
    return {NameObservation("DDR", r.wellbore, r.npdid) for r in reports}


def well_names_witsml(raw_dir: Path) -> set[NameObservation]:
    observed = set()
    with zipfile.ZipFile(raw_dir / WITSML_ZIP) as archive:
        for info in archive.infolist():
            parts = info.filename.split("/")
            if parts[-1] == "MetaFileInfo.txt" and len(parts) in (2, 3):
                text = archive.read(info).decode("utf-8", errors="replace")
                for name in parse_meta_file_info(text).values():
                    observed.add(NameObservation("WITSML", decode_witsml_name(name)))
    return observed


def well_names_production(raw_dir: Path) -> set[NameObservation]:
    observed = set()
    rows = sheet_rows(raw_dir / PRODUCTION_XLSX)
    for _name, rows_of_sheet in rows.items():
        header = [str(c) for c in rows_of_sheet[0]]
        if "WELL_BORE_CODE" in header:
            for row in rows_of_sheet[1:]:
                npdid = str(row[header.index("NPD_WELL_BORE_CODE")])
                observed.add(NameObservation("Production daily", str(row[1]), npdid))
                observed.add(
                    NameObservation(
                        "Production daily", str(row[header.index("NPD_WELL_BORE_NAME")]), npdid
                    )
                )
        elif "Wellbore name" in header:
            for row in rows_of_sheet[2:]:
                observed.add(
                    NameObservation(
                        "Production monthly", str(row[0]), str(row[header.index("NPDCode")])
                    )
                )
    return observed


def well_names_picks(raw_dir: Path) -> set[NameObservation]:
    text = (raw_dir / PICKS_DAT).read_text(encoding="latin-1")
    return {
        NameObservation("Well picks", m.group(1).strip())
        for m in re.finditer(r"^Well (.+)$", text, flags=re.M)
    }


def well_names_perforations(raw_dir: Path) -> set[NameObservation]:
    lines = (raw_dir / PERFORATIONS_DAT).read_text(encoding="latin-1").splitlines()
    header = next(line for line in lines if line.startswith("Row"))
    start = header.index("Well name")
    end = header.index("Top formation")
    return {
        NameObservation("Well perforations", line[start:end].strip())
        for line in lines
        if line[:1].isdigit()
    }


def well_names_edm(raw_dir: Path) -> set[NameObservation]:
    """Only the name attributes are read; EDM user and audit attributes are ignored."""
    observed = set()
    for _, element in ET.iterparse(raw_dir / EDM_XML, events=("end",)):
        if element.tag in ("CD_WELL", "CD_WELLBORE"):
            for attribute in ("well_legal_name", "wellbore_name"):
                value = element.get(attribute)
                if value:
                    observed.add(NameObservation(f"EDM {attribute}", value.strip()))
        element.clear()
    return observed


def collect_well_names(raw_dir: Path, reports: Iterable[ReportName]) -> set[NameObservation]:
    """Every (source, name, NPDID) observed in the Volve sources."""
    observations: set[NameObservation] = set()
    observations |= well_names_ddr(reports)
    observations |= well_names_witsml(raw_dir)
    observations |= well_names_production(raw_dir)
    observations |= well_names_picks(raw_dir)
    observations |= well_names_perforations(raw_dir)
    observations |= well_names_edm(raw_dir)
    return observations


@dataclass(frozen=True)
class NameMatch:
    source: str
    raw: str
    canonical: str | None
    method: str  # "NPDID", "name", or "unmatched"
    conflict: str | None = None


def match_well_names(
    observations: Iterable[NameObservation], sodir: list[SodirWellbore]
) -> list[NameMatch]:
    """Canonical name = Sodir wlbWellboreName. Match on NPDID when the source carries one,
    otherwise on the normalised name. A name match that disagrees with an NPDID is reported."""
    by_npdid = {w.npdid: w.name for w in sodir}
    by_name = {w.name: w.name for w in sodir}
    matches = []
    for obs in observations:
        normalised = normalise_well_name(obs.raw)
        name_hit = by_name.get(normalised)
        npdid_hit = by_npdid.get(obs.npdid) if obs.npdid else None
        if npdid_hit:
            conflict = None
            if name_hit and name_hit != npdid_hit:
                conflict = f"name matches {name_hit}"
            matches.append(NameMatch(obs.source, obs.raw, npdid_hit, "NPDID", conflict))
        elif name_hit:
            matches.append(NameMatch(obs.source, obs.raw, name_hit, "name"))
        else:
            matches.append(NameMatch(obs.source, obs.raw, None, "unmatched"))
    return sorted(matches, key=lambda m: (m.canonical or "~", m.source, m.raw))


# --------------------------------------------------------------------------------------------
# Wellbore aliases (ADR 0002 D1, D2)
# --------------------------------------------------------------------------------------------

# D2: EDM relief wells, casing-shoe targets and reservoir-intersection targets.
PLANNING_OBJECT = re.compile(r"relief well|csg\.?\s*shoe|intersect|target", re.IGNORECASE)
# A name shaped like a well or wellbore designation: '15/9-F-11 T2', 'X-1 A', '19 BT2', or a
# pilot hole of one ('15/9-X-1 pilot'). Such names are unresolved, not discarded. Pilot holes are
# unresolved by design: Sodir does not register them as separate wellbores, so no D1 key exists.
WELLBORE_LIKE = re.compile(
    r"(\d+/\d+-)?([A-Z]-)?\d+( ?[A-Z]{1,3}\d?)?( ?T\d+)?( pilot)?", re.IGNORECASE
)
SIDETRACK = re.compile(r"(?P<parent>.+?) ?(?P<suffix>T\d+)")


def sidetrack_suffix(name: str, parent: str) -> str | None:
    """The technical sidetrack suffix of `name` under the Sodir wellbore `parent`, if any:
    '15/9-F-11 T2' under '15/9-F-11' -> 'T2', '15/9-19 BT2' under '15/9-19 B' -> 'T2'."""
    match = re.fullmatch(re.escape(parent) + r" ?(T\d+)", name)
    return match.group(1) if match else None


def sidetrack_name(parent: str, suffix: str) -> str:
    """Display name of a technical sidetrack, in the form the sources use: a space after a
    digit ('15/9-F-11 T2'), none after a letter ('15/9-19 BT2')."""
    return f"{parent}{'' if parent[-1].isalpha() else ' '}{suffix}"


def alias_status(normalised: str, matched: bool) -> str:
    """D2 status. Matched names are wellbores; the rules below apply to the rest, in order."""
    if matched:
        return "wellbore"
    if PLANNING_OBJECT.search(normalised):
        return "planning_object"
    if not WELLBORE_LIKE.fullmatch(normalised):
        return "not_a_wellbore"
    return "unresolved"


@dataclass(frozen=True)
class Alias:
    source: str
    source_name: str
    normalised_name: str
    source_npdid: int | None
    match_method: str  # 'npdid', 'name' or 'none'
    wellbore_key: str | None
    wellbore_name: str | None
    status: str  # 'wellbore', 'planning_object', 'not_a_wellbore' or 'unresolved'


def _resolve(
    observation: NameObservation,
    by_npdid: dict[str, SodirWellbore],
    by_name: dict[str, SodirWellbore],
) -> Alias:
    """Match on the NPDID when the source carries one, otherwise on the normalised name, then
    on the normalised name without a technical sidetrack suffix (D1)."""
    normalised = normalise_well_name(observation.raw)
    npdid = observation.npdid if observation.npdid and observation.npdid.isdigit() else None
    method, wellbore, suffix = "none", None, None
    if npdid and npdid in by_npdid:
        method, wellbore = "npdid", by_npdid[npdid]
        suffix = sidetrack_suffix(normalised, wellbore.name)
    elif normalised in by_name:
        method, wellbore = "name", by_name[normalised]
    else:
        sidetrack = SIDETRACK.fullmatch(normalised)
        if sidetrack and sidetrack["parent"] in by_name:
            method, wellbore = "name", by_name[sidetrack["parent"]]
            suffix = sidetrack["suffix"]
    key = name = None
    if wellbore is not None:
        key = wellbore_key(wellbore.npdid, suffix)
        name = sidetrack_name(wellbore.name, suffix) if suffix else wellbore.name
    return Alias(
        source=observation.source,
        source_name=observation.raw,
        normalised_name=normalised,
        source_npdid=int(npdid) if npdid else None,
        match_method=method,
        wellbore_key=key,
        wellbore_name=name,
        status=alias_status(normalised, wellbore is not None),
    )


def build_aliases(
    observations: Iterable[NameObservation], sodir: list[SodirWellbore]
) -> list[Alias]:
    by_npdid = {w.npdid: w for w in sodir}
    by_name = {w.name: w for w in sodir}
    aliases = [_resolve(o, by_npdid, by_name) for o in observations]
    return sorted(aliases, key=lambda a: (a.source, a.source_name, a.source_npdid or 0))


ALIAS_COLUMNS: tuple[Column, ...] = (
    ("source", "VARCHAR"),
    ("source_name", "VARCHAR"),
    ("normalised_name", "VARCHAR"),
    ("source_npdid", "BIGINT"),
    ("match_method", "VARCHAR"),
    ("wellbore_key", "VARCHAR"),
    ("wellbore_name", "VARCHAR"),
    ("status", "VARCHAR"),
)


def stage_aliases(raw_dir: Path, staging_dir: Path, reports: Iterable[ReportName]) -> list[Alias]:
    """Write data/staging/identifiers/wellbore_alias.parquet and return the aliases."""
    observations = collect_well_names(raw_dir, reports)
    aliases = build_aliases(observations, load_sodir_wellbores(raw_dir))
    rows = [
        (
            a.source,
            a.source_name,
            a.normalised_name,
            a.source_npdid,
            a.match_method,
            a.wellbore_key,
            a.wellbore_name,
            a.status,
        )
        for a in aliases
    ]
    write_parquet(staging_dir / "identifiers" / "wellbore_alias.parquet", ALIAS_COLUMNS, rows)
    return aliases
