"""The drilling-report MCP server: registers the read-only tools of `tools.DrillingReports`."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from pydantic import Field

from well_ops.connectors.base import READ_ONLY, ConnectorServer
from well_ops.connectors.drilling_reports.tools import (
    RATE_LABEL,
    Category,
    DrillingReports,
    GroupBy,
)

INSTRUCTIONS = """\
Read-only access to the Volve daily drilling reports (DDR) in the warehouse. Every row carries an
evidence id; cite it for every number you state. Results are capped; `capped` says when more rows
matched. Report and activity times are local time with the original UTC offset; hole-section
times are UTC. Text fields are redacted, and people are never named."""

DRILLING_RATE = (
    "Per hole section: new hole drilled (m), hours coded 'drilling -- drill', and their ratio in "
    f"m/h, labelled '{RATE_LABEL}'. Rates are averages over all time coded 'drilling -- drill' "
    "(which can include connections, surveys and miscoded time), not on-bottom rate of "
    "penetration. `rate_m_per_h` is null with `rate_reason` 'no_drilling_hours' when no time is "
    "coded 'drilling -- drill', and 'no_new_hole' when the section drilled no new hole."
)

Wellbore = Annotated[
    str,
    Field(
        max_length=64,
        description="Wellbore key (for example 7078:T2) or name (for example 15/9-F-11 T2).",
    ),
]


def build_server(tools: DrillingReports) -> ConnectorServer:
    server = ConnectorServer("well-ops-drilling-reports", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ_ONLY)
    def list_wellbores(
        field: Annotated[str, Field(max_length=40, description="Field name.")] = "VOLVE",
    ) -> dict[str, Any]:
        """Wellbores with drilling reports in a field: key, name, report count, and the first and
        last report dates as published. `first_unflagged_report_date` skips reports flagged as
        dated before spud (often placeholder dates); `flagged_report_count` counts those
        reports. A report date is the operations day the report covers (local time, 00:00 to
        24:00); report file names carry the following day's date."""
        return tools.list_wellbores(field)

    @server.tool(annotations=READ_ONLY)
    def well_overview(wellbore_key: Wellbore) -> dict[str, Any]:
        """One wellbore's drilling reports: report count, first and last report dates as published
        (operations days, local time), the first report date without a before-spud flag and the
        number of reports with such a flag, the deepest measured depth reported and the report
        that states it, and the number of reports with each data-quality flag."""
        return tools.well_overview(wellbore_key)

    @server.tool(annotations=READ_ONLY)
    def hole_sections(wellbore_key: Wellbore) -> dict[str, Any]:
        """Hole sections of a wellbore, in drilling order: hole size and its source ('report' or
        'unknown'), operation phase, start and end (UTC), start_date_local and end_date_local
        (the operations days of the section's first and last reports, local dates), measured
        depths, new hole drilled, activity and interruption hours. `bit_size_evidence_in` is
        evidence only, never a hole size. Section 0 ('before_first_section') holds activities
        before the first stated section."""
        return tools.hole_sections(wellbore_key)

    @server.tool(annotations=READ_ONLY)
    def lost_time(wellbore_key: Wellbore, group_by: GroupBy = "section") -> dict[str, Any]:
        """Lost-time hours of a wellbore, grouped by hole section, activity code or tier. Only
        codes in the 'primary' and 'possible' lost-time tiers are counted; 'possible' codes may
        or may not be lost time and should be reported separately."""
        return tools.lost_time(wellbore_key, group_by)

    @server.tool(annotations=READ_ONLY)
    def activities(
        wellbore_key: Wellbore,
        start: Annotated[dt.date, Field(description="First local date, inclusive.")],
        end: Annotated[dt.date, Field(description="Last local date, inclusive.")],
        category: Category | None = None,
        limit: Annotated[int, Field(ge=1, le=200)] = 200,
    ) -> dict[str, Any]:
        """Activities of a wellbore whose local start date is between `start` and `end`, in time
        order, with code, lost-time tier, depth and (redacted) comments. Times are local with
        the original UTC offset."""
        return tools.activities(wellbore_key, start, end, category, limit)

    @server.tool(annotations=READ_ONLY)
    def report(
        wellbore_key: Wellbore,
        date: Annotated[
            dt.date, Field(description="Operations day the report covers (local date).")
        ],
    ) -> dict[str, Any]:
        """One daily drilling report: depths, hole and casing status, data-quality flags, and its
        activities. `date` is the operations day the report covers (local 00:00 to 24:00); the
        report file name carries the following day's date."""
        return tools.report(wellbore_key, date)

    @server.tool(annotations=READ_ONLY, description=DRILLING_RATE)
    def drilling_rate(wellbore_key: Wellbore) -> dict[str, Any]:
        return tools.drilling_rate(wellbore_key)

    return server
