"""reconciliation.json: the field's monthly production in the workbook and in Sodir's gross and
net series, with the basis of each, and the production attribution override."""

from __future__ import annotations

from typing import Any

import duckdb

RECONCILIATION = "marts.fct_production_monthly_reconciliation"
ATTRIBUTED = "intermediate.int_production__monthly_attributed"
WELLBORE = "marts.dim_wellbore"
BASIS_COLUMNS = ("workbook_basis", "sodir_gross_basis", "sodir_net_basis")


def export(con: duckdb.DuckDBPyConnection, held_out: frozenset[str]) -> dict[str, Any]:
    cur = con.execute(f"select * from {RECONCILIATION} order by month_start")
    names = [d[0] for d in cur.description or ()]
    months = []
    for row in cur.fetchall():
        record = dict(zip(names, row, strict=True))
        record["month"] = record.pop("month_start").strftime("%Y-%m")
        months.append(record)
    bases = sorted({tuple(m[c] for c in BASIS_COLUMNS) for m in months}, key=str)
    if len(bases) == 1:  # one basis for every month: given once
        for m in months:
            for c in BASIS_COLUMNS:
                del m[c]
    overrides = con.execute(
        f"""
        select a.attributed_wellbore_key, w.wellbore_name, a.published_npdid,
               a.attribution_reason, count(*), min(a.month_start), max(a.month_start)
        from {ATTRIBUTED} a join {WELLBORE} w on w.wellbore_key = a.attributed_wellbore_key
        where a.attribution_source = 'override'
        group by all order by 1, 3
        """
    ).fetchall()
    if any(o[0] in held_out for o in overrides):
        raise ValueError("an attribution override names a held-out wellbore")
    return {
        "basis": dict(zip(BASIS_COLUMNS, bases[0], strict=True)) if len(bases) == 1 else None,
        "months": months,
        "attribution_overrides": [
            {
                "attributed_wellbore_key": key,
                "attributed_wellbore_name": name,
                "published_npdid": npdid,
                "reason": reason,
                "months": n,
                "first_month": first.strftime("%Y-%m"),
                "last_month": last.strftime("%Y-%m"),
            }
            for key, name, npdid, reason, n, first, last in overrides
        ],
    }
