"""Run the Sodir MCP server on stdio: `make serve-sodir`."""

from __future__ import annotations

from well_ops.connectors.sodir.server import build_server
from well_ops.connectors.sodir.tools import Sodir
from well_ops.settings import Settings


def main() -> None:
    build_server(Sodir.from_settings(Settings())).run("stdio")


if __name__ == "__main__":
    main()
