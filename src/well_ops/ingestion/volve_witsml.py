"""Volve WITSML real-time drilling data: the zip archive and its encoded folder names."""

from __future__ import annotations

import re
from pathlib import Path

WITSML_DIR = Path("volve/WITSML Realtime drilling data")
WITSML_ZIP = WITSML_DIR / "Volve - Real Time drilling data 13.05.2018.zip"


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
