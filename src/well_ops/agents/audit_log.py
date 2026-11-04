"""The run audit log (ADR 0004): append-only JSONL run records, a DuckDB loader and replay.

Each run is one file, `<runs_dir>/<run_id>.jsonl`, created once and then only appended to. Every
line is one event:

    {"run_id", "seq", "type", "at", "prev", "data"}

`seq` counts from 0 and `prev` is the SHA-256 of the previous line (empty for the first), so a
changed, removed or reordered line breaks the chain and `verify` fails. Event types, in order:
`run_start` (agent, prompt path and hash, model, settings, prices, code version), then any number
of `model_call` (request, response, token usage, cost, latency) and `tool_call` (server, tool,
arguments, evidence ids, result and its hash, latency), `draft` (the agent's document), `check`
(claim checker results), `run_end` (status and totals), and `approval` (a reviewer's decision,
also after `run_end`). Logs hold redacted tool results; they stay under `data/` and are never
committed.

`load` builds a DuckDB file of runs, events, tool calls and claims from the JSONL files, which
remain the record.

Cost is computed from the logged tokens and the configured prices (`Prices`); without prices, or
for a call with token kinds the prices do not cover (such as cache tokens without cache prices),
it stays unknown.
Tokens are always logged.

`replay` renders a run from its log alone; with a checker it also re-checks the logged draft
against the current warehouse.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

import duckdb

from well_ops.agents.checker import Checker, ClaimResult, UnclaimedNumber, summary
from well_ops.agents.render import render_document
from well_ops.agents.schema import Document
from well_ops.settings import Settings

EVENT_TYPES = ("run_start", "model_call", "tool_call", "draft", "check", "run_end", "approval")
Status = Literal["completed", "failed", "stopped"]
Decision = Literal["approved", "rejected"]
Clock = Callable[[], dt.datetime]


class LogIntegrityError(ValueError):
    """A run log whose hash chain, sequence or structure is broken."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_version(repo: Path = Path()) -> str | None:
    """The git commit, with `-dirty` if the working tree has changes; None outside git."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{head}-dirty" if dirty else head


def new_run_id(now: dt.datetime) -> str:
    return f"{now:%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def evidence_ids(value: Any) -> list[str]:
    """Every evidence id in a tool result, sorted and unique: values of `evidence_id`,
    `evidence_ids` and `*_evidence_id` keys at any depth."""
    found: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, Mapping):
            for key, item in v.items():
                if key == "evidence_ids" and isinstance(item, list):
                    found.update(i for i in item if isinstance(i, str))
                elif key.endswith("evidence_id") and isinstance(item, str):
                    found.add(item)
                else:
                    walk(item)
        elif isinstance(v, list):
            for item in v:
                walk(item)

    walk(value)
    return sorted(found)


@dataclass(frozen=True)
class Prices:
    """Model prices in USD per million tokens, as listed by the provider on `checked_on`."""

    input_per_mtok_usd: float
    output_per_mtok_usd: float
    checked_on: dt.date
    cache_write_per_mtok_usd: float | None = None
    cache_read_per_mtok_usd: float | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> Prices | None:
        if (
            settings.price_input_per_mtok_usd is None
            or settings.price_output_per_mtok_usd is None
            or settings.price_checked_on is None
        ):
            return None
        return cls(
            settings.price_input_per_mtok_usd,
            settings.price_output_per_mtok_usd,
            settings.price_checked_on,
            settings.price_cache_write_per_mtok_usd,
            settings.price_cache_read_per_mtok_usd,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Prices | None:
        if data is None:
            return None
        return cls(
            data["input_per_mtok_usd"],
            data["output_per_mtok_usd"],
            dt.date.fromisoformat(data["checked_on"]),
            data.get("cache_write_per_mtok_usd"),
            data.get("cache_read_per_mtok_usd"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_per_mtok_usd": self.input_per_mtok_usd,
            "output_per_mtok_usd": self.output_per_mtok_usd,
            "checked_on": self.checked_on.isoformat(),
            "cache_write_per_mtok_usd": self.cache_write_per_mtok_usd,
            "cache_read_per_mtok_usd": self.cache_read_per_mtok_usd,
        }

    def cost(self, usage: Mapping[str, int | None]) -> float | None:
        """USD for one call; None if the usage holds a token kind without a price."""
        rates = {
            "input_tokens": self.input_per_mtok_usd,
            "output_tokens": self.output_per_mtok_usd,
            "cache_creation_input_tokens": self.cache_write_per_mtok_usd,
            "cache_read_input_tokens": self.cache_read_per_mtok_usd,
        }
        total = 0.0
        for kind, n in usage.items():
            if not n:
                continue
            rate = rates.get(kind)
            if rate is None:
                return None
            total += n * rate / 1e6
        return round(total, 6)


class RunLog:
    """Appends the events of one run. Use `create` for a new run and `open` to append to an
    existing one (for example an approval)."""

    def __init__(
        self,
        path: Path,
        run_id: str,
        seq: int,
        prev: str,
        ended: bool,
        clock: Clock,
        prices: Prices | None,
    ) -> None:
        self.path = path
        self.prices = prices
        self.run_id = run_id
        self._seq = seq
        self._prev = prev
        self._ended = ended
        self._clock = clock

    @classmethod
    def create(
        cls,
        runs_dir: Path,
        *,
        agent: str,
        prompt_path: Path,
        model: str,
        settings: Mapping[str, Any],
        code_version: str | None,
        prices: Prices | None,
        run_id: str | None = None,
        clock: Clock = utc_now,
    ) -> Self:
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_id = run_id or new_run_id(clock())
        path = runs_dir / f"{run_id}.jsonl"
        path.open("x").close()  # a run file is created once; an existing one is never reused
        log = cls(path, run_id, 0, "", False, clock, prices)
        log._append(
            "run_start",
            {
                "agent": agent,
                "prompt_path": prompt_path.as_posix(),
                "prompt_sha256": sha256_file(prompt_path),
                "model": model,
                "settings": dict(settings),
                "prices": None if prices is None else prices.as_dict(),
                "code_version": code_version,
            },
        )
        return log

    @classmethod
    def open(cls, path: Path, clock: Clock = utc_now) -> Self:
        events = read_events(path)
        last = path.read_text(encoding="utf-8").splitlines()[-1]
        ended = any(e["type"] == "run_end" for e in events)
        prices = Prices.from_dict(events[0]["data"]["prices"])
        return cls(path, events[0]["run_id"], len(events), sha256_text(last), ended, clock, prices)

    def model_call(
        self,
        *,
        request: Mapping[str, Any],
        response: Mapping[str, Any],
        usage: Mapping[str, int | None],
        latency_ms: int,
    ) -> None:
        """`usage` holds the provider's token counts, at least input_tokens and output_tokens."""
        if not all(isinstance(usage.get(k), int) for k in ("input_tokens", "output_tokens")):
            raise ValueError("usage needs input_tokens and output_tokens")
        cost_usd = None if self.prices is None else self.prices.cost(usage)
        self._append(
            "model_call",
            {
                "request": dict(request),
                "response": dict(response),
                "usage": dict(usage),
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            },
        )

    def tool_call(
        self,
        *,
        server: str,
        tool: str,
        arguments: Mapping[str, Any],
        result: Mapping[str, Any],
        is_error: bool,
        latency_ms: int,
    ) -> None:
        self._append(
            "tool_call",
            {
                "server": server,
                "tool": tool,
                "arguments": dict(arguments),
                "is_error": is_error,
                "evidence_ids": evidence_ids(result),
                "result_sha256": sha256_json(result),
                "result": dict(result),
                "latency_ms": latency_ms,
            },
        )

    def draft(self, document: Document) -> None:
        self._append("draft", {"document": document.model_dump(mode="json")})

    def check(
        self, results: Sequence[ClaimResult], unclaimed: Sequence[UnclaimedNumber] = ()
    ) -> None:
        self._append(
            "check",
            {
                "results": [r.as_dict() for r in results],
                "unclaimed": [u.as_dict() for u in unclaimed],
                "summary": {**summary(results), "unclaimed_number": len(unclaimed)},
            },
        )

    def end(self, status: Status, error: str | None = None) -> None:
        at = self._clock()
        totals = _totals(read_events(self.path), at)
        self._append("run_end", {"status": status, "error": error, **totals}, at)
        self._ended = True

    def approval(self, *, decision: Decision, reviewer: str, note: str | None = None) -> None:
        self._append("approval", {"decision": decision, "reviewer": reviewer, "note": note})

    def _append(
        self, event_type: str, data: Mapping[str, Any], at: dt.datetime | None = None
    ) -> None:
        if self._ended and event_type != "approval":
            raise LogIntegrityError("the run has ended; only approvals can be appended")
        line = canonical_json(
            {
                "run_id": self.run_id,
                "seq": self._seq,
                "type": event_type,
                "at": (at or self._clock()).isoformat(),
                "prev": self._prev,
                "data": dict(data),
            }
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._seq += 1
        self._prev = sha256_text(line)


def _totals(events: Sequence[Mapping[str, Any]], ended: dt.datetime) -> dict[str, Any]:
    calls = [e["data"] for e in events if e["type"] == "model_call"]
    costs = [c["cost_usd"] for c in calls]
    tokens: dict[str, int] = {}
    for call in calls:
        for name, n in call["usage"].items():
            tokens[name] = tokens.get(name, 0) + int(n or 0)
    started = dt.datetime.fromisoformat(events[0]["at"])
    return {
        "model_calls": len(calls),
        "tool_calls": sum(e["type"] == "tool_call" for e in events),
        "usage": dict(sorted(tokens.items())),
        # Unknown if any call's cost is unknown.
        "cost_usd": None if None in costs else round(sum(costs), 6),
        "elapsed_ms": int((ended - started).total_seconds() * 1000),
    }


def read_events(path: Path) -> list[dict[str, Any]]:
    """The events of one run log, after checking its hash chain and sequence."""
    events: list[dict[str, Any]] = []
    prev = ""
    for seq, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            raise LogIntegrityError(f"line {seq + 1} is not JSON") from None
        if event.get("seq") != seq or event.get("prev") != prev:
            raise LogIntegrityError(f"hash chain broken at line {seq + 1}")
        if event.get("type") not in EVENT_TYPES:
            raise LogIntegrityError(f"unknown event type at line {seq + 1}")
        if seq and event.get("run_id") != events[0]["run_id"]:
            raise LogIntegrityError(f"run id changes at line {seq + 1}")
        events.append(event)
        prev = sha256_text(line)
    if not events or events[0]["type"] != "run_start":
        raise LogIntegrityError("a run log starts with run_start")
    return events


@dataclass(frozen=True)
class Run:
    events: list[dict[str, Any]]

    @classmethod
    def read(cls, path: Path) -> Self:
        return cls(read_events(path))

    @property
    def run_id(self) -> str:
        return str(self.events[0]["run_id"])

    @property
    def start(self) -> dict[str, Any]:
        return dict(self.events[0]["data"])

    def of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e["data"] for e in self.events if e["type"] == event_type]

    def last(self, event_type: str) -> dict[str, Any] | None:
        found = self.of_type(event_type)
        return found[-1] if found else None

    @property
    def document(self) -> Document | None:
        draft = self.last("draft")
        return None if draft is None else Document.model_validate(draft["document"])

    @property
    def results(self) -> list[ClaimResult] | None:
        check = self.last("check")
        return None if check is None else [ClaimResult.from_dict(r) for r in check["results"]]

    @property
    def unclaimed(self) -> list[UnclaimedNumber]:
        check = self.last("check")
        return [UnclaimedNumber.from_dict(u) for u in (check or {}).get("unclaimed", [])]


# --- DuckDB loader ---------------------------------------------------------------------------

TABLES = {
    "runs": """
        run_id varchar primary key, agent varchar, model varchar, prompt_path varchar,
        prompt_sha256 varchar, code_version varchar, started_at timestamptz,
        ended_at timestamptz, status varchar, model_calls integer, tool_calls integer,
        input_tokens bigint, output_tokens bigint, cost_usd double, elapsed_ms bigint,
        claims integer, verified integer, contradicted integer, unsupported integer,
        unverifiable integer, unclaimed_numbers integer, approval varchar""",
    "events": "run_id varchar, seq integer, type varchar, event_at timestamptz, data json",
    "tool_calls": """
        run_id varchar, seq integer, server varchar, tool varchar, arguments json,
        is_error boolean, evidence_count integer, result_sha256 varchar, latency_ms bigint""",
    "claims": """
        run_id varchar, claim_id varchar, type varchar, metric varchar, value varchar,
        unit varchar, evidence_ids varchar[], verdict varchar, reason varchar,
        expected varchar""",
}


def _run_row(run: Run) -> tuple[Any, ...]:
    start, end = run.start, run.last("run_end") or {}
    usage = end.get("usage", {})
    counts = summary(run.results or [])
    approval = run.last("approval")
    return (
        run.run_id,
        start["agent"],
        start["model"],
        start["prompt_path"],
        start["prompt_sha256"],
        start["code_version"],
        run.events[0]["at"],
        next((e["at"] for e in run.events if e["type"] == "run_end"), None),
        end.get("status"),
        end.get("model_calls"),
        end.get("tool_calls"),
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        end.get("cost_usd"),
        end.get("elapsed_ms"),
        len(run.results) if run.results is not None else None,
        *counts.values(),
        len(run.unclaimed) if run.results is not None else None,
        approval["decision"] if approval else None,
    )


def _claim_rows(run: Run) -> Iterable[tuple[Any, ...]]:
    document, results = run.document, run.results
    if document is None:
        return
    by_id = {r.claim_id: r for r in results or []}
    for claim in document.claims():
        result = by_id.get(claim.id)
        yield (
            run.run_id,
            claim.id,
            str(claim.type),
            claim.what.metric,
            str(claim.value),
            claim.unit,
            list(claim.evidence_ids),
            str(result.verdict) if result else None,
            result.reason if result else None,
            None if result is None or result.expected is None else str(result.expected),
        )


def load(runs_dir: Path, db_path: Path) -> dict[str, int]:
    """Rebuild the runs database from every run log in `runs_dir`; returns rows per table.

    The database is written to a temporary file and moved into place, so a failed load leaves
    the previous one intact. A log with a broken chain stops the load."""
    runs = [Run.read(p) for p in sorted(runs_dir.glob("*.jsonl"))]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    try:
        for name, columns in TABLES.items():
            con.execute(f"create table {name} ({columns})")
        rows: dict[str, list[tuple[Any, ...]]] = {name: [] for name in TABLES}
        for run in runs:
            rows["runs"].append(_run_row(run))
            for e in run.events:
                rows["events"].append(
                    (run.run_id, e["seq"], e["type"], e["at"], canonical_json(e["data"]))
                )
                if e["type"] == "tool_call":
                    d = e["data"]
                    rows["tool_calls"].append(
                        (
                            run.run_id,
                            e["seq"],
                            d["server"],
                            d["tool"],
                            canonical_json(d["arguments"]),
                            d["is_error"],
                            len(d["evidence_ids"]),
                            d["result_sha256"],
                            d["latency_ms"],
                        )
                    )
            rows["claims"].extend(_claim_rows(run))
        for name, values in rows.items():
            if values:
                marks = ", ".join("?" * len(values[0]))
                con.executemany(f"insert into {name} values ({marks})", values)
    finally:
        con.close()
    tmp.replace(db_path)
    return {name: len(values) for name, values in rows.items()}


# --- Replay ----------------------------------------------------------------------------------


def replay(path: Path, checker: Checker | None = None) -> str:
    """Markdown for a run, from its log alone. With a checker, the logged draft is also checked
    against the current warehouse and changed results are listed."""
    run = Run.read(path)
    start, end = run.start, run.last("run_end")
    lines = [
        f"# Run {run.run_id}",
        "",
        f"- Agent: `{start['agent']}`; model: `{start['model']}`",
        f"- Prompt: `{start['prompt_path']}` (SHA-256 `{start['prompt_sha256'][:12]}`)",
        f"- Code version: `{start['code_version']}`",
        f"- Settings: `{canonical_json(start['settings'])}`",
        "- Prices: "
        + (
            "not configured, so cost is unknown"
            if start["prices"] is None
            else f"USD {start['prices']['input_per_mtok_usd']} input and "
            f"{start['prices']['output_per_mtok_usd']} output per million tokens, "
            f"checked on {start['prices']['checked_on']}"
        ),
    ]
    if end is None:
        lines.append("- Status: not ended")
    else:
        cost = "unknown" if end["cost_usd"] is None else f"USD {end['cost_usd']}"
        lines += [
            f"- Status: {end['status']}" + (f" ({end['error']})" if end["error"] else ""),
            f"- Model calls: {end['model_calls']}; tool calls: {end['tool_calls']}; "
            f"tokens: {canonical_json(end['usage'])}; cost: {cost}; "
            f"elapsed: {end['elapsed_ms']} ms",
        ]
    for approval in run.of_type("approval"):
        lines.append(f"- Review: {approval['decision']} by {approval['reviewer']}")
    calls = run.of_type("tool_call")
    if calls:
        lines += [
            "",
            "## Tool calls",
            "",
            "| # | Server | Tool | Arguments | Error | Evidence ids | Result SHA-256 |",
            "|---|---|---|---|---|---|---|",
        ]
        for n, c in enumerate(calls, 1):
            lines.append(
                f"| {n} | {c['server']} | {c['tool']} | `{canonical_json(c['arguments'])}` | "
                f"{'yes' if c['is_error'] else 'no'} | {len(c['evidence_ids'])} | "
                f"`{c['result_sha256'][:12]}` |"
            )
    document, results = run.document, run.results
    lines.append("")
    if document is None:
        lines.append("No draft was logged.")
    elif results is None:
        lines.append("The draft was not checked, so it is not rendered (ADR 0004).")
    else:
        rendered = render_document(document, results, run.unclaimed).rstrip().splitlines()
        lines += ["#" + line if line.startswith("#") else line for line in rendered]
        if checker is not None:
            lines += ["", *_recheck(document, results, checker)]
            lines.append(
                f"Unclaimed numbers: {len(run.unclaimed)} logged, "
                f"{len(checker.unclaimed(document))} now."
            )
    return "\n".join(lines) + "\n"


def _recheck(document: Document, logged: Sequence[ClaimResult], checker: Checker) -> list[str]:
    now = {r.claim_id: r for r in checker.check(document)}
    changed = [
        (r, now[r.claim_id])
        for r in logged
        if (now[r.claim_id].verdict, now[r.claim_id].reason) != (r.verdict, r.reason)
    ]
    lines = ["## Re-check against the current warehouse", ""]
    if not changed:
        return [*lines, f"All {len(logged)} results are unchanged."]
    lines += ["| Claim | Logged | Now | Reason now |", "|---|---|---|---|"]
    lines += [
        f"| {old.claim_id} | {old.verdict} | {new.verdict} | {new.reason} |" for old, new in changed
    ]
    return lines
