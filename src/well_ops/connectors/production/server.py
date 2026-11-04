"""The production MCP server: registers the read-only tools of `tools.Production`."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from pydantic import Field

from well_ops.connectors.base import READ_ONLY, ConnectorServer
from well_ops.connectors.production.tools import Production

INSTRUCTIONS = """\
Read-only access to Volve production in the warehouse: the operator's production workbook
(allocated volumes per wellbore, Sm3) and its monthly reconciliation with Sodir. Every row carries
an evidence id; cite it for every number you state. Months are calendar months, written yyyy-mm."""

Wellbore = Annotated[
    str,
    Field(max_length=64, description="Wellbore key (for example 7078) or name (15/9-F-11)."),
]
Start = Annotated[dt.date, Field(description="Any date in the first month, inclusive.")]
End = Annotated[dt.date, Field(description="Any date in the last month, inclusive.")]


def build_server(tools: Production) -> ConnectorServer:
    server = ConnectorServer("well-ops-production", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ_ONLY)
    def monthly_production(
        start: Start,
        end: End,
        wellbore_key: Wellbore | None = None,
        field: Annotated[str | None, Field(max_length=40)] = None,
    ) -> dict[str, Any]:
        """Monthly production in Sm3 for one wellbore (workbook monthly sheet: on-stream hours,
        oil, gas, water, and injected gas and water) or for the field (give `field` instead of
        `wellbore_key`; the workbook covers VOLVE only, and the field total is the sum of
        wellbores). Volumes are allocated to wellbores by the operator. A technical sidetrack
        reports under its own key only if the workbook lists it."""
        return tools.monthly_production(start, end, wellbore_key, field)

    @server.tool(annotations=READ_ONLY)
    def reconciliation(start: Start, end: End) -> dict[str, Any]:
        """Field production per month on three bases, in Sm3: the workbook sum of wellbores,
        Sodir gross (sum of wellbores) and Sodir net (saleable: fuel and flare deducted), with
        their ratios and the basis labels. Volumes are rounded to 0.01 Sm3 and ratios to 4
        decimals. Differences between bases are expected; quote the basis with every number."""
        return tools.reconciliation(start, end)

    @server.tool(annotations=READ_ONLY)
    def data_quality_flags(wellbore_key: Wellbore) -> dict[str, Any]:
        """Data-quality findings for one wellbore's production: daily flags (for example a
        negative volume) and months where the daily volumes do not add up to the monthly sheet,
        or the month is missing from it. `units_check_months` is the number of months
        checked."""
        return tools.data_quality_flags(wellbore_key)

    return server
