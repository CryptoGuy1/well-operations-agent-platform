// A fictional wells bundle: fictional wellbores, dates, depths and hours.
import type { WellDetail, WellEntry } from "../data/wells";

export const WELLS: WellEntry[] = [
  {
    key: "9001:T2",
    name: "XX/1-A-1 T2",
    split: "development",
    detail: true,
    file: "wells/9001-T2.json",
    report_count: 5,
    first_report_date: "2019-12-20",
    last_report_date: "2020-03-02",
    first_unflagged_report_date: "2020-01-01",
    report_span_days: 61.5,
    active_days: 4,
    campaigns: 2,
    flags: { before_sodir_spud: 1, depth_not_recorded: 1 },
  },
  {
    key: "9002",
    name: "XX/1-A-2",
    split: "held_out",
    detail: false,
    file: null,
    note: "Held out for evaluation; see the evaluation runs.",
  },
  {
    key: "9003",
    name: "XX/1-A-10",
    split: "outside_population",
    detail: true,
    file: "wells/9003.json",
    report_count: 1,
    first_report_date: "2020-05-01",
    last_report_date: "2020-05-01",
    first_unflagged_report_date: "2020-05-01",
    report_span_days: 1,
    active_days: 1,
    campaigns: 1,
    flags: {},
  },
];

function section(
  n: number,
  size: number | null,
  start: string,
  end: string,
  md: [number, number],
  newHole: number,
  rate: number | null,
  reason: string | null,
) {
  return {
    section_id: `9001:T2#${n}`,
    section_number: n,
    section_label: size === null ? "hole size unknown" : `${size} in`,
    hole_size_in: size,
    hole_size_source: size === null ? "unknown" : "report",
    start_date_local: start,
    end_date_local: end,
    start_md_m: md[0],
    end_md_m: md[1],
    end_tvd_m: md[1],
    casing_shoe_md_m: n === 1 ? 990.0 : null,
    report_count: 2,
    operation_phase: "drilling",
    new_hole_drilled_m: newHole,
    drill_hours: rate === null ? null : newHole / rate,
    rate_m_per_h: rate,
    rate_reason: reason,
  };
}

export const WELL: WellDetail = {
  key: "9001:T2",
  name: "XX/1-A-1 T2",
  rate_label: "average rate while coded drilling -- drill",
  hole_sections: [
    section(1, 26.0, "2020-01-01", "2020-01-02", [0, 1000], 1000, 50, null),
    section(2, null, "2020-03-01", "2020-03-02", [1000, 1000], 0, null, "no_new_hole"),
  ],
  campaigns: [
    {
      campaign_id: "9001:T2#1",
      campaign_number: 1,
      start_date_local: "2020-01-01",
      end_date_local: "2020-01-02",
      span_days: 2,
      active_days: 2,
      report_count: 2,
      operation_phase: "drilling",
    },
    {
      campaign_id: "9001:T2#2",
      campaign_number: 2,
      start_date_local: "2020-03-01",
      end_date_local: "2020-03-02",
      span_days: 2,
      active_days: 2,
      report_count: 2,
      operation_phase: "drilling",
    },
  ],
  lost_time: {
    by_tier: [
      { tier: "none", hours: 30, activities: 4 },
      { tier: "possible", hours: 2, activities: 2 },
      { tier: "primary", hours: 3.5, activities: 2 },
    ],
    by_cause: [
      { tier: "none", cause: "drilling -- drill", hours: 30, activities: 4 },
      { tier: "possible", cause: "drilling -- trip", hours: 2, activities: 2 },
      { tier: "primary", cause: "interruption -- repair", hours: 1, activities: 1 },
      { tier: "primary", cause: "interruption -- wait", hours: 2.5, activities: 1 },
    ],
    by_day: [
      { date: "2020-01-01", tier: "primary", hours: 2.5 },
      { date: "2020-01-02", tier: "possible", hours: 2 },
      { date: "2020-03-01", tier: "primary", hours: 1 },
    ],
  },
  depth_time: [
    {
      report_file: "R0",
      date: "2019-12-20",
      md_m: 10,
      deepest_md_m: 10,
      flags: ["before_sodir_spud"],
    },
    { report_file: "R1", date: "2020-01-01", md_m: 500, deepest_md_m: 500, flags: [] },
    { report_file: "R2", date: "2020-01-02", md_m: 1000, deepest_md_m: 1000, flags: [] },
    {
      report_file: "R3",
      date: "2020-03-01",
      md_m: null,
      deepest_md_m: 1000,
      flags: ["depth_not_recorded"],
    },
    { report_file: "R4", date: "2020-03-02", md_m: 1000, deepest_md_m: 1000, flags: [] },
  ],
  flags: [
    { flag: "before_sodir_spud", reports: 1, first_date: "2019-12-20", last_date: "2019-12-20" },
    { flag: "depth_not_recorded", reports: 1, first_date: "2020-03-01", last_date: "2020-03-01" },
  ],
};
