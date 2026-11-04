"""The real-time MCP server: registers the read-only tools of `tools.Realtime`."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from pydantic import Field

from well_ops.connectors.base import READ_ONLY, ConnectorServer
from well_ops.connectors.realtime.tools import IndexType, Realtime

INSTRUCTIONS = """\
Read-only access to WITSML real-time logs of wellbores whose logs have been extracted. Logs are
indexed by measured depth (m) or by time (UTC). Mnemonics are the vendor's own and are not mapped
between logs. Every row carries an evidence id; cite it for every number you state."""

Wellbore = Annotated[
    str,
    Field(max_length=64, description="Wellbore key (7078:T2) or name (15/9-F-11 T2)."),
]
Bound = Annotated[
    float | dt.datetime | None,
    Field(
        description="Index bound, inclusive: metres for depth logs, ISO time (UTC) for time logs."
    ),
]


def build_server(tools: Realtime) -> ConnectorServer:
    server = ConnectorServer("well-ops-realtime", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ_ONLY)
    def list_logs(wellbore_key: Wellbore, index_type: IndexType | None = None) -> dict[str, Any]:
        """Real-time logs of a wellbore: log id, name, index type, curve and unit, index range,
        run, row and curve counts, and data-quality flags. Only wellbores with extracted logs
        have any; others return `logs_not_extracted`. Time indexes are UTC."""
        return tools.list_logs(wellbore_key, index_type)

    @server.tool(annotations=READ_ONLY)
    def curve_summary(
        wellbore_key: Wellbore,
        log: Annotated[str, Field(max_length=80, description="Log id from list_logs.")],
        mnemonic: Annotated[str, Field(max_length=64, description="Exact mnemonic in the log.")],
        start: Bound = None,
        end: Bound = None,
    ) -> dict[str, Any]:
        """Count, minimum, maximum and mean of one numeric curve of one log, over an optional
        index range, with the curve's unit as the log states it. `rows_in_range` and
        `distinct_index_values` differ when the log repeats index values; all rows are
        counted. The mean is rounded to 6 decimal places."""
        return tools.curve_summary(wellbore_key, log, mnemonic, start, end)

    return server
