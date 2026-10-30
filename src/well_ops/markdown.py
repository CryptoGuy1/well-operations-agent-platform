"""Markdown helpers for generated reports: tables and marker-delimited sections."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence


def table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows]
    return "\n".join(lines)


def fill_report(template: str, sections: dict[str, str], prefix: str = "audit") -> str:
    """Replace the text between `<!-- PREFIX:NAME -->` and `<!-- /PREFIX:NAME -->` markers."""
    marker = re.compile(rf"(<!-- {prefix}:([a-z-]+) -->\n)(?:.*?\n)?(<!-- /{prefix}:\2 -->)", re.S)
    found = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(2)
        if name not in sections:
            raise KeyError(f"no {prefix} section named {name!r}")
        found.add(name)
        return f"{match.group(1)}{sections[name]}\n{match.group(3)}"

    filled = marker.sub(replace, template)
    missing = set(sections) - found
    if missing:
        raise KeyError(f"report has no markers for {sorted(missing)}")
    return filled
