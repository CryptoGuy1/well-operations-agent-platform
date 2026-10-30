"""Build the private redaction deny-list from the personal fields that are never staged.

Sources: EDM user and contact attributes, WITSML `priv_userOwner` and `priv_userLastChange` (in
the extracted object files and extracted logs), and the email addresses in the CIRA README. The
list is written to data/private/redaction_denylist.txt, which is never committed or printed;
only its entry count is reported.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path
from xml.sax.saxutils import unescape

from well_ops.ingestion.identifiers import EDM_XML
from well_ops.ingestion.volve_witsml import LOG_DIR, WITSML_DIR

DENYLIST_FILE = "redaction_denylist.txt"
CIRA_README = Path("cira/README.md")

EDM_PERSONAL_ATTRIBUTES = frozenset(
    {
        "case_author",
        "contact_name",
        "create_user_id",
        "email_address",
        "engineer",
        "update_user_id",
        "user_id",
    }
)
WITSML_PERSONAL = re.compile(rb"<(priv_user(?:Owner|LastChange))>([^<]*)</\1>")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

# Organisation names that some user fields hold instead of a person; they are not personal data
# and appear in ordinary report text.
ORGANISATIONS = frozenset(
    {"equinor", "halliburton", "schlumberger", "statoil", "weatherford", "baker hughes"}
)
MIN_LENGTH = 3  # shorter entries (initials) would match ordinary words and abbreviations


def edm_values(raw_dir: Path) -> Iterator[str]:
    for _, element in ET.iterparse(raw_dir / EDM_XML, events=("end",)):
        for name, value in element.attrib.items():
            if name in EDM_PERSONAL_ATTRIBUTES:
                yield value
        element.clear()


def witsml_values(raw_dir: Path) -> Iterator[str]:
    """User names in WITSML object files and extracted logs (the zip itself is not read)."""
    for root in (raw_dir / WITSML_DIR, raw_dir / LOG_DIR):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.xml")):
            for _, value in WITSML_PERSONAL.findall(path.read_bytes()):
                yield unescape(value.decode("utf-8", "replace"))


def cira_values(raw_dir: Path) -> Iterator[str]:
    path = raw_dir / CIRA_README
    if path.exists():
        yield from EMAIL.findall(path.read_text(encoding="utf-8"))


def denylist_entries(values: Iterable[str]) -> list[str]:
    """Trimmed, de-duplicated (ignoring case) entries; an email also adds its local part."""
    entries: dict[str, str] = {}
    for value in values:
        value = value.strip()
        candidates = [value, value.split("@", 1)[0]] if "@" in value else [value]
        for candidate in candidates:
            folded = candidate.casefold()
            if len(candidate) >= MIN_LENGTH and folded not in ORGANISATIONS:
                entries.setdefault(folded, candidate)
    return sorted(entries.values(), key=str.casefold)


def write_denylist(raw_dir: Path, private_dir: Path) -> int:
    """Write the deny-list, readable by the owner only; return the number of entries."""
    entries = denylist_entries(
        [*edm_values(raw_dir), *witsml_values(raw_dir), *cira_values(raw_dir)]
    )
    private_dir.mkdir(parents=True, exist_ok=True)
    path = private_dir / DENYLIST_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(f"{e}\n" for e in entries), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    return len(entries)
