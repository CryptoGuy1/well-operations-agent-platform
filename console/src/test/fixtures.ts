// A fictional release: fictional wellbores, numbers and run ids.
import type { DraftScore, EvaluationRelease, RunResult } from "../data/types";

export function draft(
  over: Partial<DraftScore> & { rate?: number | null; wrong?: number },
): DraftScore {
  const { rate = 0.5, wrong = 0, ...rest } = over;
  return {
    claims: 100,
    verified: 95,
    contradicted: 0,
    unsupported: 5,
    unverifiable: 0,
    unclaimed: 2,
    accuracy: 1,
    unsupported_rate: 0.05,
    unverifiable_rate: 0,
    unclaimed_rate: 0.02,
    coverage: { facts: 10, covered: 5, wrong, missing: 5, rate },
    ...rest,
  };
}

export function run(
  id: string,
  wellbore: string,
  first: DraftScore | null,
  over: Partial<RunResult> = {},
): RunResult {
  return {
    run_id: id,
    system: "primary",
    run: 1,
    wellbore_key: wellbore,
    wellbore_name: `XX/1-${wellbore}`,
    model: "test-model",
    status: "scored",
    first_draft: first,
    final_draft: null,
    value_only: null,
    cost_usd: 0.1,
    elapsed_ms: 1000,
    ...over,
  };
}

export const RELEASE: EvaluationRelease = {
  release: "r2",
  summary_md: null,
  runs: [
    run("a", "A-1", draft({ claims: 200, contradicted: 1, unsupported_rate: 0.1, rate: 0.6 })),
    run("b", "A-1", draft({ claims: 210, unclaimed_rate: 0.04, rate: 0.7 })),
    run("c", "A-2", draft({ claims: 1897, unverifiable_rate: 0.03, rate: 0.62 })),
    run("d", "A-2", draft({ claims: 5000, contradicted: 9, rate: 0.1 }), { system: "baseline" }),
    run("e", "A-3", null, { status: "task_failure" }),
  ],
};

export function mockFetch(files: Record<string, unknown>): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn((url: string) => {
    const name = Object.keys(files).find((f) => url.endsWith(`data/${f}`));
    return Promise.resolve(
      name === undefined
        ? new Response("missing", { status: 404 })
        : new Response(JSON.stringify(files[name]), { status: 200 }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
