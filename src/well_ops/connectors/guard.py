"""The held-out guard (ADR 0004, ADR 0002 D8).

Outside evaluation mode every per-wellbore lookup of a held-out wellbore is refused with the same
error, whatever the wellbore holds. Evaluation mode is the WELL_OPS_EVALUATION_MODE flag, set only
by the evaluation harness.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeVar

from well_ops.connectors.errors import ToolError
from well_ops.settings import Settings

T = TypeVar("T")


def not_available() -> ToolError:
    """The one refusal for a held-out wellbore, whatever it holds."""
    return ToolError(
        "wellbore_not_available",
        "This wellbore is not available to tools in this mode.",
        "Use a development wellbore.",
    )


def held_out_keys(splits: Path) -> frozenset[str]:
    """D1 keys of the held-out wellbores in evaluation/splits.json."""
    data = json.loads(splits.read_text(encoding="utf-8"))
    return frozenset(str(entry["key"]) for entry in data["held_out"])


class HeldOutGuard:
    def __init__(self, held_out: Iterable[str], evaluation_mode: bool) -> None:
        self._held_out = frozenset(held_out)
        self.evaluation_mode = evaluation_mode

    @classmethod
    def from_settings(cls, settings: Settings) -> HeldOutGuard:
        return cls(held_out_keys(settings.splits_path), settings.evaluation_mode)

    def allows(self, wellbore_key: str) -> bool:
        return self.evaluation_mode or wellbore_key not in self._held_out

    def check(self, wellbore_key: str) -> None:
        """Raise `wellbore_not_available` for a held-out key outside evaluation mode."""
        if not self.allows(wellbore_key):
            raise not_available()

    def visible(self, rows: Iterable[T], key: Callable[[T], str]) -> list[T]:
        """The rows whose wellbore the guard allows, in their original order."""
        return [row for row in rows if self.allows(key(row))]
