"""The release summary (evaluation/RULES.md): every metric reported together, as the mean and the
min-max over the runs of each wellbore and over all runs of a system. A metric a run cannot
define (accuracy without verified or contradicted claims, for example) is left out of that mean,
and the number of runs behind a value is shown when it is not every run. A task failure counts
as zero answer-key coverage."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from well_ops.evaluation.answer_key import WellboreKey

Record = Mapping[str, Any]
Getter = Callable[[Record], float | None]

STATUSES = ("scored", "task_failure", "infrastructure_failure", "budget_stopped")


def _draft(part: str, name: str) -> Getter:
    def get(record: Record) -> float | None:
        draft = record.get(part)
        if draft is None:
            return None
        value = draft[name]
        return None if value is None else float(value)

    return get


def _coverage(part: str) -> Getter:
    def get(record: Record) -> float | None:
        if record.get("status") == "task_failure":
            return 0.0
        draft = record.get(part)
        if draft is None:
            return None
        rate = draft["coverage"]["rate"]
        return None if rate is None else float(rate)

    return get


def _wrong(part: str) -> Getter:
    def get(record: Record) -> float | None:
        draft = record.get(part)
        return None if draft is None else float(draft["coverage"]["wrong"])

    return get


def _field(name: str, scale: float = 1.0) -> Getter:
    def get(record: Record) -> float | None:
        value = record.get(name)
        return None if value is None else float(value) * scale

    return get


def _removed(name: str) -> Getter:
    def get(record: Record) -> float | None:
        removed = record.get("removed")
        return None if removed is None else float(removed[name])

    return get


PERCENT, NUMBER, USD, SECONDS = "percent", "number", "usd", "seconds"


def draft_rows(part: str) -> list[tuple[str, Getter, str]]:
    return [
        ("Claim accuracy", _draft(part, "accuracy"), PERCENT),
        ("Unsupported rate", _draft(part, "unsupported_rate"), PERCENT),
        ("Unverifiable rate", _draft(part, "unverifiable_rate"), PERCENT),
        ("Unclaimed-number rate", _draft(part, "unclaimed_rate"), PERCENT),
        ("Answer-key coverage", _coverage(part), PERCENT),
        ("Key facts wrong", _wrong(part), NUMBER),
        ("Claims", _draft(part, "claims"), NUMBER),
    ]


RUN_ROWS = [
    ("Cost (USD)", _field("cost_usd"), USD),
    ("Latency (s)", _field("elapsed_ms", 1e-3), SECONDS),
]
REMOVED_ROWS = [
    ("Removed during revision: claims", _removed("claims"), NUMBER),
    ("Removed during revision: numbers", _removed("numbers"), NUMBER),
]


def _format(value: float, kind: str) -> str:
    if kind == PERCENT:
        return f"{value * 100:.1f} %"
    if kind == USD:
        return f"{value:.4f}"
    if kind == SECONDS:
        return f"{value:.0f}"
    return f"{value:.1f}" if value != int(value) else f"{value:.0f}"


def cell(records: Sequence[Record], get: Getter, kind: str) -> str:
    values = [v for v in (get(r) for r in records) if v is not None]
    if not values:
        return "n/a"
    mean = sum(values) / len(values)
    text = _format(mean, kind)
    if len(values) > 1:
        text += f" ({_format(min(values), kind)} to {_format(max(values), kind)})"
    if len(values) < len(records):
        text += f", n={len(values)}"
    return text


def metric_table(
    records: Sequence[Record], keys: Sequence[WellboreKey], rows: Sequence[tuple[str, Getter, str]]
) -> list[str]:
    """Rows are metrics; columns are the wellbores and all runs together."""
    columns = [
        (k.wellbore_name, [r for r in records if r["wellbore_key"] == k.wellbore_key]) for k in keys
    ]
    columns.append(("All runs", list(records)))
    lines = [
        "| Metric | " + " | ".join(name for name, _ in columns) + " |",
        "|---|" + "---|" * len(columns),
    ]
    for label, get, kind in rows:
        cells = [cell(rs, get, kind) if rs else "not run" for _, rs in columns]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return lines


def status_table(records: Sequence[Record], planned: Mapping[str, int]) -> list[str]:
    lines = [
        "| System | Planned | "
        + " | ".join(s.replace("_", " ") for s in STATUSES)
        + " | Not run |",
        "|---|---|" + "---|" * (len(STATUSES) + 1),
    ]
    for system, count in planned.items():
        rs = [r for r in records if r["system"] == system]
        counts = [sum(r["status"] == s for r in rs) for s in STATUSES]
        lines.append(
            f"| {system} | {count} | "
            + " | ".join(str(c) for c in counts)
            + f" | {count - len(rs)} |"
        )
    return lines


def summary(
    *,
    title: str,
    setup: Sequence[str],
    records: Sequence[Record],
    keys: Sequence[WellboreKey],
    planned: Mapping[str, int],  # runs per system
    stopped: str | None,
) -> str:
    def of(system: str) -> list[Record]:
        return [r for r in records if r["system"] == system]

    lines = [f"# {title}", "", *setup, ""]
    lines += ["## Runs", "", *status_table(records, planned), ""]
    if stopped:
        lines += [f"The release stopped early: {stopped}.", ""]
    lines += [
        "Each cell is the mean, with the minimum to maximum in brackets, over the runs of that "
        "wellbore; n is the number of runs behind a value when it is not every run.",
        "",
        "## Primary system: first draft (scored)",
        "",
        *metric_table(of("primary"), keys, draft_rows("first_draft") + RUN_ROWS),
        "",
        "## Primary system: final draft after checker feedback",
        "",
        "Reported separately; never a headline metric. Runs without a revision have no final "
        "draft.",
        "",
        *metric_table(of("primary"), keys, draft_rows("final_draft") + REMOVED_ROWS),
        "",
        "## Baseline and primary system, value only",
        "",
        "The baseline (same model, no tools) is scored on value only, with the evidence "
        "requirement waived; the primary system's first draft is shown checked the same way.",
        "",
        "### Baseline",
        "",
        *metric_table(of("baseline"), keys, draft_rows("value_only") + RUN_ROWS),
        "",
        "### Primary system, first draft, value only",
        "",
        *metric_table(of("primary"), keys, draft_rows("value_only")),
        "",
        "## Secondary model (reported separately, never pooled with the primary results)",
        "",
    ]
    secondary = of("secondary")
    if secondary:
        lines += [*metric_table(secondary, keys, draft_rows("first_draft") + RUN_ROWS), ""]
    else:
        lines += ["Not run.", ""]
    reruns = [(r, a) for r in records for a in r["attempts"] if a["error"] is not None]
    lines += ["## Infrastructure errors and reruns", ""]
    if reruns:
        lines += [
            "| System | Wellbore | Run | Run id | Error | Kind |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['system']} | {r['wellbore_name']} | {r['run']} | `{a['run_id']}` | "
            f"{a['error']} | {a['kind']} |"
            for r, a in reruns
        ]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"
