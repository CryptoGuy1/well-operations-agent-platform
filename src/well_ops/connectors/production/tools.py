"""Production tools: the Volve production workbook and its reconciliation with Sodir (ADR 0002 D9).

Per-wellbore results come from the workbook's monthly sheet and leave held-out wellbores out. The
field total is the reconciliation table's workbook sum, a field-level result that ADR 0004 allows
in development mode; it names no wellbore.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from well_ops.connectors import evidence
from well_ops.connectors.base import (
    ConnectorTools,
    field_name,
    invalid_arguments,
    iso,
    month_start,
)
from well_ops.connectors.errors import ToolError

MONTHLY = "staging.stg_production__monthly"
DAILY_FLAG = "intermediate.int_production__daily_flag"
UNITS_CHECK = "intermediate.int_production__daily_units_check"
RECONCILIATION = "marts.fct_production_monthly_reconciliation"
WELLBORE = "marts.dim_wellbore"

# The workbook covers one field.
WORKBOOK_FIELD = "VOLVE"
FLUIDS = ("oil", "gas", "water")


def field_not_available() -> ToolError:
    return ToolError(
        "field_not_available",
        "The production workbook covers the VOLVE field only.",
        "Use field VOLVE, or the Sodir connector for other fields.",
    )


def _months(start: dt.date, end: dt.date) -> tuple[dt.date, dt.date]:
    if end < start:
        raise invalid_arguments(["end"])
    return month_start(start), month_start(end)


def _round(value: float | None, digits: int) -> float | None:
    """Volumes to 0.01 Sm3 and ratios to 4 decimals: sums of the workbook carry float noise."""
    return None if value is None else round(value, digits)


def _npdid(key: str) -> int:
    return int(key.split(":", 1)[0])


class Production(ConnectorTools):
    def monthly_production(
        self,
        start: dt.date,
        end: dt.date,
        wellbore_key: str | None = None,
        field: str | None = None,
    ) -> dict[str, Any]:
        first, last = _months(start, end)
        if field is not None and wellbore_key is None:
            return self._field_monthly(field, first, last)
        if wellbore_key is None or field is not None:
            raise invalid_arguments(["wellbore_key", "field"])
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        rows = cur.execute(
            f"""
            select npdid, month_start, on_stream_hours, oil_sm3, gas_sm3, water_sm3,
                   gas_injected_sm3, water_injected_sm3
            from {MONTHLY}
            where wellbore_key = ? and month_start between ? and ?
            order by month_start
            """,
            [key, first, last],
        ).fetchall()
        return self._envelope(
            [MONTHLY],
            {"wellbore_key": key, "start": evidence.month(first), "end": evidence.month(last)},
            [
                {
                    "evidence_id": evidence.build(
                        "prod:monthly", npdid=npdid, month=evidence.month(m)
                    ),
                    "month": evidence.month(m),
                    "on_stream_hours": hours,
                    "oil_sm3": oil,
                    "gas_sm3": gas,
                    "water_sm3": water,
                    "gas_injected_sm3": gas_inj,
                    "water_injected_sm3": water_inj,
                }
                for npdid, m, hours, oil, gas, water, gas_inj, water_inj in rows
            ],
        )

    def _field_monthly(self, field: str, first: dt.date, last: dt.date) -> dict[str, Any]:
        name = field_name(field)
        if name != WORKBOOK_FIELD:
            raise field_not_available()
        rows = (
            self._cursor()
            .execute(
                f"""
            select month_start, oil_workbook_sm3, gas_workbook_sm3, water_workbook_sm3,
                   workbook_basis
            from {RECONCILIATION}
            where month_start between ? and ?
            order by month_start
            """,
                [first, last],
            )
            .fetchall()
        )
        return self._envelope(
            [RECONCILIATION],
            {"field": name, "start": evidence.month(first), "end": evidence.month(last)},
            [
                {
                    "evidence_id": evidence.build("prod:reconciliation", month=evidence.month(m)),
                    "month": evidence.month(m),
                    "oil_sm3": _round(oil, 2),
                    "gas_sm3": _round(gas, 2),
                    "water_sm3": _round(water, 2),
                    "basis": basis,
                }
                for m, oil, gas, water, basis in rows
            ],
        )

    def reconciliation(self, start: dt.date, end: dt.date) -> dict[str, Any]:
        first, last = _months(start, end)
        cur = self._cursor()
        columns = [
            f"{fluid}_{part}"
            for fluid in FLUIDS
            for part in (
                "workbook_sm3",
                "sodir_gross_sm3",
                "sodir_net_sm3",
                "workbook_to_gross",
                "workbook_to_net",
                "gross_to_net",
            )
        ]
        basis = cur.execute(
            f"select distinct workbook_basis, sodir_gross_basis, sodir_net_basis"
            f" from {RECONCILIATION} order by all"
        ).fetchall()
        rows = cur.execute(
            f"""
            select month_start, {", ".join(columns)}
            from {RECONCILIATION}
            where month_start between ? and ?
            order by month_start
            """,
            [first, last],
        ).fetchall()
        return self._envelope(
            [RECONCILIATION],
            {"start": evidence.month(first), "end": evidence.month(last)},
            [
                {
                    "evidence_id": evidence.build(
                        "prod:reconciliation", month=evidence.month(r[0])
                    ),
                    "month": evidence.month(r[0]),
                    **{
                        column: _round(value, 2 if column.endswith("_sm3") else 4)
                        for column, value in zip(columns, r[1:], strict=True)
                    },
                }
                for r in rows
            ],
            extra={
                "basis": [{"workbook": w, "sodir_gross": g, "sodir_net": n} for w, g, n in basis],
                "ratio_note": (
                    "Ratios divide the first volume by the second, for example "
                    "oil_workbook_to_gross = oil_workbook_sm3 / oil_sodir_gross_sm3."
                ),
            },
        )

    def data_quality_flags(self, wellbore_key: str) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        npdid = _npdid(key)
        flags = cur.execute(
            f"""
            select production_date, flag, detail from {DAILY_FLAG}
            where wellbore_key = ? order by production_date, flag
            """,
            [key],
        ).fetchall()
        checks = cur.execute(
            f"""
            select month_start, in_monthly_sheet, daily_volume_unit,
                   oil_agrees, gas_agrees, water_agrees, oil_ratio, gas_ratio, water_ratio
            from {UNITS_CHECK}
            where wellbore_key = ?
              and not (coalesce(oil_agrees, true) and coalesce(gas_agrees, true)
                       and coalesce(water_agrees, true) and in_monthly_sheet)
            order by month_start
            """,
            [key],
        ).fetchall()
        months_checked = cur.execute(
            f"select count(*) from {UNITS_CHECK} where wellbore_key = ?", [key]
        ).fetchall()[0][0]
        rows: list[dict[str, Any]] = [
            {
                "kind": "daily_flag",
                "evidence_id": evidence.build("prod:daily", npdid=npdid, day=day),
                "date": iso(day),
                "flag": flag,
                "detail": detail,
            }
            for day, flag, detail in flags
        ]
        rows += [
            {
                "kind": "units_check",
                # A month missing from the monthly sheet has no monthly row to cite.
                "evidence_id": (
                    evidence.build("prod:monthly", npdid=npdid, month=evidence.month(m))
                    if in_sheet
                    else None
                ),
                "month": evidence.month(m),
                "in_monthly_sheet": in_sheet,
                "daily_volume_unit": unit,
                "oil_agrees": oil,
                "gas_agrees": gas,
                "water_agrees": water,
                "oil_ratio": oil_r,
                "gas_ratio": gas_r,
                "water_ratio": water_r,
            }
            for m, in_sheet, unit, oil, gas, water, oil_r, gas_r, water_r in checks
        ]
        return self._envelope(
            [DAILY_FLAG, UNITS_CHECK],
            {"wellbore_key": key},
            rows,
            extra={"units_check_months": months_checked},
        )
