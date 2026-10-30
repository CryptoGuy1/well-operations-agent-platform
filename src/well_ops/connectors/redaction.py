"""Redaction of personal data in text returned by tools (ADR 0004).

Email addresses, phone numbers, IP addresses and names on the private deny-list are replaced by
`[redacted]`. The deny-list is built at staging time (`well_ops.ingestion.denylist`) and is never
printed or committed. Phone numbers are matched only in an international form (+ and 8 to 15
digits) or after a label such as "tel" or "phone", because drilling text is full of numbers
(depths, sizes, times) that a looser pattern would remove.
"""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REDACTED = "[redacted]"
MATCH_TYPES = ("email", "ip", "phone", "name")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Candidates only; each is confirmed with the ipaddress module.
IPV4 = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w.])")
IPV6 = re.compile(
    r"(?<![\w:])(?=[0-9A-Fa-f:]*::|(?:[0-9A-Fa-f]{1,4}:){7})[0-9A-Fa-f:]{2,39}(?![\w:])"
)
# The number is the `number` group; a label before it is kept.
PHONE = re.compile(
    r"(?<![\w+])(?P<number>\+\d[\d ()./-]{6,20}\d)(?!\w)"
    r"|\b(?:tel|tlf|phone|mobile?|mob|cell|fax)\b\.?:?\s*"
    r"(?P<labelled>\+?\d[\d ()./-]{6,20}\d)(?!\w)",
    re.I,
)


def _ip(candidate: str) -> bool:
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return True


def _phone(candidate: str) -> bool:
    return 8 <= sum(c.isdigit() for c in candidate) <= 15


@dataclass(frozen=True)
class Redaction:
    text: str
    counts: Counter[str] = field(default_factory=Counter)


class Redactor:
    """Replaces personal data in text; `counts` says how many matches of each type were found."""

    def __init__(self, names: Iterable[str] = ()) -> None:
        unique = sorted({n.strip() for n in names if n.strip()}, key=lambda n: (-len(n), n))
        self._names = (
            re.compile(
                r"(?<![\w.@-])(?:" + "|".join(re.escape(n) for n in unique) + r")(?![\w@-])",
                re.I,
            )
            if unique
            else None
        )

    @classmethod
    def from_file(cls, path: Path) -> Redactor:
        """Load the deny-list (one name per line). A missing file is an error: fail closed."""
        if not path.is_file():
            raise FileNotFoundError("redaction deny-list not found; run `make stage` to build it")
        return cls(path.read_text(encoding="utf-8").splitlines())

    def redact(self, text: str) -> Redaction:
        counts: Counter[str] = Counter()

        def sub(kind: str, pattern: re.Pattern[str], text: str, valid: Any = None) -> str:
            def replace(match: re.Match[str]) -> str:
                whole = match.group(0)
                group = next((g for g in ("number", "labelled") if match.groupdict().get(g)), None)
                value = match.group(group) if group else whole
                if valid is not None and not valid(value):
                    return whole
                counts[kind] += 1
                if group is None:
                    return REDACTED
                start = match.start(group) - match.start(0)
                return whole[:start] + REDACTED + whole[start + len(value) :]

            return pattern.sub(replace, text)

        text = sub("email", EMAIL, text)
        text = sub("ip", IPV4, text, _ip)
        text = sub("ip", IPV6, text, _ip)
        text = sub("phone", PHONE, text, _phone)
        if self._names is not None:
            text = sub("name", self._names, text)
        return Redaction(text, counts)

    def redact_tree(self, value: Any) -> tuple[Any, Counter[str]]:
        """Redact every string in a JSON-like value (dicts, lists, tuples); keys are unchanged."""
        counts: Counter[str] = Counter()

        def walk(v: Any) -> Any:
            if isinstance(v, str):
                result = self.redact(v)
                counts.update(result.counts)
                return result.text
            if isinstance(v, dict):
                return {k: walk(x) for k, x in v.items()}
            if isinstance(v, list | tuple):
                return type(v)(walk(x) for x in v)
            return v

        return walk(value), counts
