import {
  checkerCatchRun,
  isRunIndex,
  latestCompletedRun,
  runPath,
  type RunIndexEntry,
} from "./runs";

function entry(id: string, name: string | null, status: string, at: string): RunIndexEntry {
  return {
    run_id: id,
    file: `runs/${id}.json`,
    source: "development",
    system: null,
    run: null,
    result_status: null,
    wellbore_key: name === null ? null : "9001",
    wellbore_name: name,
    agent: "post_well_review",
    model: "test-model",
    prompt_path: "prompts/post_well_review/v3.md",
    status,
    error: status === "failed" ? "TestError" : null,
    started_at: at,
    cost_usd: 0.1,
    elapsed_ms: 1000,
    model_calls: 2,
    tool_calls: 1,
    drafts: 1,
    first_draft_summary: null,
  };
}

describe("latestCompletedRun", () => {
  const index = [
    entry("old", "XX/1-A-1", "completed", "2020-01-01T10:00:00+00:00"),
    entry("new", "XX/1-A-1", "completed", "2020-01-03T10:00:00+00:00"),
    entry("failed", "XX/1-A-1", "failed", "2020-01-04T10:00:00+00:00"),
    entry("other", "XX/1-A-2", "completed", "2020-01-05T10:00:00+00:00"),
    entry("unknown", null, "failed", "2020-01-06T10:00:00+00:00"),
  ];

  it("takes the latest completed run on the wellbore", () => {
    expect(latestCompletedRun(index, "XX/1-A-1")?.run_id).toBe("new");
  });

  it("is null without a completed run", () => {
    expect(latestCompletedRun(index, "XX/1-A-9")).toBeNull();
  });

  it("links to the run viewer and recognises an index", () => {
    expect(runPath("new")).toBe("/runs/new");
    expect(isRunIndex(index)).toBe(true);
    expect(isRunIndex([{ run_id: 1 }])).toBe(false);
  });
});

describe("the runs list", () => {
  it("derives first-draft figures, coverage where scored, and failure reasons", async () => {
    const { INDEX } = await import("../test/runFixture");
    const { listFigures, failureReason, applyFilters, filterOptions, NO_FILTERS } =
      await import("./runs");
    const coverage = new Map([["run-fixture-r9", 0.5]]);
    const dev = listFigures(INDEX[0]!, coverage);
    expect(dev).toEqual({ claims: 5, accuracy: 2 / 3, unsupportedRate: 0.2, coverage: null });
    expect(listFigures(INDEX[2]!, coverage).coverage).toBe(0.5);
    expect(listFigures(INDEX[1]!, coverage).claims).toBeNull();
    expect(failureReason(INDEX[1]!)).toBe("Failed: TestTimeout");
    expect(failureReason({ status: "failed", error: "ReadTimeout", result_status: "rerun" })).toBe(
      "Infrastructure error (ReadTimeout); the run was rerun",
    );
    expect(failureReason(INDEX[0]!)).toBeNull();
    expect(filterOptions(INDEX).system).toEqual(["development", "primary"]);
    expect(applyFilters(INDEX, { ...NO_FILTERS, system: "development" })).toHaveLength(2);
    expect(
      applyFilters(INDEX, { ...NO_FILTERS, release: "r9", model: "other-model" }),
    ).toHaveLength(1);
  });
});

describe("checkerCatchRun", () => {
  it("finds a completed release run with a contradicted claim, primary first", () => {
    const base = entry("a", "XX/1-A-1", "completed", "2020-01-01T00:00:00Z");
    const caught = { ...base, first_draft_summary: { verified: 3, contradicted: 1 } };
    const index: RunIndexEntry[] = [
      { ...caught, run_id: "dev" }, // development, not the release
      { ...caught, run_id: "baseline", source: "r9", system: "baseline", started_at: "2020-03" },
      { ...caught, run_id: "primary", source: "r9", system: "primary" },
      { ...base, run_id: "clean", source: "r9", system: "primary", started_at: "2020-04" },
      { ...caught, run_id: "failed", source: "r9", system: "primary", status: "failed" },
    ];
    expect(checkerCatchRun(index, "r9")?.run_id).toBe("primary");
    expect(checkerCatchRun(index, "r8")).toBeNull();
  });
});
