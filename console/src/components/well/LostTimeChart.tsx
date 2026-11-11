import { useId } from "react";

import { LOST_TIME_TIERS, tierHours, type LostTimeTier, type WellDetail } from "../../data/wells";
import { formatInteger } from "../../format";
import { useWidth } from "./useWidth";

const ROW_H = 38; // cause label above its bar
const BAR_H = 12;
const VALUE_W = 64; // room for the value after the longest bar

const hours = (h: number) => `${h.toLocaleString("en-GB", { maximumFractionDigits: 2 })} h`;

// The tiers of ADR 0002 D7, as amended after the lost-time review.
const TIER_TEXT: Record<LostTimeTier, string> = {
  primary:
    "Codes counted as lost time: interruption -- repair, waiting on weather, fish, lost circulation, well control and rig up/down, and drilling -- wait.",
  possible:
    "Codes that may or may not be lost time: interruption -- wait, other, maintain and sidetrack, and wait under formation evaluation, plug abandon and workover. Reported apart from primary lost time, never added to it.",
};

/** Lost time by cause, one bar chart per tier on a shared scale; the tiers are never added. */
export function LostTimeChart({ detail }: { detail: WellDetail }) {
  const causes = (tier: LostTimeTier) =>
    detail.lost_time.by_cause
      .filter((c) => c.tier === tier)
      .sort((a, b) => b.hours - a.hours || a.cause.localeCompare(b.cause));
  const max = Math.max(1, ...LOST_TIME_TIERS.flatMap((t) => causes(t).map((c) => c.hours)));
  return (
    <div className="lost">
      {LOST_TIME_TIERS.map((tier) => (
        <TierChart
          key={tier}
          tier={tier}
          rows={causes(tier)}
          max={max}
          total={tierHours(detail, tier)}
        />
      ))}
    </div>
  );
}

function TierChart({
  tier,
  rows,
  max,
  total,
}: {
  tier: LostTimeTier;
  rows: { cause: string; hours: number; activities: number }[];
  max: number;
  total: number;
}) {
  const [ref, width] = useWidth<HTMLDivElement>(360);
  const id = useId().replace(/[^A-Za-z0-9_-]/g, "");
  const name = tier === "primary" ? "Primary" : "Possible";
  const top = rows[0];
  const summary =
    rows.length === 0
      ? `${name} lost time: none recorded.`
      : `${name} lost time: ${hours(total)} in ${rows.length} ${rows.length === 1 ? "cause" : "causes"}; the largest is ${top?.cause ?? ""} with ${hours(top?.hours ?? 0)}.`;
  const barRoom = Math.max(40, width - VALUE_W);
  const height = Math.max(1, rows.length) * ROW_H;

  return (
    <figure className="chart" aria-labelledby={`${id}-cap`}>
      <figcaption id={`${id}-cap`}>
        <span className="chart__title">
          {name} lost time by cause <span className="mono chart__total">{hours(total)}</span>
        </span>
        <span className="chart__summary">{TIER_TEXT[tier]}</span>
      </figcaption>
      {rows.length === 0 ? (
        <p className="note">None recorded.</p>
      ) : (
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
            <title id={`${id}-title`}>{name} lost time by cause</title>
            <desc id={`${id}-desc`}>{summary} The table below gives every value.</desc>
            <defs>
              <pattern
                id={`${id}-hatch`}
                width="4"
                height="4"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)"
              >
                <rect width="4" height="4" className="chart__hatch-ground" />
                <line x1="0" y1="0" x2="0" y2="4" className="chart__hatch-line" />
              </pattern>
            </defs>
            {rows.map((r, i) => {
              const y = i * ROW_H;
              const w = Math.max(2, (r.hours / max) * barRoom);
              return (
                <g key={r.cause}>
                  <text className="chart__label" x={0} y={y + 13}>
                    {r.cause}
                  </text>
                  <rect
                    className={`chart__lost chart__lost--${tier}`}
                    x={0.5}
                    y={y + 19}
                    width={w}
                    height={BAR_H}
                    rx={2}
                    fill={tier === "possible" ? `url(#${id}-hatch)` : undefined}
                  >
                    <title>
                      {r.cause}: {hours(r.hours)}, {formatInteger(r.activities)} activities
                    </title>
                  </rect>
                  <text className="chart__tick" x={w + 6} y={y + 19 + BAR_H / 2} dy="0.32em">
                    {hours(r.hours)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
      <p className="visually-hidden">{summary}</p>
      {rows.length > 0 && (
        <details className="chart__data">
          <summary>Show {tier} lost time as a table</summary>
          <div className="table-scroll" tabIndex={0} role="region" aria-label={`${name} lost time`}>
            <table className="data-table">
              <caption>{name} lost time by cause</caption>
              <thead>
                <tr>
                  <th scope="col">Cause</th>
                  <th scope="col" className="num">
                    Hours
                  </th>
                  <th scope="col" className="num">
                    Activities
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.cause}>
                    <th scope="row">{r.cause}</th>
                    <td className="num mono">{hours(r.hours)}</td>
                    <td className="num mono">{formatInteger(r.activities)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">Total, {tier} only</th>
                  <td className="num mono">{hours(total)}</td>
                  <td className="num mono">
                    {formatInteger(rows.reduce((a, r) => a + r.activities, 0))}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </details>
      )}
    </figure>
  );
}
