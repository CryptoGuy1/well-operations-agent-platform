"""Sodir FactPages tools, read from the warehouse copy of the FactPages tables (never the internet).

Sodir lists wellbores by NPDID only, so a technical sidetrack (`<npdid>:T<n>`, ADR 0002 D1) is
answered with its parent wellbore's facts and says so. Field production is a field-level result,
allowed in development mode (ADR 0004).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from well_ops.connectors import evidence
from well_ops.connectors.base import ConnectorTools, field_name, invalid_arguments, iso, month_start
from well_ops.connectors.errors import ToolError

Basis = Literal["gross", "net"]

WELLBORE = "staging.stg_sodir__wellbore"
FIELD_PRODUCTION = {
    "gross": "staging.stg_sodir__field_production_gross_monthly",
    "net": "staging.stg_sodir__field_production_net_monthly",
}
# Volume columns by basis, in the units Sodir publishes.
VOLUMES = {
    "gross": (
        "oil_gross_mill_sm3",
        "gas_gross_bill_sm3",
        "condensate_gross_mill_sm3",
        "oe_gross_mill_sm3",
        "produced_water_in_field_mill_sm3",
    ),
    "net": (
        "oil_net_mill_sm3",
        "gas_net_bill_sm3",
        "ngl_net_mill_sm3",
        "condensate_net_mill_sm3",
        "oe_net_mill_sm3",
        "produced_water_in_field_mill_sm3",
    ),
}
BASIS_LABELS = {
    "gross": "Sodir sum of wellbores (gross)",
    "net": "Sodir saleable (net): fuel and flare deducted",
}


def not_in_sodir() -> ToolError:
    return ToolError(
        "wellbore_not_in_sodir",
        "Sodir lists no wellbore for this key.",
        "Check the key with the drilling-report connector's list_wellbores.",
    )


def field_not_found() -> ToolError:
    return ToolError(
        "field_not_found",
        "Sodir lists no production for this field.",
        "Use the field name as Sodir writes it, for example VOLVE.",
    )


class Sodir(ConnectorTools):
    def wellbore_facts(self, wellbore_key: str) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        parent = key.split(":", 1)[0]
        self.guard.check(parent)  # a sidetrack is answered with its parent's facts
        found = cur.execute(
            f"""
            select wellbore_key, npdid, wellbore_name, well_name, field_name, purpose, status,
                   entry_date, completion_date, total_depth_m
            from {WELLBORE}
            where wellbore_key in (?, ?)
            order by wellbore_key = ? desc
            limit 1
            """,
            [key, parent, key],
        ).fetchall()
        if not found:
            raise not_in_sodir()
        (sodir_key, npdid, name, well, field, purpose, status, entry, completion, depth) = found[0]
        row = {
            "evidence_id": evidence.build("sodir:wellbore", npdid=npdid),
            "wellbore_key": key,
            "sodir_wellbore_key": sodir_key,
            "note": (
                None
                if sodir_key == key
                else "Sodir does not list technical sidetracks; these are the parent's facts."
            ),
            "wellbore_name": name,
            "well_name": well,
            "field_name": field,
            "purpose": purpose,
            "status": status,
            "entry_date": iso(entry),
            "completion_date": iso(completion),
            "total_depth_m": depth,
        }
        return self._envelope([WELLBORE], {"wellbore_key": key}, [row])

    def field_production(
        self, field: str, start: dt.date, end: dt.date, basis: Basis = "net"
    ) -> dict[str, Any]:
        if end < start:
            raise invalid_arguments(["end"])
        name = field_name(field)
        first, last = month_start(start), month_start(end)
        cur = self._cursor()
        table = FIELD_PRODUCTION[basis]
        volumes = VOLUMES[basis]
        if not cur.execute(
            f"select 1 from {table} where upper(field_name) = ? limit 1", [name]
        ).fetchall():
            raise field_not_found()
        rows = cur.execute(
            f"""
            select field_npdid, month_start, {", ".join(volumes)}
            from {table}
            where upper(field_name) = ? and month_start between ? and ?
            order by month_start
            """,
            [name, first, last],
        ).fetchall()
        return self._envelope(
            [table],
            {
                "field": name,
                "start": evidence.month(first),
                "end": evidence.month(last),
                "basis": basis,
            },
            [
                {
                    "evidence_id": evidence.build(
                        f"sodir:field-{basis}", field_npdid=r[0], month=evidence.month(r[1])
                    ),
                    "month": evidence.month(r[1]),
                    **dict(zip(volumes, r[2:], strict=True)),
                }
                for r in rows
            ],
            extra={"basis_label": BASIS_LABELS[basis]},
        )
