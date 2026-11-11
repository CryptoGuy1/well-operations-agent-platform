// Placing claims in their sentence: each claim is shown on the number, date or text it states,
// found in the sentence the way the checker reads numbers (src/well_ops/agents/checker.py).
// A claim whose value is not written in its sentence is listed after the sentence instead.

import type { Claim, RunFile } from "./runTypes";

// ISO dates and months, then numbers not inside a word, wellbore name or code, with optional
// thousands separators and decimals.
const TOKEN =
  /(?<![\w-])\d{4}-\d{2}(?:-\d{2})?(?![\w-])|(?<![\w/.,-])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w/-]|[.,]\d)/g;

export type Segment =
  | { kind: "text"; text: string }
  | { kind: "claim"; text: string; claim: Claim }
  | { kind: "unclaimed"; text: string };

interface Span {
  start: number;
  end: number;
  claim?: Claim;
}

function tokens(text: string): Span[] {
  return [...text.matchAll(TOKEN)].map((m) => ({ start: m.index, end: m.index + m[0].length }));
}

function overlaps(span: Span, taken: Span[]): boolean {
  return taken.some((t) => span.start < t.end && t.start < span.end);
}

function numeric(written: string): number {
  return Number(written.replace(/,/g, ""));
}

/** The sentence split into plain text, claim spans and unclaimed numbers, and the claims whose
 *  value is not written in the sentence. */
export function segmentSentence(
  text: string,
  claims: Claim[],
  unclaimed: string[] = [],
): { segments: Segment[]; unplaced: Claim[] } {
  const all = tokens(text);
  const taken: Span[] = [];
  const unplaced: Claim[] = [];
  let from = 0; // claims are written in order: search after the previous one first
  for (const claim of claims) {
    let found: Span | undefined;
    if (typeof claim.value === "number") {
      const value = claim.value;
      const fits = (s: Span) =>
        !overlaps(s, taken) && numeric(text.slice(s.start, s.end)) === value;
      found = all.find((s) => s.start >= from && fits(s)) ?? all.find(fits);
    } else if (claim.value !== "") {
      const value = claim.value;
      const at = (start: number) => {
        const i = text.indexOf(value, start);
        return i < 0 ? undefined : { start: i, end: i + value.length };
      };
      let span = at(from) ?? at(0);
      while (span && overlaps(span, taken)) span = at(span.start + 1);
      found = span;
    }
    if (found) {
      taken.push({ ...found, claim });
      from = found.end;
    } else {
      unplaced.push(claim);
    }
  }
  for (const written of unclaimed) {
    const span = all.find((s) => text.slice(s.start, s.end) === written && !overlaps(s, taken));
    if (span) taken.push(span);
  }
  taken.sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let at = 0;
  for (const span of taken) {
    if (span.start > at) segments.push({ kind: "text", text: text.slice(at, span.start) });
    const written = text.slice(span.start, span.end);
    segments.push(
      span.claim
        ? { kind: "claim", text: written, claim: span.claim }
        : { kind: "unclaimed", text: written },
    );
    at = span.end;
  }
  if (at < text.length) segments.push({ kind: "text", text: text.slice(at) });
  return { segments, unplaced };
}

/** The element id of a claim in the rendered draft. */
export function claimElementId(claimId: string): string {
  return `claim-${claimId}`;
}

/** A claim's scope in words: "wellbore 7078:T2, section 1". */
export function scopeText(claim: Claim): string {
  return Object.entries(claim.what)
    .filter(([k]) => k !== "metric")
    .map(([k, v]) => `${k} ${String(v)}`)
    .join(", ");
}

/** The first contradicted claim of a run's first draft, or null. */
export function firstContradictedClaim(run: RunFile): string | null {
  const results = run.drafts[0]?.check?.results ?? [];
  return results.find((r) => r.verdict === "contradicted")?.claim_id ?? null;
}
