"""Run the real-time MCP server on stdio: `make serve-rt`."""

from __future__ import annotations

from well_ops.connectors.realtime.server import build_server
from well_ops.connectors.realtime.tools import Realtime
from well_ops.settings import Settings


def main() -> None:
    build_server(Realtime.from_settings(Settings())).run("stdio")


if __name__ == "__main__":
    main()
