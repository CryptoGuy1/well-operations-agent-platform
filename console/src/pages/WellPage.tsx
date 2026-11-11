import type { ReactNode } from "react";
import { Link, useParams } from "react-router";

import { Badge } from "../components/Badge";
import { DepthChart } from "../components/well/DepthChart";
import { LostTimeChart } from "../components/well/LostTimeChart";
import {
  RUNS_INDEX,
  failureReason,
  isRunIndex,
  listFigures,
  runPath,
  systemOf,
} from "../data/runs";
import { useBundle } from "../data/useBundle";
import {
  WELLS_INDEX,
  deepest,
  flagText,
  isWellDetail,
  isWellIndex,
  isWellSlug,
  rateReason,
  splitLabel,
  tierHours,
  wellRunsPath,
  wellSlug,
  type WellDetail,
  type WellEntry,
} from "../data/wells";
import { formatInteger, formatPercent } from "../format";

const metres = (m: number | null) =>
  m === null ? "unknown" : `${m.toLocaleString("en-GB", { maximumFractionDigits: 1 })} m`;
const hours = (h: number) => `${h.toLocaleString("en-GB", { maximumFractionDigits: 2 })} h`;

export function WellPage() {
  const { slug = "" } = useParams();
  const index = useBundle(WELLS_INDEX, isWellIndex);
  if (!isWellSlug(slug)) return <NotFound />;
  if (index.state === "loading") return <p aria-live="polite">Loading the well…</p>;
  if (index.state === "error") {
    return <p role="alert">The wells could not be loaded ({index.error.message}).</p>;
  }
  const entry = index.data.find((w) => wellSlug(w) === slug);
  if (!entry) return <NotFound />;
  if (!entry.detail || entry.file === null) return <HeldOut entry={entry} />;
  return <LoadedWell entry={entry} file={entry.file} />;
}

function NotFound() {
  return (
    <>
      <h1>Well not found</h1>
      <p>
        There is no such wellbore in the data bundle. <Link to="/wells">See all wells</Link>.
      </p>
    </>
  );
}

// Held-out wellbores have no detail page: name and role only, and their evaluation runs.
function HeldOut({ entry }: { entry: WellEntry }) {
  return (
    <>
      <p className="breadcrumb">
        <Link to="/wells">Wells</Link> /
      </p>
      <h1 className="mono">{entry.name}</h1>
      <p>
        <Badge tone="warning">{splitLabel(entry.split)}</Badge> {entry.note}
      </p>
      <p>
        <Link to={wellRunsPath(entry.name)}>See its evaluation runs</Link>.
      </p>
    </>
  );
}

function LoadedWell({ entry, file }: { entry: WellEntry; file: string }) {
  const loaded = useBundle(file, isWellDetail);
  if (loaded.state === "loading") return <p aria-live="polite">Loading the well…</p>;
  if (loaded.state === "error") {
    return <p role="alert">The well could not be loaded ({loaded.error.message}).</p>;
  }
  return <WellView entry={entry} detail={loaded.data} />;
}

function WellView({ entry, detail }: { entry: WellEntry; detail: WellDetail }) {
  const top = deepest(detail.depth_time);
  return (
    <div className="well-page">
      <p className="breadcrumb">
        <Link to="/wells">Wells</Link> /
      </p>
      <h1 className="mono">{detail.name}</h1>
      <dl className="run-meta well-facts">
        <Fact term="Wellbore key" mono>
          {detail.key}
        </Fact>
        <Fact term="Role">{splitLabel(entry.split)}</Fact>
        <Fact term="Reports" mono>
          {formatInteger(entry.report_count ?? detail.depth_time.length)}
        </Fact>
        <Fact term="Report span">
          <span className="mono">
            <span className="date">{entry.first_report_date}</span> to{" "}
            <span className="date">{entry.last_report_date}</span>
          </span>
          {entry.report_span_days != null && (
            <span className="cell-sub">
              {entry.report_span_days.toLocaleString("en-GB")} days,{" "}
              {formatInteger(entry.active_days ?? 0)} active
            </span>
          )}
        </Fact>
        <Fact term="Campaigns" mono>
          {formatInteger(detail.campaigns.length)}
        </Fact>
        <Fact term="Hole sections" mono>
          {formatInteger(detail.hole_sections.length)}
        </Fact>
        <Fact term="Deepest reported MD" mono>
          {top ? metres(top.md) : "unknown"}
        </Fact>
        <Fact term="Primary lost time" mono>
          {hours(tierHours(detail, "primary"))}
        </Fact>
        <Fact term="Possible lost time" mono>
          {hours(tierHours(detail, "possible"))}
        </Fact>
      </dl>
      {entry.first_unflagged_report_date &&
        entry.first_unflagged_report_date !== entry.first_report_date && (
          <p className="note">
            The first report without a spud-date flag is dated{" "}
            <span className="mono">{entry.first_unflagged_report_date}</span>; the report span is
            counted from it.
          </p>
        )}

      <section aria-labelledby="depth-heading">
        <h2 id="depth-heading">Drilling history</h2>
        <DepthChart detail={detail} />
      </section>

      <section aria-labelledby="sections-heading">
        <h2 id="sections-heading">Hole sections</h2>
        <SectionsTable detail={detail} />
      </section>

      <section aria-labelledby="lost-heading">
        <h2 id="lost-heading">Lost time by tier and cause</h2>
        <p>
          Lost time is measured in hours of coded activities. The two tiers are reported side by
          side and never added together.
        </p>
        <LostTimeChart detail={detail} />
      </section>

      <section aria-labelledby="flags-heading">
        <h2 id="flags-heading">Data-quality flags</h2>
        <Flags detail={detail} />
      </section>

      <section aria-labelledby="runs-heading">
        <h2 id="runs-heading">Agent runs on this well</h2>
        <WellRuns name={detail.name} />
      </section>
    </div>
  );
}

function Fact({
  term,
  mono = false,
  children,
}: {
  term: string;
  mono?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <dt>{term}</dt>
      <dd className={mono ? "mono" : undefined}>{children}</dd>
    </div>
  );
}

function SectionsTable({ detail }: { detail: WellDetail }) {
  if (detail.hole_sections.length === 0) {
    return <p className="note">The reports give no hole sections.</p>;
  }
  return (
    <>
      <p className="note">
        Rate: the {detail.rate_label}, the section's new hole over its hours coded drilling --
        drill. Where a section has no rate, the reason is given.
      </p>
      <div className="table-scroll" tabIndex={0} role="region" aria-labelledby="sections-caption">
        <table className="data-table">
          <caption id="sections-caption" className="visually-hidden">
            Hole sections of {detail.name}
          </caption>
          <thead>
            <tr>
              <th scope="col">Section</th>
              <th scope="col">Hole size</th>
              <th scope="col">Dates</th>
              <th scope="col" className="num">
                Start MD
              </th>
              <th scope="col" className="num">
                End MD
              </th>
              <th scope="col" className="num">
                New hole
              </th>
              <th scope="col">Phase</th>
              <th scope="col" className="num">
                Rate (m/h)
              </th>
              <th scope="col" className="num">
                Casing shoe MD
              </th>
            </tr>
          </thead>
          <tbody>
            {detail.hole_sections.map((s) => (
              <tr key={s.section_id}>
                <th scope="row" className="mono">
                  {s.section_number}
                </th>
                <td>
                  {s.hole_size_in === null ? (
                    "unknown"
                  ) : (
                    <span className="mono">{s.hole_size_in} in</span>
                  )}
                  <span className="cell-sub">
                    {s.hole_size_source === "unknown"
                      ? "no source gives it"
                      : `from the ${s.hole_size_source.replace(/_/g, " ")}`}
                  </span>
                </td>
                <td className="mono">
                  {s.start_date_local}
                  <span className="cell-sub">to {s.end_date_local}</span>
                </td>
                <td className="num mono">{metres(s.start_md_m)}</td>
                <td className="num mono">{metres(s.end_md_m)}</td>
                <td className="num mono">{metres(s.new_hole_drilled_m)}</td>
                <td>{s.operation_phase ?? "unknown"}</td>
                <td className="num">
                  {s.rate_m_per_h === null ? (
                    <span className="muted">none: {rateReason(s.rate_reason)}</span>
                  ) : (
                    <span className="mono">{s.rate_m_per_h.toFixed(2)}</span>
                  )}
                </td>
                <td className="num mono">
                  {s.casing_shoe_md_m === null ? "none" : metres(s.casing_shoe_md_m)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Flags({ detail }: { detail: WellDetail }) {
  if (detail.flags.length === 0) {
    return <p>No report of this wellbore is flagged.</p>;
  }
  return (
    <>
      <p>
        Flags mark doubtful reports. Nothing is corrected or removed from the warehouse; the chart
        and figures say where a flag changes what they show.
      </p>
      <ul className="flags">
        {detail.flags.map((f) => {
          const text = flagText(f.flag);
          return (
            <li key={f.flag}>
              <h3>
                {text.title}{" "}
                <span className="muted">
                  ({formatInteger(f.reports)} {f.reports === 1 ? "report" : "reports"},{" "}
                  <span className="mono">
                    {f.first_date === f.last_date
                      ? f.first_date
                      : `${f.first_date} to ${f.last_date}`}
                  </span>
                  )
                </span>
              </h3>
              <p>{text.meaning}</p>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function WellRuns({ name }: { name: string }) {
  const index = useBundle(RUNS_INDEX, isRunIndex);
  if (index.state === "loading") return <p aria-live="polite">Loading the runs…</p>;
  if (index.state === "error") {
    return <p role="alert">The runs could not be loaded ({index.error.message}).</p>;
  }
  const runs = index.data
    .filter((r) => r.wellbore_name === name)
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
  if (runs.length === 0) return <p>No agent has run on this well.</p>;
  const none = new Map<string, number | null>();
  return (
    <ul className="well-runs">
      {runs.map((r) => {
        const f = listFigures(r, none);
        const reason = failureReason(r);
        return (
          <li key={r.run_id}>
            <Link to={runPath(r.run_id)} className="mono">
              {r.run_id}
            </Link>{" "}
            <span className="muted">
              {r.system === null ? r.source : `${r.source} · ${systemOf(r)}`} ·{" "}
              {r.started_at.slice(0, 10)} ·{" "}
            </span>
            {reason === null ? (
              f.claims === null ? (
                "not checked"
              ) : (
                <>
                  {formatInteger(f.claims)} claims, accuracy {formatPercent(f.accuracy)}
                </>
              )
            ) : (
              <Badge tone="error">{reason}</Badge>
            )}
          </li>
        );
      })}
    </ul>
  );
}
