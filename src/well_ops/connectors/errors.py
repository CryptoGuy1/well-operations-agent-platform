"""Structured tool errors: {error, detail, hint}. Details never echo the caller's input."""

from __future__ import annotations


class ToolError(Exception):
    def __init__(self, error: str, detail: str, hint: str = "") -> None:
        super().__init__(error)
        self.error = error  # a stable code, such as wellbore_not_available
        self.detail = detail
        self.hint = hint

    def as_dict(self) -> dict[str, str]:
        return {"error": self.error, "detail": self.detail, "hint": self.hint}
