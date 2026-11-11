// The run index (runs/index.json): the runs list, its filters, and the run the Overview offers
// to watch.

import type { EvaluationRelease } from "./types";

export const RUNS_INDEX = "runs/index.json";

// The worked-example wellbore: a development wellbore, never a held-out one.
export const FEATURED_WELLBORE = "15/9-F-11 T2";

export const RUN_VIEWER_READY: boolean = true;

export const DEVELOPMENT = "development";

export interface RunIndexEntry {
  run_id: string;
  file: string;
  source: string; // "development" or a release name
  system: string | null; // primary, baseline or secondary; null for development runs
  run: number | null;
  result_status: string | null; // the release result's status; "rerun" for a rerun attempt
  wellbore_key: string | null;
  wellbore_name: string | null;
  agent: string;
  model: string;
  prompt_path: string;
  status: string | null; // completed or failed
  error: string | null;
  started_at: string;
  cost_usd: number | null;
  elapsed_ms: number | null;
  model_calls: number | null;
  tool_calls: number | null;
  drafts: number;
  first_draft_summary: Record<string, number> | null;
}

export function isRunIndex(value: unknown): value is RunIndexEntry[] {
  return (
    Array.isArray(value) &&
    value.every(
      (e: unknown) =>
        typeof e === "object" &&
        e !== null &&
        typeof (e as Record<string, unknown>).run_id === "string" &&
        typeof (e as Record<string, unknown>).started_at === "string",
    )
  );
}

/** The latest completed run on a wellbore, or null without one. */
export function latestCompletedRun(
  index: RunIndexEntry[],
  wellboreName: string = FEATURED_WELLBORE,
): RunIndexEntry | null {
  const runs = index.filter((e) => e.wellbore_name === wellboreName && e.status === "completed");
  runs.sort((a, b) => b.started_at.localeCompare(a.started_at));
  return runs[0] ?? null;
}

/** A run of a release whose first draft has a contradicted claim: primary runs first, then the
 *  latest. Null when the release has none. */
export function checkerCatchRun(index: RunIndexEntry[], release: string): RunIndexEntry | null {
  const runs = index.filter(
    (e) =>
      e.source === release &&
      e.status === "completed" &&
      (e.first_draft_summary?.contradicted ?? 0) > 0,
  );
  runs.sort(
    (a, b) =>
      Number(b.system === "primary") - Number(a.system === "primary") ||
      b.started_at.localeCompare(a.started_at),
  );
  return runs[0] ?? null;
}

export function runPath(runId: string): string {
  return `/runs/${runId}`;
}

/** A run id as the bundle names it; anything else is not looked up. */
export function isRunId(text: string): boolean {
  return /^[A-Za-z0-9_-]{1,64}$/.test(text);
}

/** The system of a run: primary, baseline or secondary, or "development". */
export function systemOf(entry: Pick<RunIndexEntry, "system">): string {
  return entry.system ?? DEVELOPMENT;
}

/** The prompt version from its path: prompts/post_well_review/v3.md is v3. */
export function promptVersion(path: string): string {
  return /\/(v\d+)\.md$/.exec(path)?.[1] ?? path;
}

export interface ListFigures {
  claims: number | null;
  accuracy: number | null;
  unsupportedRate: number | null;
  coverage: number | null; // scored release runs only
}

/** First-draft figures of a run: from the index's check summary, and the answer-key coverage
 *  from the release results where the run was scored. */
export function listFigures(
  entry: RunIndexEntry,
  coverage: Map<string, number | null>,
): ListFigures {
  const s = entry.first_draft_summary;
  if (s === null) {
    return { claims: null, accuracy: null, unsupportedRate: null, coverage: null };
  }
  const n = (k: string) => s[k] ?? 0;
  const claims = n("verified") + n("contradicted") + n("unsupported") + n("unverifiable");
  const decided = n("verified") + n("contradicted");
  return {
    claims,
    accuracy: decided ? n("verified") / decided : null,
    unsupportedRate: claims ? n("unsupported") / claims : null,
    coverage: coverage.get(entry.run_id) ?? null,
  };
}

/** Answer-key coverage of each scored run's first draft, by run id. */
export function coverageByRun(releases: EvaluationRelease[]): Map<string, number | null> {
  const found = new Map<string, number | null>();
  for (const release of releases) {
    for (const r of release.runs) {
      if (r.first_draft) found.set(r.run_id, r.first_draft.coverage.rate);
    }
  }
  return found;
}

/** Why a run did not end in a scored draft, or null if it did. */
export function failureReason(
  entry: Pick<RunIndexEntry, "status" | "error" | "result_status">,
): string | null {
  if (entry.result_status === "rerun") {
    return `Infrastructure error (${entry.error ?? "unknown"}); the run was rerun`;
  }
  if (entry.result_status && entry.result_status !== "scored") {
    return `${entry.result_status.replace(/_/g, " ")}${entry.error ? ` (${entry.error})` : ""}`;
  }
  if (entry.status !== "completed") {
    return `Failed: ${entry.error ?? "no error recorded"}`;
  }
  return null;
}

export interface RunFilters {
  wellbore: string;
  system: string;
  model: string;
  release: string;
}

export const NO_FILTERS: RunFilters = { wellbore: "", system: "", model: "", release: "" };

export function applyFilters(index: RunIndexEntry[], f: RunFilters): RunIndexEntry[] {
  return index.filter(
    (e) =>
      (!f.wellbore || e.wellbore_name === f.wellbore) &&
      (!f.system || systemOf(e) === f.system) &&
      (!f.model || e.model === f.model) &&
      (!f.release || e.source === f.release),
  );
}

/** The choices of each filter, from the runs themselves. */
export function filterOptions(index: RunIndexEntry[]): Record<keyof RunFilters, string[]> {
  const of = (get: (e: RunIndexEntry) => string | null) =>
    [...new Set(index.map(get).filter((v): v is string => v !== null))].sort();
  return {
    wellbore: of((e) => e.wellbore_name),
    system: of(systemOf),
    model: of((e) => e.model),
    release: of((e) => e.source),
  };
}
