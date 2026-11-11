import { RELEASE } from "../test/fixtures";
import { isRelease, primaryFigures } from "./evaluation";

describe("primaryFigures", () => {
  it("sums counts and averages rates over the primary system's scored runs", () => {
    const f = primaryFigures(RELEASE);
    expect(f).not.toBeNull();
    expect(f?.wellbores).toBe(2);
    expect(f?.runs).toBe(3);
    expect(f?.claims).toBe(2307);
    expect(f?.claimsPerReview).toBe(769);
    expect(f?.contradicted).toBe(1);
    expect(f?.keyFactsWrong).toBe(0);
    expect(f?.coverage).toBeCloseTo(0.64);
    expect(f?.unsupportedRate).toBeCloseTo((0.1 + 0.05 + 0.05) / 3);
    expect(f?.unverifiableRate).toBeCloseTo(0.01);
    expect(f?.unclaimedRate).toBeCloseTo((0.02 + 0.04 + 0.02) / 3);
  });

  it("leaves runs with an undefined rate out of its mean", () => {
    const release = {
      ...RELEASE,
      runs: RELEASE.runs.map((r) =>
        r.run_id === "a" && r.first_draft
          ? { ...r, first_draft: { ...r.first_draft, unsupported_rate: null } }
          : r,
      ),
    };
    expect(primaryFigures(release)?.unsupportedRate).toBeCloseTo(0.05);
  });

  it("is null without scored primary runs", () => {
    expect(primaryFigures({ ...RELEASE, runs: [] })).toBeNull();
  });

  it("recognises a release", () => {
    expect(isRelease(RELEASE)).toBe(true);
    expect(isRelease({ release: "r2" })).toBe(false);
    expect(isRelease(null)).toBe(false);
  });
});
