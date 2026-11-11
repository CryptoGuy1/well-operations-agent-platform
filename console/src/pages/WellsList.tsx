import { useId } from "react";
import { Link } from "react-router";

import { Badge } from "../components/Badge";
import { useBundle } from "../data/useBundle";
import {
  WELLS_INDEX,
  flagText,
  isWellIndex,
  splitLabel,
  wellPath,
  wellRunsPath,
  type WellEntry,
} from "../data/wells";
import { formatInteger } from "../format";

export function WellsList() {
  const index = useBundle(WELLS_INDEX, isWellIndex);
  return (
    <div className="wells-page">
      <h1>Wells</h1>
      <p>
        Every Volve wellbore with daily drilling reports. Development wellbores and wellbores
        outside the evaluation population have a page with their drilling history. Held-out
        wellbores are listed by name only: they appear in the evaluation and its runs, and nowhere
        else.
      </p>
      {index.state === "loading" && <p aria-live="polite">Loading the wells…</p>}
      {index.state === "error" && (
        <p role="alert">The wells could not be loaded ({index.error.message}).</p>
      )}
      {index.state === "ready" && <WellsTable wells={index.data} />}
    </div>
  );
}

function WellsTable({ wells }: { wells: WellEntry[] }) {
  const id = useId();
  const count = (split: string) => wells.filter((w) => w.split === split).length;
  return (
    <>
      <p className="note">
        {formatInteger(wells.length)} wellbores: {formatInteger(count("development"))} development,{" "}
        {formatInteger(count("held_out"))} held out, {formatInteger(count("outside_population"))}{" "}
        outside the evaluation population.
      </p>
      <div className="table-scroll" tabIndex={0} role="region" aria-labelledby={`${id}-caption`}>
        <table className="data-table">
          <caption id={`${id}-caption`} className="visually-hidden">
            Wellbores, with their role in the evaluation split
          </caption>
          <thead>
            <tr>
              <th scope="col">Wellbore</th>
              <th scope="col">Role</th>
              <th scope="col">Report span</th>
              <th scope="col" className="num">
                Reports
              </th>
              <th scope="col" className="num">
                Campaigns
              </th>
              <th scope="col">Data-quality flags</th>
            </tr>
          </thead>
          <tbody>
            {[...wells].sort(byName).map((w) => (
              <Row key={w.key} well={w} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// 15/9-F-4 before 15/9-F-15.
const byName = (a: WellEntry, b: WellEntry) =>
  a.name.localeCompare(b.name, "en", { numeric: true }) || a.key.localeCompare(b.key);

function Row({ well }: { well: WellEntry }) {
  const role = (
    <td>
      <Badge
        tone={
          well.split === "held_out" ? "warning" : well.split === "development" ? "accent" : "muted"
        }
      >
        {splitLabel(well.split)}
      </Badge>
    </td>
  );
  if (!well.detail) {
    return (
      <tr>
        <th scope="row" className="mono">
          {well.name}
        </th>
        {role}
        <td colSpan={4} className="row-note">
          Held out for evaluation:{" "}
          <Link to={wellRunsPath(well.name)}>
            see its evaluation runs<span className="visually-hidden"> ({well.name})</span>
          </Link>
          .
        </td>
      </tr>
    );
  }
  const flags = Object.entries(well.flags ?? {});
  const total = flags.reduce((a, [, n]) => a + n, 0);
  return (
    <tr>
      <th scope="row">
        <Link to={wellPath(well)} className="mono">
          {well.name}
        </Link>
        <span className="cell-sub mono">{well.key}</span>
      </th>
      {role}
      <td>
        <span className="mono">
          {well.first_report_date} to {well.last_report_date}
        </span>
        <span className="cell-sub">
          {well.report_span_days == null
            ? "span unknown"
            : `${well.report_span_days.toLocaleString("en-GB")} days`}
          {well.active_days !== undefined && `, ${formatInteger(well.active_days)} active`}
        </span>
      </td>
      <td className="num mono">{formatInteger(well.report_count ?? 0)}</td>
      <td className="num mono">{formatInteger(well.campaigns ?? 0)}</td>
      <td className="cell-wrap">
        {total === 0 ? (
          "None"
        ) : (
          <>
            <span className="mono">{formatInteger(total)}</span> {total === 1 ? "flag" : "flags"}
            <span className="cell-sub">
              {flags.map(([f, n]) => `${flagText(f).title}: ${formatInteger(n)}`).join("; ")}
            </span>
          </>
        )}
      </td>
    </tr>
  );
}
