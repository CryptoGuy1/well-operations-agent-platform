// Release figures for the console, computed from a release's run results exactly as the release
// summary computes them (src/well_ops/evaluation/report.py): a rate is the mean over runs of each
// run's rate, leaving out runs where it is not defined; counts are summed.

import type { DraftScore, EvaluationRelease, RunResult } from "./types";

export const HEADLINE_RELEASE = "r2";
export const PRIMARY = "primary";

export function isRelease(value: unknown): value is EvaluationRelease {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.release === "string" && Array.isArray(v.runs);
}

export function releasePath(release: string): string {
  return `evaluation/${release}.json`;
}

export interface Figures {
  release: string;
  model: string | null;
  wellbores: number;
  runs: number;
  claimsPerReview: number;
  claims: number;
  contradicted: number;
  keyFactsWrong: number;
  coverage: number | null;
  unsupportedRate: number | null;
  unverifiableRate: number | null;
  unclaimedRate: number | null;
}

function mean(values: (number | null)[]): number | null {
  const defined = values.filter((v): v is number => v !== null);
  return defined.length ? defined.reduce((a, b) => a + b, 0) / defined.length : null;
}

function sum(values: number[]): number {
  return values.reduce((a, b) => a + b, 0);
}

/** First-draft figures of the primary system's scored runs; null without any. */
export function primaryFigures(release: EvaluationRelease): Figures | null {
  const scored = release.runs.filter(
    (r): r is RunResult & { first_draft: DraftScore } =>
      r.system === PRIMARY && r.status === "scored" && r.first_draft !== null,
  );
  if (!scored.length) return null;
  const drafts = scored.map((r) => r.first_draft);
  const models = new Set(scored.map((r) => r.model));
  return {
    release: release.release,
    model: models.size === 1 ? (scored[0]?.model ?? null) : null,
    wellbores: new Set(scored.map((r) => r.wellbore_key)).size,
    runs: scored.length,
    claimsPerReview: sum(drafts.map((d) => d.claims)) / drafts.length,
    claims: sum(drafts.map((d) => d.claims)),
    contradicted: sum(drafts.map((d) => d.contradicted)),
    keyFactsWrong: sum(drafts.map((d) => d.coverage.wrong)),
    coverage: mean(drafts.map((d) => d.coverage.rate)),
    unsupportedRate: mean(drafts.map((d) => d.unsupported_rate)),
    unverifiableRate: mean(drafts.map((d) => d.unverifiable_rate)),
    unclaimedRate: mean(drafts.map((d) => d.unclaimed_rate)),
  };
}
