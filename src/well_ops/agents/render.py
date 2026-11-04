"""Markdown for a checked document (ADR 0004). A document is rendered only with its check
results: each sentence shows the result of each of its claims, and a table lists every claim."""

from __future__ import annotations

from collections.abc import Sequence

from well_ops.agents.checker import ClaimResult, Verdict, summary
from well_ops.agents.schema import Claim, Document

MARKS = {
    Verdict.VERIFIED: "verified",
    Verdict.CONTRADICTED: "CONTRADICTED",
    Verdict.UNSUPPORTED: "UNSUPPORTED",
    Verdict.UNVERIFIABLE: "UNVERIFIABLE",
}


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _stated(claim: Claim) -> str:
    return f"{claim.value} {claim.unit}" if claim.unit else str(claim.value)


def render_document(document: Document, results: Sequence[ClaimResult]) -> str:
    by_id = {r.claim_id: r for r in results}
    claims = list(document.claims())
    if {c.id for c in claims} != set(by_id):
        raise ValueError("every claim needs exactly one check result")
    counts = summary(results)
    lines = [
        f"# {document.title}",
        "",
        f"Agent `{document.agent}`. Claims: {len(claims)}; "
        + ", ".join(f"{n} {verdict}" for verdict, n in counts.items())
        + ".",
    ]
    for section in document.sections:
        lines += ["", f"## {section.heading}", ""]
        sentences = []
        for sentence in section.sentences:
            marks = "".join(f" [{c.id}: {MARKS[by_id[c.id].verdict]}]" for c in sentence.claims)
            sentences.append(sentence.text + marks)
        lines.append(" ".join(sentences))
    if claims:
        lines += [
            "",
            "## Claims",
            "",
            "| Claim | Type | Metric | Stated | Recomputed | Result | Reason | Evidence |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in claims:
            r = by_id[c.id]
            row = (
                c.id,
                c.type,
                c.what.metric,
                _stated(c),
                r.expected,
                MARKS[r.verdict],
                r.reason if r.detail is None else f"{r.reason}: {r.detail}",
                ", ".join(f"`{e}`" for e in c.evidence_ids),
            )
            lines.append("| " + " | ".join(_cell(v) for v in row) + " |")
    return "\n".join(lines) + "\n"
