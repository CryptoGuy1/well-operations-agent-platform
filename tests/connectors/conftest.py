"""The `mcp` fixture for connector server tests: build a synthetic warehouse and call tools over
MCP."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import duckdb
import pytest
from mcp.client.client import Client

from well_ops.connectors.base import ConnectorServer
from well_ops.connectors.guard import not_available

WELLBORE_SCHEMA = """
create schema if not exists staging; create schema if not exists marts;
create table marts.dim_wellbore (wellbore_key varchar, wellbore_name varchar, field_name varchar);
create table staging.stg_identifiers__wellbore_alias (
    normalised_name varchar, wellbore_key varchar, status varchar);
"""


class Mcp:
    refusal = not_available().as_dict()

    @staticmethod
    def build_warehouse(
        path: Path,
        schema: str,
        wellbores: Iterable[tuple[str, str, str]],
        rows: dict[str, Sequence[tuple[Any, ...]]],
    ) -> Path:
        """A DuckDB file with the wellbore tables, `schema`, and `rows` inserted per table."""
        con = duckdb.connect(str(path))
        con.execute(WELLBORE_SCHEMA)
        con.execute(schema)
        con.executemany("insert into marts.dim_wellbore values (?, ?, ?)", list(wellbores))
        for table, values in rows.items():
            if values:
                marks = ", ".join("?" * len(values[0]))
                con.executemany(f"insert into {table} values ({marks})", list(values))
        con.close()
        return path

    @staticmethod
    def call(server: ConnectorServer, name: str, **arguments: Any) -> tuple[bool, dict[str, Any]]:
        async def run() -> tuple[bool, dict[str, Any]]:
            async with Client(server) as client:
                result = await client.call_tool(name, arguments)
            assert result.structured_content is not None
            return bool(result.is_error), result.structured_content

        return asyncio.run(run())

    @staticmethod
    def ok(server: ConnectorServer, name: str, **arguments: Any) -> dict[str, Any]:
        is_error, body = Mcp.call(server, name, **arguments)
        assert not is_error, body
        return body

    @staticmethod
    def error(server: ConnectorServer, name: str, **arguments: Any) -> dict[str, Any]:
        is_error, body = Mcp.call(server, name, **arguments)
        assert is_error, body
        return body


@pytest.fixture
def mcp() -> type[Mcp]:
    return Mcp
