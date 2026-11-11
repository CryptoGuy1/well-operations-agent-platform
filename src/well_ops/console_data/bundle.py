"""Writing the bundle: deterministic JSON, file sizes and the privacy scan."""

from __future__ import annotations

import datetime as dt
import json
import math
import shutil
from collections import Counter
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

from well_ops.connectors.redaction import Redactor


def jsonable(value: Any) -> Any:
    """A JSON value: dates and timestamps as ISO text, decimals as numbers, NaN as null, tuples as
    lists. Raises TypeError for anything else that JSON cannot hold."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(v) for v in value]
    if isinstance(value, bool) or value is None or isinstance(value, str | int):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    raise TypeError(f"not JSON: {type(value).__name__}")


def dumps(value: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8 text, one trailing newline."""
    return (
        json.dumps(
            jsonable(value),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


class Bundle:
    """The bundle directory. `reset` empties it, so a file no export writes cannot linger."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def write(self, name: str, value: Any) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps(value), encoding="utf-8")

    def files(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*") if p.is_file())

    def sizes(self) -> list[tuple[str, int]]:
        """(path relative to the bundle, bytes), largest first."""
        found = [(p.relative_to(self.root).as_posix(), p.stat().st_size) for p in self.files()]
        return sorted(found, key=lambda f: (-f[1], f[0]))


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def scan(bundle: Bundle, redactor: Redactor) -> Counter[str]:
    """Personal-data matches (emails, IP addresses, phone numbers, deny-listed names) in every key
    and string of the bundle, by type. Counts only: the matches are never returned."""
    total: Counter[str] = Counter()
    for path in bundle.files():
        for text in _strings(json.loads(path.read_text(encoding="utf-8"))):
            total.update(redactor.redact(text).counts)
    return total
