// The wells bundle (wells.json and wells/<key>.json), as exported by
// well_ops.console_data.wells. Held-out wellbores are listed with key, name and split role only,
// and have no detail file (docs/adr/0005-console-architecture.md).

export const WELLS_INDEX = "wells.json";

export const LOST_TIME_TIERS = ["primary", "possible"] as const;
export type LostTimeTier = (typeof LOST_TIME_TIERS)[number];

export interface WellEntry {
  key: string;
  name: string;
  split: string; // development, held_out or outside_population
  detail: boolean;
  file: string | null;
  note?: string;
  report_count?: number;
  first_report_date?: string;
  last_report_date?: string;
  first_unflagged_report_date?: string;
  report_span_days?: number | null;
  active_days?: number;
  campaigns?: number;
  flags?: Record<string, number>;
}

export interface HoleSection {
  section_id: string;
  section_number: number;
  section_label: string;
  hole_size_in: number | null;
  hole_size_source: string;
  start_date_local: string;
  end_date_local: string;
  start_md_m: number | null;
  end_md_m: number | null;
  end_tvd_m: number | null;
  casing_shoe_md_m: number | null;
  report_count: number;
  operation_phase: string | null;
  new_hole_drilled_m: number | null;
  drill_hours: number | null;
  rate_m_per_h: number | null;
  rate_reason: string | null;
}

export interface Campaign {
  campaign_id: string;
  campaign_number: number;
  start_date_local: string;
  end_date_local: string;
  span_days: number;
  active_days: number;
  report_count: number;
  operation_phase: string | null;
}

export interface DepthPoint {
  report_file: string;
  date: string;
  md_m: number | null;
  deepest_md_m: number | null;
  flags: string[];
}

export interface CauseHours {
  tier: string;
  cause: string;
  hours: number;
  activities: number;
}

export interface DayHours {
  date: string;
  tier: string;
  hours: number;
}

export interface FlagSummary {
  flag: string;
  reports: number;
  first_date: string;
  last_date: string;
}

export interface WellDetail {
  key: string;
  name: string;
  hole_sections: HoleSection[];
  rate_label: string;
  campaigns: Campaign[];
  lost_time: {
    by_tier: { tier: string; hours: number; activities: number }[];
    by_cause: CauseHours[];
    by_day: DayHours[];
  };
  depth_time: DepthPoint[];
  flags: FlagSummary[];
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isWellIndex(value: unknown): value is WellEntry[] {
  return (
    Array.isArray(value) &&
    value.every(
      (e: unknown) =>
        isObject(e) &&
        typeof e.key === "string" &&
        typeof e.name === "string" &&
        typeof e.split === "string",
    )
  );
}

export function isWellDetail(value: unknown): value is WellDetail {
  return (
    isObject(value) &&
    typeof value.key === "string" &&
    Array.isArray(value.hole_sections) &&
    Array.isArray(value.campaigns) &&
    Array.isArray(value.depth_time) &&
    Array.isArray(value.flags) &&
    isObject(value.lost_time) &&
    Array.isArray(value.lost_time.by_day)
  );
}

/** The address of a well page: its file name without the extension (7078:T2 is 7078-T2). */
export function wellSlug(entry: Pick<WellEntry, "key">): string {
  return entry.key.replace(/:/g, "-");
}

export function wellPath(entry: Pick<WellEntry, "key">): string {
  return `/wells/${wellSlug(entry)}`;
}

/** A well page address as the bundle names it; anything else is not looked up. */
export function isWellSlug(text: string): boolean {
  return /^[A-Za-z0-9-]{1,32}$/.test(text);
}

/** The runs list filtered to one wellbore. */
export function wellRunsPath(name: string): string {
  return `/runs?${new URLSearchParams({ wellbore: name }).toString()}`;
}

export const SPLIT_LABELS: Record<string, string> = {
  development: "Development",
  held_out: "Held out",
  outside_population: "Outside the evaluation",
};

export function splitLabel(split: string): string {
  return SPLIT_LABELS[split] ?? split;
}

// The data-quality flags of int_ddr__report_flag, in plain language. Flags mark doubtful
// reports; nothing is corrected or removed.
export const FLAG_TEXT: Record<string, { title: string; meaning: string }> = {
  depth_not_recorded: {
    title: "Depth not recorded",
    meaning:
      "The report gives its measured depth as −999.99, the source's placeholder for a missing value. The depth chart carries the deepest depth reported so far through these days.",
  },
  before_sodir_spud: {
    title: "Dated before the spud date in Sodir",
    meaning:
      "The report ends on or before the wellbore's spud date in the Sodir FactPages, so its date is doubtful. It is left out of the campaigns and of the depth chart.",
  },
  before_report_spud: {
    title: "Dated before the report's own spud time",
    meaning:
      "The report ends on or before the spud time stated in the report itself, so its date is doubtful. It is left out of the campaigns and of the depth chart.",
  },
  activity_gap_or_overlap: {
    title: "Activities do not join up",
    meaning:
      "In the report, an activity starts before or after the previous one ends, so the day's hours do not add up cleanly.",
  },
  no_activities: {
    title: "No activities",
    meaning:
      "The report lists no activities, so it adds no hours to the hole sections or to lost time.",
  },
};

export function flagText(flag: string): { title: string; meaning: string } {
  return FLAG_TEXT[flag] ?? { title: flag.replace(/_/g, " "), meaning: "No description." };
}

export const RATE_REASONS: Record<string, string> = {
  no_drilling_hours: "no coded drilling hours",
  no_new_hole: "no new hole drilled",
};

export function rateReason(reason: string | null): string {
  return reason === null ? "unknown" : (RATE_REASONS[reason] ?? reason.replace(/_/g, " "));
}

/** Total hours of one lost-time tier; tiers are never added together. */
export function tierHours(detail: WellDetail, tier: LostTimeTier): number {
  return detail.lost_time.by_tier.find((t) => t.tier === tier)?.hours ?? 0;
}

/** The deepest measured depth of the wellbore's reports and the first date it was reported. */
export function deepest(points: DepthPoint[]): { md: number; date: string } | null {
  let best: { md: number; date: string } | null = null;
  for (const p of points) {
    if (p.md_m !== null && (best === null || p.md_m > best.md)) best = { md: p.md_m, date: p.date };
  }
  return best;
}

// --- Depth against time: geometry of the chart, kept apart from drawing so it can be tested.

const DAY_MS = 86_400_000;

/** An ISO date as a whole day number. */
export function dayNumber(date: string): number {
  const [y, m, d] = date.split("-").map(Number);
  return Math.round(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1) / DAY_MS);
}

export interface Panel {
  campaign: Campaign;
  start: number; // first day
  end: number; // the day after the last
  x0: number;
  x1: number;
}

/** One panel per campaign, side by side with a gap between, widths in proportion to their days
 *  (with a floor, so a short campaign stays visible). */
export function panels(campaigns: Campaign[], width: number, gap: number): Panel[] {
  if (campaigns.length === 0 || width <= 0) return [];
  const spans = campaigns.map(
    (c) => dayNumber(c.end_date_local) + 1 - dayNumber(c.start_date_local),
  );
  const total = spans.reduce((a, b) => a + b, 0);
  const floor = total * 0.08;
  const weights = spans.map((s) => Math.max(s, floor));
  const sum = weights.reduce((a, b) => a + b, 0);
  const room = Math.max(0, width - gap * (campaigns.length - 1));
  const out: Panel[] = [];
  let x = 0;
  campaigns.forEach((c, i) => {
    const w = (room * (weights[i] ?? 0)) / sum;
    const start = dayNumber(c.start_date_local);
    out.push({ campaign: c, start, end: start + (spans[i] ?? 1), x0: x, x1: x + w });
    x += w + gap;
  });
  return out;
}

/** The panel holding a day, or undefined: reports outside every campaign are not plotted. */
export function panelOf(all: Panel[], day: number): Panel | undefined {
  return all.find((p) => day >= p.start && day < p.end);
}

/** The x of a day's left edge within its panel. */
export function xOf(p: Panel, day: number): number {
  return p.x0 + ((day - p.start) / (p.end - p.start)) * (p.x1 - p.x0);
}

/** Round, readable depth ticks from 0 to at least `max`. */
export function depthTicks(max: number): number[] {
  if (max <= 0) return [0];
  const raw = max / 5;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * pow >= raw) ?? 10) * pow;
  const ticks = [];
  for (let t = 0; t < max + step; t += step) ticks.push(t);
  return ticks;
}

/** The depth chart in words, for its caption and for screen readers. */
export function depthSummary(detail: WellDetail): string {
  const points = detail.depth_time;
  const count = (n: number, one: string, many = `${one}s`) =>
    `${n.toLocaleString("en-GB")} ${n === 1 ? one : many}`;
  const h = (n: number) => `${n.toLocaleString("en-GB", { maximumFractionDigits: 2 })} h`;
  const parts: string[] = [];
  const c = detail.campaigns;
  const first = c[0];
  const last = c[c.length - 1];
  parts.push(
    first && last
      ? `${count(points.length, "report")} in ${count(c.length, "campaign")}, from ${first.start_date_local} to ${last.end_date_local}.`
      : `${count(points.length, "report")} and no campaign.`,
  );
  const top = deepest(points);
  if (top) {
    parts.push(
      `The deepest measured depth reported is ${top.md.toLocaleString("en-GB", { maximumFractionDigits: 1 })} m, first on ${top.date}.`,
    );
  }
  parts.push(`${count(detail.hole_sections.length, "hole section")}.`);
  const tier = (t: LostTimeTier) => {
    const days = new Set(detail.lost_time.by_day.filter((d) => d.tier === t).map((d) => d.date));
    return `${t} lost time on ${count(days.size, "day")} (${h(tierHours(detail, t))})`;
  };
  parts.push(
    `There is ${tier("primary")} and ${tier("possible")}; the two tiers are kept apart, never added.`,
  );
  const unplaced = points.filter((p) => {
    const day = dayNumber(p.date);
    return !c.some(
      (x) => day >= dayNumber(x.start_date_local) && day <= dayNumber(x.end_date_local),
    );
  }).length;
  const missing = points.filter((p) => p.md_m === null).length;
  if (missing) parts.push(`${count(missing, "report")} gave no depth of its own.`);
  if (unplaced) {
    parts.push(
      `${count(unplaced, "report")} outside the campaigns (dated before spud) ${unplaced === 1 ? "is" : "are"} not plotted.`,
    );
  }
  return parts.join(" ");
}
