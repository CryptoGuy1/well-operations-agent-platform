"""The agent runtime (ADR 0004): a plain tool-use loop on the Messages API over the connector
MCP servers.

An agent run sends its versioned prompt as the system prompt, the task as the first user message,
and every connector tool plus `submit_review`, through which the agent hands in its document.
Tool calls go to the MCP servers; a submitted document is validated against the output contract
(validation errors go back to the model as a tool error) and then checked by the claim checker.
If any claim is contradicted, the agent gets one revision turn with the checker's findings: claim
ids, results and reasons, never the recomputed values, so a fix has to come from the tools. The
last checked document is the result, with every remaining failure shown.

The model, effort, response cap and step budget come from settings. Sampling parameters are not
sent: the API version of the installed SDK rejects them. Every model call, tool call, draft and
check is written to the run's audit log.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from anthropic.types import Message
from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters
from pydantic import ValidationError

from well_ops.agents.audit_log import RunLog, Status, canonical_json, sha256_json, sha256_text
from well_ops.agents.checker import Checker, ClaimResult, UnclaimedNumber, Verdict
from well_ops.agents.schema import Document
from well_ops.settings import Settings

# The connector servers an agent can call, by name, and their modules (`python -m <module>`).
SERVER_MODULES = {
    "drilling_reports": "well_ops.connectors.drilling_reports",
    "production": "well_ops.connectors.production",
    "sodir": "well_ops.connectors.sodir",
    "realtime": "well_ops.connectors.realtime",
}

SUBMIT = "submit_review"
SUBMIT_TOOL: dict[str, Any] = {
    "name": SUBMIT,
    "description": (
        "Hand in the finished review as a document of the output contract: agent, title, and "
        "sections of sentences with their claims. Call it once, when the review is complete; "
        "after a checker revision, call it again with the full revised document."
    ),
    "input_schema": Document.model_json_schema(),
}


def stdio_servers(repo: Path) -> dict[str, StdioServerParameters]:
    """Each connector server as a subprocess of this interpreter. The subprocess gets only the
    WELL_OPS_* settings and the variables a Python process needs, not the provider API key."""
    env = {
        k: v for k, v in os.environ.items() if k.startswith("WELL_OPS_") or k in ("PATH", "HOME")
    }
    return {
        name: StdioServerParameters(
            command=sys.executable, args=["-m", module], env=env, cwd=str(repo)
        )
        for name, module in SERVER_MODULES.items()
    }


class Toolbox:
    """Open MCP client sessions to the connector servers and their tools, in the Messages API
    tool shape. Tool names must be unique across servers."""

    def __init__(self, servers: Mapping[str, Any]) -> None:
        self._servers = servers  # name -> anything mcp.client.Client accepts
        self._stack = AsyncExitStack()
        self._clients: dict[str, Client] = {}
        self._owner: dict[str, str] = {}
        self.tools: list[dict[str, Any]] = []

    async def __aenter__(self) -> Toolbox:
        for name in sorted(self._servers):
            client = await self._stack.enter_async_context(Client(self._servers[name]))
            self._clients[name] = client
            for tool in (await client.list_tools()).tools:
                if tool.name in self._owner or tool.name == SUBMIT:
                    raise ValueError(f"tool name {tool.name!r} is not unique")
                self._owner[tool.name] = name
                self.tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                        "input_schema": tool.input_schema,
                    }
                )
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.aclose()

    async def call(self, tool: str, arguments: Mapping[str, Any]) -> tuple[str, bool, Any]:
        """(server, is_error, structured result) for one tool call."""
        server = self._owner.get(tool)
        if server is None:
            return "", True, {"error": "unknown_tool", "detail": "No such tool.", "hint": ""}
        result = await self._clients[server].call_tool(tool, dict(arguments))
        body: Any = result.structured_content
        if body is None:  # a server without structured output: keep its text
            body = {"text": [getattr(c, "text", "") for c in result.content]}
        return server, bool(result.is_error), body


class ModelClient(Protocol):
    async def create(self, params: Mapping[str, Any]) -> Message: ...


class MessagesApiModel:
    """The provider's Messages API, streamed so long responses do not time out."""

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        self._client = client or AsyncAnthropic()

    async def create(self, params: Mapping[str, Any]) -> Message:
        async with self._client.messages.stream(**params) as stream:
            return await stream.get_final_message()


@dataclass
class Outcome:
    run_id: str
    log_path: Path
    status: Status
    error: str | None
    document: Document | None
    results: list[ClaimResult] | None
    checks: list[dict[str, int]] = field(default_factory=list)  # verdict counts per check
    unclaimed: list[UnclaimedNumber] = field(default_factory=list)  # of the last check


def _usage(message: Message) -> dict[str, int]:
    u = message.usage
    return {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
        "cache_read_input_tokens": u.cache_read_input_tokens or 0,
    }


def _findings(results: Sequence[ClaimResult], unclaimed: Sequence[UnclaimedNumber]) -> str:
    failed = [r for r in results if r.verdict is not Verdict.VERIFIED]
    lines = [
        "The claim checker found these problems in your review (claim id: result, reason):",
        *(
            f"- {r.claim_id}: {r.verdict}, {r.reason}" + (f" ({r.detail})" if r.detail else "")
            for r in failed
        ),
        *(
            f"- unclaimed number {u.text!r} in section {u.section + 1}, sentence "
            f"{u.sentence + 1}: state it as a claim with evidence, or remove it"
            for u in unclaimed
        ),
        "",
        "Revise the review once. For each contradicted claim, call the tools again and state "
        "the value they give, with its evidence ids, or remove the claim if the tools do not "
        "support it. Fix unsupported claims by citing the rows the value rests on. Then call "
        f"{SUBMIT} with the full revised document.",
    ]
    return "\n".join(lines)


def _validation_errors(error: ValidationError) -> str:
    return "\n".join(
        f"- {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors()[:30]
    )


async def run_agent(
    *,
    prompt_path: Path,
    task: str,
    settings: Settings,
    model: ModelClient,
    toolbox: Toolbox,
    checker: Checker,
    log: RunLog,
) -> Outcome:
    model_id = settings.require_model()
    system = prompt_path.read_text(encoding="utf-8")
    tools = [*toolbox.tools, SUBMIT_TOOL]
    base: dict[str, Any] = {
        "model": model_id,
        "max_tokens": settings.max_tokens,
        "system": system,
        "tools": tools,
        # Caches the growing conversation prefix from turn to turn.
        "cache_control": {"type": "ephemeral"},
    }
    if settings.effort is not None:
        base["output_config"] = {"effort": settings.effort}
    fixed = {
        "model": model_id,
        "max_tokens": settings.max_tokens,
        "effort": settings.effort,
        "system_sha256": sha256_text(system),
        "tools_sha256": sha256_json(tools),
    }

    messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
    logged = 0  # messages already written to the log
    checked: tuple[Document, list[ClaimResult], list[UnclaimedNumber]] | None = None
    checks: list[dict[str, int]] = []
    revised = False
    status: Status = "stopped"
    error: str | None = "max_steps"

    for _ in range(settings.max_steps):
        request = {
            **fixed,
            "message_count": len(messages),
            "new_messages": [m for m in messages[logged:] if m["role"] == "user"],
        }
        started = time.monotonic()
        response = await model.create({**base, "messages": messages})
        log.model_call(
            request=request,
            response=response.to_dict(),
            usage=_usage(response),
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        messages.append({"role": "assistant", "content": response.content})
        logged = len(messages)

        if response.stop_reason in ("refusal", "max_tokens"):
            status, error = "failed", str(response.stop_reason)
            break
        if response.stop_reason == "pause_turn":
            continue
        uses = [b for b in response.content if b.type == "tool_use"]
        if not uses:
            messages.append({"role": "user", "content": f"Hand in the review by calling {SUBMIT}."})
            continue

        results: list[dict[str, Any]] = []
        submitted: Document | None = None
        for use in uses:
            if use.name == SUBMIT:
                try:
                    submitted = Document.model_validate(use.input)
                    content, is_error = "Received; the claim checker is running.", False
                except ValidationError as e:
                    content = "The document does not fit the output contract:\n"
                    content += _validation_errors(e)
                    is_error = True
            else:
                started = time.monotonic()
                server, is_error, body = await toolbox.call(use.name, use.input)
                log.tool_call(
                    server=server,
                    tool=use.name,
                    arguments=use.input,
                    result=body if isinstance(body, dict) else {"result": body},
                    is_error=is_error,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
                content = canonical_json(body)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": use.id,
                    "content": content,
                    "is_error": is_error,
                }
            )

        if submitted is not None:
            log.draft(submitted)
            check = checker.check(submitted)
            unclaimed = checker.unclaimed(submitted)
            log.check(check, unclaimed)
            checked = (submitted, check, unclaimed)
            checks.append(
                {str(v): sum(r.verdict is v for r in check) for v in Verdict}
                | {"unclaimed_number": len(unclaimed)}
            )
            if not revised and any(r.verdict is Verdict.CONTRADICTED for r in check):
                revised = True
                results.append({"type": "text", "text": _findings(check, unclaimed)})
                messages.append({"role": "user", "content": results})
                continue
            status, error = "completed", None
            break
        messages.append({"role": "user", "content": results})

    if checked is not None and status == "stopped":
        status, error = "completed", "revision not submitted within the step budget"
    log.end(status, error)
    if checked is None:
        return Outcome(log.run_id, log.path, status, error, None, None, checks)
    document, final, unclaimed = checked
    return Outcome(log.run_id, log.path, status, error, document, final, checks, unclaimed)
