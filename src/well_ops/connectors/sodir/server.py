"""The Sodir MCP server: registers the read-only tools of `tools.Sodir`."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from pydantic import Field

from well_ops.connectors.base import READ_ONLY, ConnectorServer
from well_ops.connectors.sodir.tools import Basis, Sodir

INSTRUCTIONS = """\
Read-only access to the Norwegian Offshore Directorate (Sodir) FactPages tables copied into the
warehouse; nothing is fetched from the internet. Every row carries an evidence id; cite it for
every number you state."""


def build_server(tools: Sodir) -> ConnectorServer:
    server = ConnectorServer("well-ops-sodir", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ_ONLY)
    def wellbore_facts(
        wellbore_key: Annotated[
            str,
            Field(max_length=64, description="Wellbore key (7078:T2) or name (15/9-F-11 T2)."),
        ],
    ) -> dict[str, Any]:
        """Sodir facts for a wellbore: name, well, field, purpose, status, entry date, completion
        date and total depth (m). The completion date is the end of drilling, not production
        start-up. Sodir does not list technical sidetracks; for one, the parent wellbore's facts
        are returned and `note` says so."""
        return tools.wellbore_facts(wellbore_key)

    @server.tool(annotations=READ_ONLY)
    def field_production(
        field: Annotated[str, Field(max_length=40, description="Field name, for example VOLVE.")],
        start: Annotated[dt.date, Field(description="Any date in the first month, inclusive.")],
        end: Annotated[dt.date, Field(description="Any date in the last month, inclusive.")],
        basis: Basis = "net",
    ) -> dict[str, Any]:
        """Monthly field production from Sodir, gross (sum of wellbores) or net (saleable: fuel
        and flare deducted). Units are as Sodir publishes them: million Sm3 for oil, NGL,
        condensate, oil equivalents and produced water, and billion Sm3 for gas."""
        return tools.field_production(field, start, end, basis)

    return server
