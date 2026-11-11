import { WELL, WELLS } from "../test/wellFixture";
import {
  dayNumber,
  depthSummary,
  depthTicks,
  isWellDetail,
  isWellIndex,
  panelOf,
  panels,
  rateReason,
  tierHours,
  wellPath,
  wellRunsPath,
  xOf,
} from "./wells";

describe("wells data", () => {
  it("recognises the bundle files and names the pages", () => {
    expect(isWellIndex(WELLS)).toBe(true);
    expect(isWellDetail(WELL)).toBe(true);
    expect(isWellDetail({ key: "x" })).toBe(false);
    expect(wellPath(WELLS[0]!)).toBe("/wells/9001-T2");
    expect(wellRunsPath("XX/1-A-2")).toBe("/runs?wellbore=XX%2F1-A-2");
    expect(rateReason("no_new_hole")).toBe("no new hole drilled");
    expect(rateReason(null)).toBe("unknown");
  });

  it("keeps the lost-time tiers apart", () => {
    expect(tierHours(WELL, "primary")).toBe(3.5);
    expect(tierHours(WELL, "possible")).toBe(2);
  });

  it("puts each campaign in its own panel, with a gap between", () => {
    const all = panels(WELL.campaigns, 200, 20);
    expect(all.map((p) => [p.x0, p.x1])).toEqual([
      [0, 90],
      [110, 200],
    ]);
    const day = dayNumber("2020-01-02");
    expect(panelOf(all, day)).toBe(all[0]);
    expect(xOf(all[0]!, day)).toBe(45);
    // A report before spud is in no campaign, so it is not plotted.
    expect(panelOf(all, dayNumber("2019-12-20"))).toBeUndefined();
  });

  it("gives round depth ticks", () => {
    expect(depthTicks(4562.1)).toEqual([0, 1000, 2000, 3000, 4000, 5000]);
    expect(depthTicks(1000)).toEqual([0, 200, 400, 600, 800, 1000]);
  });

  it("states the chart in words", () => {
    expect(depthSummary(WELL)).toBe(
      "5 reports in 2 campaigns, from 2020-01-01 to 2020-03-02. " +
        "The deepest measured depth reported is 1,000 m, first on 2020-01-02. " +
        "2 hole sections. " +
        "There is primary lost time on 2 days (3.5 h) and possible lost time on 1 day (2 h); " +
        "the two tiers are kept apart, never added. " +
        "1 report gave no depth of its own. " +
        "1 report outside the campaigns (dated before spud) is not plotted.",
    );
  });
});
