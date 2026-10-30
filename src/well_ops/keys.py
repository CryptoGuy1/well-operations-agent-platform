"""Wellbore keys (ADR 0002 D1), shared by every source that names a wellbore."""

from __future__ import annotations


def wellbore_key(npdid: str, suffix: str | None = None) -> str:
    """D1 key: the Sodir NPDID, plus ':T2' (or ':T3', ...) for a technical sidetrack."""
    return f"{npdid}:{suffix}" if suffix else npdid
