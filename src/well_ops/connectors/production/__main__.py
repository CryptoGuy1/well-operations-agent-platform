"""Run the production MCP server on stdio: `make serve-prod`."""

from __future__ import annotations

from well_ops.connectors.production.server import build_server
from well_ops.connectors.production.tools import Production
from well_ops.settings import Settings


def main() -> None:
    build_server(Production.from_settings(Settings())).run("stdio")


if __name__ == "__main__":
    main()
