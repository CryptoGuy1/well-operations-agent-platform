import { useId, useMemo, useState } from "react";
import { Link } from "react-router";

import { Badge } from "../components/Badge";
import { HEADLINE_RELEASE, isRelease, releasePath } from "../data/evaluation";
import {
  NO_FILTERS,
  RUNS_INDEX,
  applyFilters,
  coverageByRun,
  failureReason,
  filterOptions,
  isRunIndex,
  listFigures,
  promptVersion,
  runPath,
  systemOf,
  type RunFilters,
  type RunIndexEntry,
} from "../data/runs";
import { useBundle } from "../data/useBundle";
import { formatDuration, formatInteger, formatPercent } from "../format";

const FILTERS: { key: keyof RunFilters; label: string; all: string }[] = [
  { key: "wellbore", label: "Wellbore", all: "All wellbores" },
  { key: "system", label: "System", all: "All systems" },
  { key: "model", label: "Model", all: "All models" },
  { key: "release", label: "Release", all: "All releases" },
];

export function RunsList() {
  const index = useBundle(RUNS_INDEX, isRunIndex);
  const release = useBundle(releasePath(HEADLINE_RELEASE), isRelease);
  return (
    <div className="runs-page">
      <h1>Agent runs</h1>
      <p>
        Every recorded run: the development runs and the runs of evaluation release{" "}
        <span className="mono">{HEADLINE_RELEASE}</span>. Failed runs are listed with their reason.
        Figures are for the first draft; coverage of the answer key exists only for scored release
        runs.
      </p>
      {index.state === "loading" && <p aria-live="polite">Loading the runs…</p>}
      {index.state === "error" && (
        <p role="alert">The runs could not be loaded ({index.error.message}).</p>
      )}
      {index.state === "ready" && (
        <RunsTable
          index={index.data}
          coverage={coverageByRun(release.state === "ready" ? [release.data] : [])}
        />
      )}
    </div>
  );
}

function RunsTable({
  index,
  coverage,
}: {
  index: RunIndexEntry[];
  coverage: Map<string, number | null>;
}) {
  const [filters, setFilters] = useState<RunFilters>(NO_FILTERS);
  const options = useMemo(() => filterOptions(index), [index]);
  const shown = useMemo(() => {
    const runs = applyFilters(index, filters);
    // Release runs first, newest first within each source.
    return runs.sort(
      (a, b) => a.source.localeCompare(b.source) * -1 || b.started_at.localeCompare(a.started_at),
    );
  }, [index, filters]);
  const id = useId();

  return (
    <>
      <form
        className="filters"
        aria-label="Filter runs"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        {FILTERS.map((f) => (
          <div className="filters__field" key={f.key}>
            <label htmlFor={`${id}-${f.key}`}>{f.label}</label>
            <select
              id={`${id}-${f.key}`}
              value={filters[f.key]}
              onChange={(e) => {
                setFilters({ ...filters, [f.key]: e.target.value });
              }}
            >
              <option value="">{f.all}</option>
              {options[f.key].map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
        ))}
        <button
          type="button"
          className="button button--secondary"
          disabled={filters === NO_FILTERS}
          onClick={() => {
            setFilters(NO_FILTERS);
          }}
        >
          Clear filters
        </button>
      </form>
      <p className="note" aria-live="polite">
        Showing {formatInteger(shown.length)} of {formatInteger(index.length)} runs.
      </p>
      <div className="table-scroll" tabIndex={0} role="region" aria-labelledby={`${id}-caption`}>
        <table className="data-table">
          <caption id={`${id}-caption`} className="visually-hidden">
            Agent runs, with first-draft figures
          </caption>
          <thead>
            <tr>
              <th scope="col">Run</th>
              <th scope="col">Wellbore</th>
              <th scope="col">Status</th>
              <th scope="col" className="num">
                Claims
              </th>
              <th scope="col" className="num">
                Accuracy
              </th>
              <th scope="col" className="num">
                Unsupported
              </th>
              <th scope="col" className="num">
                Coverage
              </th>
              <th scope="col" className="num">
                Cost (USD)
              </th>
              <th scope="col" className="num">
                Latency
              </th>
              <th scope="col">Model and prompt</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <Row key={e.run_id} entry={e} coverage={coverage} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Row({ entry, coverage }: { entry: RunIndexEntry; coverage: Map<string, number | null> }) {
  const f = listFigures(entry, coverage);
  const reason = failureReason(entry);
  return (
    <tr>
      <th scope="row">
        <Link to={runPath(entry.run_id)} className="mono">
          {entry.run_id}
        </Link>
        <span className="cell-sub">
          <span className="mono">{entry.source}</span>
          {entry.system !== null && ` · ${systemOf(entry)}`}
          {entry.run !== null && ` · run ${entry.run}`}
        </span>
      </th>
      <td className="mono">{entry.wellbore_name ?? "unknown"}</td>
      <td>
        {reason === null ? (
          <Badge tone="accent">Completed</Badge>
        ) : (
          <>
            <Badge tone={entry.result_status === "rerun" ? "warning" : "error"}>
              {entry.result_status === "rerun" ? "Rerun" : "Failed"}
            </Badge>
            <span className="row-reason">{reason}</span>
          </>
        )}
      </td>
      <td className="num mono">{f.claims === null ? "–" : formatInteger(f.claims)}</td>
      <td className="num mono">{f.claims === null ? "–" : formatPercent(f.accuracy)}</td>
      <td className="num mono">{f.claims === null ? "–" : formatPercent(f.unsupportedRate)}</td>
      <td className="num mono">{f.coverage === null ? "–" : formatPercent(f.coverage)}</td>
      <td className="num mono">{entry.cost_usd === null ? "n/a" : entry.cost_usd.toFixed(4)}</td>
      <td className="num mono">{formatDuration(entry.elapsed_ms)}</td>
      <td>
        <span className="mono">{entry.model}</span>
        <span className="cell-sub">
          prompt <span className="mono">{promptVersion(entry.prompt_path)}</span>
        </span>
      </td>
    </tr>
  );
}
