import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { Badge } from "../components/Badge";
import { Approval } from "../components/run/Approval";
import { DraftPanel, type DraftView } from "../components/run/DraftPanel";
import { EvidencePanel } from "../components/run/EvidencePanel";
import { StepTrace } from "../components/run/StepTrace";
import { claimElementId } from "../data/claims";
import { failureReason, isRunId, promptVersion, systemOf } from "../data/runs";
import { isRunFile, type RunFile } from "../data/runTypes";
import { useBundle } from "../data/useBundle";
import { formatDuration, formatInteger, formatUsd } from "../format";

const NARROW = "(max-width: 69.99rem)"; // panels stacked

export function RunPage() {
  const { runId = "" } = useParams();
  if (!isRunId(runId)) {
    return <NotFound />;
  }
  return <LoadedRun runId={runId} />;
}

function NotFound() {
  return (
    <>
      <h1>Run not found</h1>
      <p>
        There is no such run in the data bundle. <Link to="/runs">See all runs</Link>.
      </p>
    </>
  );
}

function LoadedRun({ runId }: { runId: string }) {
  const loaded = useBundle(`runs/${runId}.json`, isRunFile);
  if (loaded.state === "loading") return <p aria-live="polite">Loading the run…</p>;
  if (loaded.state === "error") {
    return loaded.error.message.includes("HTTP 404") ? (
      <NotFound />
    ) : (
      <p role="alert">The run could not be loaded ({loaded.error.message}).</p>
    );
  }
  // Keyed by run, so moving to another run starts its replay afresh.
  return <RunView key={loaded.data.run_id} run={loaded.data} />;
}

function RunView({ run }: { run: RunFile }) {
  const [cursor, setCursor] = useState(Math.max(0, run.steps.length - 1));
  const [playing, setPlaying] = useState(false);
  const [view, setView] = useState<DraftView>("first");
  // The selected claim is in the address (?claim=c4), so a claim can be linked to.
  const [params, setParams] = useSearchParams();
  const selected = params.get("claim");

  // What the replay position has reached: drafts submitted, and drafts checked.
  const at = run.steps[cursor]?.seq ?? Number.POSITIVE_INFINITY;
  const available = run.drafts.filter((d) => d.seq <= at).length;
  const checked = run.steps.filter((s) => s.type === "check" && s.seq <= at).length;

  const draftIndex = view === "final" && available > 1 ? run.drafts.length - 1 : 0;
  const draft = run.drafts[draftIndex];
  const claim =
    draft?.document.sections
      .flatMap((s) => s.sentences.flatMap((t) => t.claims))
      .find((c) => c.id === selected) ?? null;
  const result =
    draftIndex < checked ? draft?.check?.results.find((r) => r.claim_id === selected) : undefined;

  const select = useCallback(
    (claimId: string) => {
      setParams({ claim: claimId }, { replace: true });
      if (window.matchMedia(NARROW).matches) {
        document.getElementById("evidence-heading")?.scrollIntoView({ block: "start" });
      }
    },
    [setParams],
  );

  // Arriving with a claim in the address, bring it into view once: inside the draft panel on wide
  // screens, the page itself when the panels are stacked. It waits for the web fonts: text set in
  // the fallback font reflows when they load and would move the claim out of view again.
  const arrived = useRef(selected);
  useEffect(() => {
    let live = true;
    const fonts = "fonts" in document ? document.fonts.ready : Promise.resolve();
    void fonts.then(() => {
      const id = arrived.current;
      if (!live || id === null) return;
      arrived.current = null;
      const el = document.getElementById(claimElementId(id));
      if (!el) return;
      const panel = el.closest(".panel");
      if (window.matchMedia(NARROW).matches || panel === null) {
        el.scrollIntoView({ block: "center" });
      } else {
        // Only if it is not already in the part of the panel on screen, then centred there; near
        // the end of the draft the panel cannot scroll that far, and the page moves the rest.
        const box = panel.getBoundingClientRect();
        const bottom = Math.min(box.bottom, window.innerHeight);
        const at = el.getBoundingClientRect();
        if (at.top < box.top || at.bottom > bottom) {
          panel.scrollTop += at.top - box.top - (bottom - box.top) / 2;
        }
        const now = el.getBoundingClientRect();
        if (now.top < 0 || now.bottom > window.innerHeight) el.scrollIntoView({ block: "center" });
      }
    });
    return () => {
      live = false;
    };
  }, []);

  const reason = failureReason(run);
  return (
    <div className="run-page">
      <p className="breadcrumb">
        <Link to="/runs">Agent runs</Link> /
      </p>
      <h1>
        Review of <span className="mono">{run.wellbore_name ?? "an unknown wellbore"}</span>
      </h1>
      <dl className="run-meta">
        <div>
          <dt>Run</dt>
          <dd className="mono">{run.run_id}</dd>
        </div>
        <div>
          <dt>Release</dt>
          <dd>
            <span className="mono">{run.source}</span>
            {run.system !== null && ` · ${systemOf(run)}`}
            {run.run !== null && ` · run ${run.run}`}
          </dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd className="mono">{run.model}</dd>
        </div>
        <div>
          <dt>Prompt</dt>
          <dd className="mono" title={run.prompt_sha256}>
            {promptVersion(run.prompt_path)} · {run.prompt_sha256.slice(0, 12)}
          </dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>
            {reason === null ? (
              <Badge tone="accent">Completed</Badge>
            ) : (
              <>
                <Badge tone={run.result_status === "rerun" ? "warning" : "error"}>
                  {run.result_status === "rerun" ? "Rerun" : "Failed"}
                </Badge>{" "}
                {reason}
              </>
            )}
          </dd>
        </div>
        <div>
          <dt>Cost</dt>
          <dd className="mono">{formatUsd(run.cost_usd)}</dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd className="mono">{formatDuration(run.elapsed_ms)}</dd>
        </div>
        <div>
          <dt>Calls</dt>
          <dd className="mono">
            {formatInteger(run.model_calls ?? 0)} model · {formatInteger(run.tool_calls ?? 0)} tool
          </dd>
        </div>
      </dl>

      <Approval />

      <div className="run-panels">
        <section className="panel panel--trace" aria-labelledby="trace-heading">
          <h2 id="trace-heading" className="panel__heading">
            Step trace
          </h2>
          <StepTrace
            steps={run.steps}
            drafts={run.drafts}
            cursor={cursor}
            onCursor={setCursor}
            playing={playing}
            onPlaying={setPlaying}
          />
        </section>
        <section className="panel panel--draft" aria-labelledby="draft-heading">
          <h2 id="draft-heading" className="panel__heading">
            The draft
          </h2>
          <DraftPanel
            run={run}
            available={run.steps.length ? available : run.drafts.length}
            checked={run.steps.length ? checked : run.drafts.length}
            view={view}
            onView={setView}
            selected={selected}
            onSelect={select}
          />
        </section>
        <section className="panel panel--evidence" aria-labelledby="evidence-heading">
          <h2 id="evidence-heading" className="panel__heading" tabIndex={-1}>
            Evidence
          </h2>
          <p className="visually-hidden" aria-live="polite">
            {claim ? `Claim ${claim.id} selected: ${result?.verdict ?? "not checked"}.` : ""}
          </p>
          <EvidencePanel claim={claim} result={result} evidence={run.evidence} />
        </section>
      </div>
    </div>
  );
}
