import type { ReactNode } from "react";
import { Link } from "react-router";

import { Pipeline } from "../components/Pipeline";
import { Status } from "../components/Status";
import { HEADLINE_RELEASE, isRelease, primaryFigures, releasePath } from "../data/evaluation";
import {
  FEATURED_WELLBORE,
  RUN_VIEWER_READY,
  RUNS_INDEX,
  isRunIndex,
  latestCompletedRun,
  runPath,
} from "../data/runs";
import { useBundle } from "../data/useBundle";
import { countWord, formatInteger, formatPercent } from "../format";
import type { Figures } from "../data/evaluation";

export function Overview() {
  const loaded = useBundle(releasePath(HEADLINE_RELEASE), isRelease);
  return (
    <>
      <h1>Well Operations Agent Platform</h1>
      <section className="lead" aria-labelledby="result-heading">
        <h2 id="result-heading" className="eyebrow">
          Evaluation release <span className="mono">{HEADLINE_RELEASE}</span>
        </h2>
        {loaded.state === "loading" && <p aria-live="polite">Loading the release results…</p>}
        {loaded.state === "error" && (
          <p role="alert">The release results could not be loaded ({loaded.error.message}).</p>
        )}
        {loaded.state === "ready" && <Result figures={primaryFigures(loaded.data)} />}
      </section>

      <section aria-labelledby="what-heading">
        <h2 id="what-heading">What the platform does</h2>
        <p>
          Agents read offshore field data through read-only tools and write engineering documents,
          such as the end-of-well review of a wellbore. Every number an agent writes is a claim that
          names its metric, its scope and the warehouse rows it comes from. A deterministic checker
          recomputes each claim from the warehouse, without the model, and marks it verified,
          contradicted, unsupported or unverifiable. A person then reads the checked document and
          approves or rejects it; nothing leaves the platform unreviewed.
        </p>
      </section>

      <section aria-labelledby="pipeline-heading">
        <h2 id="pipeline-heading">How it fits together</h2>
        <Pipeline />
      </section>
    </>
  );
}

function Result({ figures }: { figures: Figures | null }) {
  if (figures === null) {
    return <p>This release has no scored runs of the primary system.</p>;
  }
  const wrong = figures.keyFactsWrong;
  return (
    <>
      <p className="statement">
        On {countWord(figures.wellbores)} wells the agent had never seen: about{" "}
        <span className="figure">{formatInteger(Math.round(figures.claimsPerReview))}</span> checked
        claims per review, <span className="figure">{formatInteger(figures.contradicted)}</span>{" "}
        contradicted in <span className="figure">{formatInteger(figures.claims)}</span>,{" "}
        {wrong === 0 ? (
          "no answer-key fact wrong"
        ) : (
          <>
            <span className="figure">{formatInteger(wrong)}</span> answer-key{" "}
            {wrong === 1 ? "fact" : "facts"} wrong
          </>
        )}
        , <span className="figure">{formatPercent(figures.coverage, 0)}</span> of key facts covered
        in the first draft.
      </p>
      <Actions />
      <dl className="rates">
        <Rate
          status={<Status kind="unsupported" />}
          value={formatPercent(figures.unsupportedRate)}
          detail="of claims cite no evidence that backs them"
        />
        <Rate
          status={<Status kind="unverifiable" />}
          value={formatPercent(figures.unverifiableRate)}
          detail="of claims the checker could not recompute"
        />
        <Rate
          status={<Status kind="flagged" label="Unclaimed" />}
          value={formatPercent(figures.unclaimedRate)}
          detail="of numbers in the text carry no claim"
        />
      </dl>
      <p className="note">
        First drafts of the primary system, {formatInteger(figures.runs)} runs on{" "}
        {countWord(figures.wellbores)} held-out wells; rates are the mean over runs. The evaluation
        page gives every metric, the baseline and the runs.
      </p>
    </>
  );
}

function Rate({ status, value, detail }: { status: ReactNode; value: string; detail: string }) {
  return (
    <div className="rate">
      <dt>{status}</dt>
      <dd>
        <span className="figure">{value}</span> {detail}
      </dd>
    </div>
  );
}

const WATCH = "Watch an agent review a well";

function Actions() {
  return (
    <div className="actions">
      {RUN_VIEWER_READY ? (
        <WatchLink />
      ) : (
        <button type="button" className="button button--primary" disabled>
          {WATCH}
          <span className="button__note">Coming next</span>
        </button>
      )}
      <Link to="/evaluation" className="button button--secondary">
        See the evaluation
      </Link>
    </div>
  );
}

// The latest completed review of the worked-example wellbore, in the run viewer.
function WatchLink() {
  const index = useBundle(RUNS_INDEX, isRunIndex);
  const run = index.state === "ready" ? latestCompletedRun(index.data) : null;
  if (run === null) {
    return (
      <button type="button" className="button button--primary" disabled>
        {WATCH}
        <span className="button__note">
          {index.state === "loading" ? "Loading" : `No completed run on ${FEATURED_WELLBORE}`}
        </span>
      </button>
    );
  }
  return (
    <Link to={runPath(run.run_id)} className="button button--primary">
      {WATCH}
    </Link>
  );
}
