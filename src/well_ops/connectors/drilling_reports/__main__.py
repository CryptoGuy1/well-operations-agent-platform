"""Run the drilling-report MCP server on stdio: `make serve-ddr`."""

from __future__ import annotations

from well_ops.connectors.drilling_reports.server import build_server
from well_ops.connectors.drilling_reports.tools import DrillingReports
from well_ops.settings import Settings


def main() -> None:
    build_server(DrillingReports.from_settings(Settings())).run("stdio")


if __name__ == "__main__":
    main()
