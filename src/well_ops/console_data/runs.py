"""runs/index.json and runs/<run_id>.json: precomputed agent runs for the console.

Each run file holds the steps (model calls and tool calls, with arguments and row counts but not
the rows), the first and final drafts with their check results, what the revision removed, cost,
latency, model and prompt hash, and the warehouse rows the drafts' claims cite, with every string
redacted. Tool results are not exported.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from well_ops.agents.audit_log import Run
from well_ops.agents.checker import fetch
from well_ops.agents.revision import removed_in_revision
from well_ops.agents.schema import Document
from well_ops.connectors import evidence
from well_ops.connectors.base import resolve_wellbore
from well_ops.connectors.errors import ToolError
from well_ops.connectors.redaction import Redactor

TASK = re.compile(r"for wellbore (?P<name>.+)\.$")
DEVELOPMENT = "development"


@dataclass(frozen=True)
class Source:
    """Where a run comes from: development runs, or one evaluation release."""

    name: str  # "development" or a release name, r2
    path: Path  # a run log


@dataclass(frozen=True)
class EvaluationRun:
    """A run's place in an evaluation release, from the committed results."""

    system: str
    run: int
    wellbore_key: str
    wellbore_name: str
    status: str  # the result's status, or "rerun" for an attempt that was rerun


def evaluation_runs(results_dir: Path) -> dict[str, EvaluationRun]:
    """Every attempt of every run of a release's results, by run id."""
    found = {}
    for path in sorted(results_dir.glob("runs/*/*.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        for attempt in r["attempts"]:
            final = attempt["run_id"] == r["run_id"]
            found[attempt["run_id"]] = EvaluationRun(
                r["system"],
                r["run"],
                r["wellbore_key"],
                r["wellbore_name"],
                r["status"] if final else "rerun",
            )
    return found


def _task_wellbore(run: Run) -> str | None:
    """The wellbore named in the run's task, the first user message."""
    calls = run.of_type("model_call")
    if not calls:
        return None
    content = calls[0]["request"].get("new_messages", [{}])[0].get("content")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    match = TASK.search(content or "")
    return match["name"] if match else None


def _steps(run: Run, redactor: Redactor) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for event in run.events:
        data, seq = event["data"], event["seq"]
        if event["type"] == "model_call":
            usage = data["usage"]
            steps.append(
                {
                    "seq": seq,
                    "type": "model_call",
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "cache_write_tokens": usage.get("cache_creation_input_tokens"),
                    "cache_read_tokens": usage.get("cache_read_input_tokens"),
                    "stop_reason": data["response"].get("stop_reason"),
                    "cost_usd": data["cost_usd"],
                    "latency_ms": data["latency_ms"],
                }
            )
        elif event["type"] == "tool_call":
            result = data["result"]
            arguments, _ = redactor.redact_tree(data["arguments"])
            steps.append(
                {
                    "seq": seq,
                    "type": "tool_call",
                    "server": data["server"],
                    "tool": data["tool"],
                    "arguments": arguments,
                    "is_error": data["is_error"],
                    "error_code": result.get("error") if data["is_error"] else None,
                    "matched": result.get("matched"),
                    "returned": result.get("returned"),
                    "capped": result.get("capped"),
                    "evidence_count": len(data["evidence_ids"]),
                    "latency_ms": data["latency_ms"],
                }
            )
        elif event["type"] in ("draft", "check", "approval"):
            steps.append({"seq": seq, "type": event["type"]})
    return steps


def _drafts(run: Run, redactor: Redactor) -> list[dict[str, Any]]:
    """Each draft with the check that follows it, in order: the first is the scored one."""
    drafts: list[dict[str, Any]] = []
    for event in run.events:
        if event["type"] == "draft":
            document, _ = redactor.redact_tree(event["data"]["document"])
            drafts.append({"seq": event["seq"], "document": document, "check": None})
        elif event["type"] == "check" and drafts and drafts[-1]["check"] is None:
            drafts[-1]["check"], _ = redactor.redact_tree(event["data"])
    return drafts


def _removed(run: Run, redactor: Redactor) -> dict[str, Any] | None:
    first, final = run.first_document, run.document
    if first is None or final is None or len(run.of_type("draft")) < 2:
        return None
    removed = removed_in_revision(first, final)
    claims, _ = redactor.redact_tree([c.model_dump(mode="json") for c in removed.claims])
    numbers, _ = redactor.redact_tree(removed.numbers)
    return {"claims": claims, "numbers": numbers}


def _cited(drafts: Sequence[Mapping[str, Any]]) -> list[str]:
    ids: set[str] = set()
    for d in drafts:
        for claim in Document.model_validate(d["document"]).claims():
            ids.update(claim.evidence_ids)
    return sorted(ids)


def evidence_rows(
    cur: duckdb.DuckDBPyConnection, ids: Sequence[str], redactor: Redactor
) -> dict[str, dict[str, Any]]:
    """The warehouse row of each cited id, every string redacted; ids that name no single row
    get a status instead."""
    rows: dict[str, dict[str, Any]] = {}
    for text in ids:
        try:
            eid = evidence.parse(text)
        except evidence.EvidenceIdError:
            rows[text] = {"status": "malformed"}
            continue
        if eid.kind == "rt:log-value":
            rows[text] = {"status": "not_a_single_row", "relation": eid.relation}
            continue
        row = fetch(cur, eid)
        if row is None:
            rows[text] = {"status": "not_found", "relation": eid.relation}
            continue
        redacted, _ = redactor.redact_tree(row)
        rows[text] = {"status": "found", "relation": eid.relation, "row": redacted}
    return rows


def export_run(
    run: Run,
    source: str,
    cur: duckdb.DuckDBPyConnection,
    redactor: Redactor,
    held_out: frozenset[str],
    evaluation: EvaluationRun | None = None,
) -> dict[str, Any]:
    """One run file. A development run on a held-out wellbore is refused."""
    start, end = run.start, run.last("run_end") or {}
    key: str | None
    name: str | None
    if evaluation is not None:
        key, name = evaluation.wellbore_key, evaluation.wellbore_name
    elif run.of_type("model_call"):
        name = _task_wellbore(run)
        if name is None:
            raise ValueError(f"run {run.run_id}: no wellbore in its task")
        try:
            key = resolve_wellbore(cur, name)
        except ToolError:
            raise ValueError(f"run {run.run_id}: its wellbore is not in the warehouse") from None
        if key in held_out:
            raise ValueError(f"run {run.run_id}: a development run on a held-out wellbore")
    else:  # failed before its first model call: the log does not record the wellbore
        key = name = None
    drafts = _drafts(run, redactor)
    return {
        "run_id": run.run_id,
        "source": source,
        "system": evaluation.system if evaluation else None,
        "run": evaluation.run if evaluation else None,
        "result_status": evaluation.status if evaluation else None,
        "wellbore_key": key,
        "wellbore_name": name,
        "agent": start["agent"],
        "model": start["model"],
        "prompt_path": start["prompt_path"],
        "prompt_sha256": start["prompt_sha256"],
        "code_version": start["code_version"],
        "started_at": run.events[0]["at"],
        "status": end.get("status"),
        "error": end.get("error"),
        "cost_usd": end.get("cost_usd"),
        "elapsed_ms": end.get("elapsed_ms"),
        "model_calls": end.get("model_calls"),
        "tool_calls": end.get("tool_calls"),
        "usage": end.get("usage"),
        "steps": _steps(run, redactor),
        "drafts": drafts,
        "removed_in_revision": _removed(run, redactor),
        "evidence": evidence_rows(cur, _cited(drafts), redactor),
    }


def index_entry(exported: Mapping[str, Any]) -> dict[str, Any]:
    first = exported["drafts"][0]["check"] if exported["drafts"] else None
    return {
        "file": f"runs/{exported['run_id']}.json",
        "first_draft_summary": None if first is None else first["summary"],
        "drafts": len(exported["drafts"]),
        **{
            k: exported[k]
            for k in (
                "run_id",
                "source",
                "system",
                "run",
                "result_status",
                "wellbore_key",
                "wellbore_name",
                "agent",
                "model",
                "prompt_path",
                "prompt_sha256",
                "started_at",
                "status",
                "error",
                "cost_usd",
                "elapsed_ms",
                "model_calls",
                "tool_calls",
            )
        },
    }
