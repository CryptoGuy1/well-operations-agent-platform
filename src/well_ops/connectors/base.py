"""Shared plumbing for the connector MCP servers (ADR 0004, tool conventions in
docs/architecture.md).

- `ConnectorServer` turns every tool failure into a `{error, detail, hint}` result that never
  echoes the caller's input. The SDK's own messages for invalid arguments include the rejected
  values, so they are replaced here.
- `resolve_wellbore` turns a D1 key or a wellbore name into a D1 key through the alias table.
- `envelope` wraps result rows with their source relations, the parameters used, the row cap and
  redaction counts.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any, Self

import duckdb
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError as SdkToolError
from mcp.types import CallToolResult, InputRequiredResult, TextContent, ToolAnnotations
from pydantic import ValidationError

from well_ops.connectors.errors import ToolError
from well_ops.connectors.guard import HeldOutGuard
from well_ops.connectors.redaction import Redactor
from well_ops.settings import Settings

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)

KEY = re.compile(r"\d+(?::T\d+)?")
NAME = re.compile(r"[A-Za-z0-9/ ._-]{1,64}")
FIELD = re.compile(r"[A-Z0-9ÆØÅ /()-]{1,40}")


def invalid_arguments(fields: Sequence[str] = ()) -> ToolError:
    named = f": {', '.join(fields)}" if fields else ""
    return ToolError(
        "invalid_arguments",
        f"One or more arguments are invalid{named}.",
        "Check the tool's input schema and description.",
    )


def wellbore_not_found() -> ToolError:
    return ToolError(
        "wellbore_not_found",
        "No wellbore matches this key or name.",
        "Use list_wellbores for keys, for example 7078:T2.",
    )


def _error_result(error: ToolError) -> CallToolResult:
    body = error.as_dict()
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(body, sort_keys=True))],
        structured_content=body,
        is_error=True,
    )


class ConnectorServer(MCPServer[Any]):
    """An MCP server whose tool errors are structured and never echo the input."""

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context[Any, Any] | None = None
    ) -> CallToolResult | InputRequiredResult:
        tool = self._tool_manager.get_tool(name)
        if tool is None:
            return _error_result(
                ToolError("unknown_tool", "No tool has this name.", "List the tools first.")
            )
        try:
            return await super().call_tool(name, arguments, context)
        except SdkToolError as exc:
            cause = exc.__cause__
            if isinstance(cause, ToolError):
                return _error_result(cause)
            if isinstance(cause, ValidationError):
                known = set(tool.parameters.get("properties", {}))
                fields = sorted({str(e["loc"][0]) for e in cause.errors() if e["loc"]} & known)
                return _error_result(invalid_arguments(fields))
            logger.error("tool %s failed", name, exc_info=cause)
            return _error_result(
                ToolError("internal_error", "The tool failed.", "Report this tool call.")
            )


def connect(path: Any) -> duckdb.DuckDBPyConnection:
    """The warehouse, opened read-only."""
    return duckdb.connect(str(path), read_only=True)


def resolve_wellbore(con: duckdb.DuckDBPyConnection, text: str) -> str:
    """The D1 key for a key (`7078:T2`) or a wellbore name (`15/9-F-11 T2`, `NO 15/9-F-11 T2`)."""
    value = " ".join(text.split())
    if KEY.fullmatch(value):
        found = con.execute(
            "select wellbore_key from marts.dim_wellbore where wellbore_key = ?", [value]
        ).fetchall()
    elif NAME.fullmatch(value):
        name = value.lower().removeprefix("no ")
        found = con.execute(
            """
            select distinct wellbore_key from (
                select wellbore_key, lower(wellbore_name) as name from marts.dim_wellbore
                union all
                select wellbore_key, lower(normalised_name)
                from staging.stg_identifiers__wellbore_alias
                where status = 'wellbore' and wellbore_key is not null
            )
            where name = ?
            """,
            [name],
        ).fetchall()
    else:
        raise invalid_arguments(["wellbore"])
    if len(found) != 1:
        raise wellbore_not_found()
    return str(found[0][0])


def field_name(text: str) -> str:
    """A field name, upper-cased with spaces collapsed, as Sodir and the workbook write it."""
    name = " ".join(text.split()).upper()
    if not FIELD.fullmatch(name):
        raise invalid_arguments(["field"])
    return name


def month_start(value: date) -> date:
    return value.replace(day=1)


def local_sql(utc: str, offset: str) -> str:
    """SQL for a UTC timestamp column shifted to local time by its `+hh:mm` offset column."""
    return (
        f"({utc} + (case when substr({offset}, 1, 1) = '-' then -1 else 1 end)"
        f" * (cast(substr({offset}, 2, 2) as int) * 60 + cast(substr({offset}, 5, 2) as int))"
        " * interval 1 minute)"
    )


def local_iso(utc: datetime | None, offset: str | None) -> str | None:
    """A UTC timestamp as local ISO 8601 with its original offset, for example
    `2013-03-23T00:00:00+01:00`."""
    if utc is None or offset is None:
        return None
    sign = -1 if offset.startswith("-") else 1
    tz = timezone(sign * timedelta(hours=int(offset[1:3]), minutes=int(offset[4:6])))
    return utc.replace(tzinfo=UTC).astimezone(tz).isoformat()


def utc_iso(utc: datetime | None) -> str | None:
    return None if utc is None else utc.replace(tzinfo=UTC).isoformat()


def iso(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def envelope(
    *,
    sources: Sequence[str],
    parameters: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    cap: int,
    redactor: Redactor,
    matched: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A tool result: rows capped at `cap`, every string redacted, and the redaction counts.

    `matched` is the number of rows the query matched, when `rows` was already limited in SQL.
    """
    kept = list(rows[:cap])
    total_rows = len(rows) if matched is None else matched
    body: dict[str, Any] = {**(extra or {}), "rows": kept}
    redacted, counts = redactor.redact_tree(body)
    total: Counter[str] = Counter(counts)
    return {
        "source": sorted(sources),
        "parameters": dict(parameters),
        "matched": total_rows,
        "returned": len(kept),
        "capped": total_rows > len(kept),
        **redacted,
        "redactions": {kind: total[kind] for kind in sorted(total) if total[kind]},
    }


class ConnectorTools:
    """Base of each connector's tools: the read-only warehouse, the guard, the redactor and the
    row cap."""

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        guard: HeldOutGuard,
        redactor: Redactor,
        row_cap: int,
    ) -> None:
        self._con = con
        self.guard = guard
        self.redactor = redactor
        self.row_cap = row_cap

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            connect(settings.warehouse_path),
            HeldOutGuard.from_settings(settings),
            Redactor.from_file(settings.redaction_denylist_path),
            settings.tool_row_cap,
        )

    def _cursor(self) -> duckdb.DuckDBPyConnection:
        return self._con.cursor()  # one cursor per call: tools run on worker threads

    def _wellbore(self, cur: duckdb.DuckDBPyConnection, text: str) -> str:
        key = resolve_wellbore(cur, text)
        self.guard.check(key)
        return key

    def _envelope(
        self,
        sources: Sequence[str],
        parameters: dict[str, Any],
        rows: Sequence[dict[str, Any]],
        cap: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return envelope(
            sources=sources,
            parameters=parameters,
            rows=rows,
            cap=cap or self.row_cap,
            redactor=self.redactor,
            **kwargs,
        )
