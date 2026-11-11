// The run index (runs/index.json) and the run the Overview offers to watch.

export const RUNS_INDEX = "runs/index.json";

// The worked-example wellbore: a development wellbore, never a held-out one.
export const FEATURED_WELLBORE = "15/9-F-11 T2";

// The run viewer arrives with the next console step; until then the Overview shows its button
// disabled.
export const RUN_VIEWER_READY: boolean = false;

export interface RunIndexEntry {
  run_id: string;
  source: string; // "development" or a release name
  wellbore_key: string | null;
  wellbore_name: string | null;
  status: string | null;
  started_at: string;
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

export function runPath(runId: string): string {
  return `/runs/${runId}`;
}
