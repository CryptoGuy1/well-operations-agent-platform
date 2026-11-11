import { useId } from "react";

import {
  dayNumber,
  depthSummary,
  flagText,
  depthTicks,
  panelOf,
  panels,
  xOf,
  type HoleSection,
  type Panel,
  type WellDetail,
} from "../../data/wells";
import { formatInteger } from "../../format";
import { useWidth } from "./useWidth";

const M = { left: 60, right: 12, top: 30 };
const PLOT_H = 240;
const GAP = 18; // between campaign panels
const LANE_H = 20;
const AXIS_H = 44; // dates and campaign names under the plot

const hours = (h: number) => `${h.toLocaleString("en-GB", { maximumFractionDigits: 2 })} h`;
const metres = (m: number) => `${m.toLocaleString("en-GB", { maximumFractionDigits: 1 })} m`;

export function DepthChart({ detail }: { detail: WellDetail }) {
  const [ref, width] = useWidth<HTMLDivElement>(720);
  const id = useId().replace(/[^A-Za-z0-9_-]/g, "");
  const summary = depthSummary(detail);

  const plotW = Math.max(120, width - M.left - M.right);
  const all = panels(detail.campaigns, plotW, GAP).map((p) => ({
    ...p,
    x0: p.x0 + M.left,
    x1: p.x1 + M.left,
  }));
  const placed = detail.depth_time.flatMap((pt) => {
    const day = dayNumber(pt.date);
    const panel = panelOf(all, day);
    return panel && pt.deepest_md_m !== null ? [{ pt, day, panel }] : [];
  });
  const maxDepth = Math.max(
    1,
    ...placed.map((p) => p.pt.deepest_md_m ?? 0),
    ...detail.hole_sections.map((s) => s.end_md_m ?? 0),
  );
  const ticks = depthTicks(maxDepth);
  const bottom = ticks[ticks.length - 1] ?? maxDepth;
  const y = (md: number) => M.top + (md / bottom) * PLOT_H;
  const plotBottom = M.top + PLOT_H;
  const laneTop = plotBottom + AXIS_H;
  const height = laneTop + 2 * (LANE_H + 8) + 4;
  const dayWidth = (p: Panel) => (p.x1 - p.x0) / (p.end - p.start);

  return (
    <figure className="chart" aria-labelledby={`${id}-cap`}>
      <figcaption id={`${id}-cap`}>
        <span className="chart__title">Depth against time</span>
        <span className="chart__summary">{summary}</span>
      </figcaption>
      <DepthLegend id={id} />
      <div ref={ref} className="chart__frame">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${id}-title`}
          aria-describedby={`${id}-desc`}
          className="chart__svg"
        >
          <title id={`${id}-title`}>Depth against time, {detail.name}</title>
          <desc id={`${id}-desc`}>{summary} The tables below give every value.</desc>
          <defs>
            <Hatch id={`${id}-hatch`} />
          </defs>

          {/* Hole sections as shaded bands, clipped to each campaign panel. */}
          {all.map((p) =>
            detail.hole_sections.map((s) => (
              <SectionBand key={`${p.campaign.campaign_id}-${s.section_id}`} p={p} s={s} />
            )),
          )}

          {/* Depth grid and axis. */}
          {ticks.map((t) => (
            <g key={t}>
              <line className="chart__grid" x1={M.left} x2={M.left + plotW} y1={y(t)} y2={y(t)} />
              <text className="chart__tick" x={M.left - 6} y={y(t)} dy="0.32em" textAnchor="end">
                {formatInteger(t)}
              </text>
            </g>
          ))}
          <text className="chart__tick" x={M.left - 6} y={M.top - 14} textAnchor="end">
            MD (m)
          </text>

          {/* Deepest depth so far, one line per campaign; a hollow point where the report has no
              depth of its own. */}
          {all.map((p) => {
            const pts = placed.filter((q) => q.panel === p);
            const half = dayWidth(p) / 2;
            return (
              <g key={p.campaign.campaign_id}>
                <polyline
                  className="chart__line"
                  points={pts
                    .map((q) => `${xOf(p, q.day) + half},${y(q.pt.deepest_md_m ?? 0)}`)
                    .join(" ")}
                />
                {pts.map((q) => (
                  <circle
                    key={q.pt.report_file}
                    className={q.pt.md_m === null ? "chart__dot chart__dot--open" : "chart__dot"}
                    cx={xOf(p, q.day) + half}
                    cy={y(q.pt.deepest_md_m ?? 0)}
                    r={q.pt.md_m === null ? 3 : 2.5}
                  >
                    <title>
                      {q.pt.date}: deepest {metres(q.pt.deepest_md_m ?? 0)}
                      {q.pt.md_m === null
                        ? "; depth not recorded in this report"
                        : `; reported ${metres(q.pt.md_m)}`}
                    </title>
                  </circle>
                ))}
              </g>
            );
          })}

          {/* Dates at the panel edges, campaign names, and a break mark between panels. */}
          {all.map((p, i) => {
            const wide = p.x1 - p.x0 >= 150;
            return (
              <g key={`axis-${p.campaign.campaign_id}`}>
                <line className="chart__axis" x1={p.x0} x2={p.x1} y1={plotBottom} y2={plotBottom} />
                <text className="chart__tick" x={p.x0} y={plotBottom + 14}>
                  {p.campaign.start_date_local}
                </text>
                {wide && (
                  <text className="chart__tick" x={p.x1} y={plotBottom + 14} textAnchor="end">
                    {p.campaign.end_date_local}
                  </text>
                )}
                <text
                  className="chart__label"
                  x={(p.x0 + p.x1) / 2}
                  y={plotBottom + 32}
                  textAnchor="middle"
                >
                  {wide
                    ? `Campaign ${p.campaign.campaign_number}`
                    : `C${p.campaign.campaign_number}`}
                </text>
                {i > 0 && (
                  <path
                    className="chart__break"
                    d={`M${p.x0 - GAP / 2 - 4},${plotBottom + 5} l5,-10 M${p.x0 - GAP / 2 + 1},${plotBottom + 5} l5,-10`}
                  />
                )}
              </g>
            );
          })}

          {/* Lost time by day: two lanes, one per tier, never added together. */}
          {(["primary", "possible"] as const).map((tier, lane) => {
            const top = laneTop + lane * (LANE_H + 8);
            return (
              <g key={tier}>
                <text
                  className="chart__label"
                  x={M.left - 6}
                  y={top + LANE_H / 2}
                  dy="0.32em"
                  textAnchor="end"
                >
                  {tier === "primary" ? "Primary" : "Possible"}
                </text>
                {all.map((p) => (
                  <line
                    key={p.campaign.campaign_id}
                    className="chart__axis"
                    x1={p.x0}
                    x2={p.x1}
                    y1={top + LANE_H}
                    y2={top + LANE_H}
                  />
                ))}
                {detail.lost_time.by_day
                  .filter((d) => d.tier === tier)
                  .map((d) => {
                    const day = dayNumber(d.date);
                    const p = panelOf(all, day);
                    if (!p) return null;
                    const w = Math.max(2, dayWidth(p) - 1);
                    const h = Math.max(3, (Math.min(d.hours, 24) / 24) * LANE_H);
                    return (
                      <rect
                        key={d.date}
                        className={`chart__lost chart__lost--${tier}`}
                        x={xOf(p, day)}
                        y={top + LANE_H - h}
                        width={w}
                        height={h}
                        fill={tier === "possible" ? `url(#${id}-hatch)` : undefined}
                      >
                        <title>
                          {d.date}: {tier} lost time {hours(d.hours)}
                        </title>
                      </rect>
                    );
                  })}
              </g>
            );
          })}
        </svg>
      </div>
      <DepthTables detail={detail} />
    </figure>
  );
}

function SectionBand({ p, s }: { p: Panel; s: HoleSection }) {
  const start = Math.max(dayNumber(s.start_date_local), p.start);
  const end = Math.min(dayNumber(s.end_date_local) + 1, p.end);
  if (end <= start) return null;
  const x0 = xOf(p, start);
  const w = xOf(p, end) - x0;
  const label = s.hole_size_in === null ? "size unknown" : `${String(s.hole_size_in)} in`;
  const text = w >= label.length * 6.5 + 6 ? label : w >= 14 ? String(s.section_number) : "";
  return (
    <g>
      <rect
        className={`chart__band chart__band--${s.section_number % 2 ? "odd" : "even"}`}
        x={x0}
        y={M.top}
        width={Math.max(1, w - 2)}
        height={PLOT_H}
      >
        <title>
          Section {s.section_number}, {label}: {s.start_date_local} to {s.end_date_local}
        </title>
      </rect>
      {text && (
        <text className="chart__band-label" x={x0 + 3} y={M.top - 4}>
          {text}
        </text>
      )}
    </g>
  );
}

function Hatch({ id }: { id: string }) {
  return (
    <pattern
      id={id}
      width="4"
      height="4"
      patternUnits="userSpaceOnUse"
      patternTransform="rotate(45)"
    >
      <rect width="4" height="4" className="chart__hatch-ground" />
      <line x1="0" y1="0" x2="0" y2="4" className="chart__hatch-line" />
    </pattern>
  );
}

function DepthLegend({ id }: { id: string }) {
  return (
    <ul className="chart__legend" aria-label="Legend">
      <li>
        <svg width="22" height="12" aria-hidden="true">
          <line className="chart__line" x1="1" x2="21" y1="6" y2="6" />
          <circle className="chart__dot" cx="11" cy="6" r="2.5" />
        </svg>
        Deepest measured depth so far, per report
      </li>
      <li>
        <svg width="12" height="12" aria-hidden="true">
          <circle className="chart__dot chart__dot--open" cx="6" cy="6" r="3.5" />
        </svg>
        Report without a depth of its own
      </li>
      <li>
        <svg width="16" height="12" aria-hidden="true">
          <rect className="chart__band chart__band--odd" width="16" height="12" />
        </svg>
        Hole section (shaded band)
      </li>
      <li>
        <svg width="12" height="12" aria-hidden="true">
          <rect className="chart__lost chart__lost--primary" width="12" height="12" />
        </svg>
        Primary lost time (solid)
      </li>
      <li>
        <svg width="12" height="12" aria-hidden="true">
          <defs>
            <Hatch id={`${id}-legend-hatch`} />
          </defs>
          <rect
            className="chart__lost chart__lost--possible"
            x="0.5"
            y="0.5"
            width="11"
            height="11"
            fill={`url(#${id}-legend-hatch)`}
          />
        </svg>
        Possible lost time (hatched)
      </li>
    </ul>
  );
}

// The chart's values as tables: depth per report, and lost time per day by tier.
function DepthTables({ detail }: { detail: WellDetail }) {
  const days = new Map<string, Partial<Record<string, number>>>();
  for (const d of detail.lost_time.by_day) {
    days.set(d.date, { ...days.get(d.date), [d.tier]: d.hours });
  }
  const cell = (h: number | undefined) => (h === undefined ? "–" : hours(h));
  return (
    <details className="chart__data">
      <summary>Show the chart's data as tables</summary>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Depth per report">
        <table className="data-table">
          <caption>Depth per report</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col" className="num">
                Reported MD (m)
              </th>
              <th scope="col" className="num">
                Deepest so far (m)
              </th>
              <th scope="col">Flags</th>
            </tr>
          </thead>
          <tbody>
            {detail.depth_time.map((p) => (
              <tr key={p.report_file}>
                <th scope="row" className="mono">
                  {p.date}
                </th>
                <td className="num mono">{p.md_m === null ? "not recorded" : metres(p.md_m)}</td>
                <td className="num mono">
                  {p.deepest_md_m === null ? "–" : metres(p.deepest_md_m)}
                </td>
                <td>{p.flags.map((f) => flagText(f).title).join("; ") || "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Lost time by day">
        <table className="data-table">
          <caption>Lost time by day, by tier</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col" className="num">
                Primary
              </th>
              <th scope="col" className="num">
                Possible
              </th>
            </tr>
          </thead>
          <tbody>
            {[...days].map(([date, h]) => (
              <tr key={date}>
                <th scope="row" className="mono">
                  {date}
                </th>
                <td className="num mono">{cell(h.primary)}</td>
                <td className="num mono">{cell(h.possible)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
