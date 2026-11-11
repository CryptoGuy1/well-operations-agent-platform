import { isRunIndex, latestCompletedRun, runPath, type RunIndexEntry } from "./runs";

function entry(id: string, name: string | null, status: string, at: string): RunIndexEntry {
  return {
    run_id: id,
    source: "development",
    wellbore_key: name === null ? null : "9001",
    wellbore_name: name,
    status,
    started_at: at,
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
