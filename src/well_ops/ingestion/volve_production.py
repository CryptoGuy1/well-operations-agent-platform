"""Volve production workbook (daily and monthly sheets)."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import openpyxl

PRODUCTION_XLSX = Path("volve/Production_data/Volve production data.xlsx")


@cache
def sheet_rows(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return {ws.title: list(ws.iter_rows(values_only=True)) for ws in workbook.worksheets}
    finally:
        workbook.close()
