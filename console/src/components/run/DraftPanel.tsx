import { claimElementId, scopeText, segmentSentence } from "../../data/claims";
import type { Claim, ClaimResult, Draft, RunFile, Verdict } from "../../data/runTypes";
import { formatInteger, formatValue } from "../../format";

export type DraftView = "first" | "final" | "removed";

const GLYPHS: Record<Verdict, string> = {
  verified: "✓",
  contradicted: "✕",
  unsupported: "!",
  unverifiable: "?",
};

export function DraftPanel({
  run,
  available,
  checked,
  view,
  onView,
  selected,
  onSelect,
}: {
  run: RunFile;
  available: number; // drafts submitted by the replay position
  checked: number; // drafts checked by the replay position
  view: DraftView;
  onView: (view: DraftView) => void;
  selected: string | null;
  onSelect: (claimId: string) => void;
}) {
  if (run.drafts.length === 0) {
    return (
      <p className="note">
        This run produced no draft
        {run.error ? (
          <>
            : it ended with <span className="mono">{run.error}</span>.
          </>
        ) : (
          "."
        )}
      </p>
    );
  }
  if (available === 0) {
    return <p className="note">No draft yet at this step of the replay.</p>;
  }
  const hasFinal = run.drafts.length > 1;
  const index = view === "final" && hasFinal && available > 1 ? run.drafts.length - 1 : 0;
  const draft = run.drafts[index];
  const removed = run.removed_in_revision;

  return (
    <>
      <Legend />
      <div className="segmented" role="group" aria-label="Draft">
        <button
          type="button"
          aria-pressed={view === "first"}
          onClick={() => {
            onView("first");
          }}
        >
          First draft
        </button>
        {hasFinal && (
          <button
            type="button"
            aria-pressed={view === "final"}
            disabled={available < 2}
            onClick={() => {
              onView("final");
            }}
          >
            Final draft
          </button>
        )}
        {hasFinal && (
          <button
            type="button"
            aria-pressed={view === "removed"}
            disabled={available < 2}
            onClick={() => {
              onView("removed");
            }}
          >
            Removed during revision
          </button>
        )}
      </div>
      {view === "removed" && removed ? (
        <Removed claims={removed.claims} numbers={removed.numbers} />
      ) : (
        draft && (
          <DraftDocument
            draft={draft}
            first={index === 0}
            checked={index < checked}
            selected={selected}
            onSelect={onSelect}
          />
        )
      )}
    </>
  );
}

const MEANINGS: Record<Verdict, string> = {
  verified: "recomputed from the warehouse; it matches",
  contradicted: "recomputed; the warehouse gives another value",
  unsupported: "no evidence cited, or evidence that does not back it",
  unverifiable: "a metric or scope the checker cannot recompute",
};

// What each mark in the draft means, drawn as the marks themselves, each with its text label.
function Legend() {
  return (
    <div role="group" aria-label="Legend">
      <dl className="legend">
        {(Object.keys(MEANINGS) as Verdict[]).map((verdict) => (
          <div key={verdict}>
            <dt>
              <span className={`legend__mark claim--${verdict}`}>
                <span aria-hidden="true">{GLYPHS[verdict]}</span> {verdict}
              </span>
            </dt>
            <dd>{MEANINGS[verdict]}</dd>
          </div>
        ))}
        <div>
          <dt>
            <span className="legend__mark unclaimed">
              <span aria-hidden="true">!</span> unclaimed
            </span>
          </dt>
          <dd>dashed: a number in the text that carries no claim</dd>
        </div>
      </dl>
    </div>
  );
}

function DraftDocument({
  draft,
  first,
  checked,
  selected,
  onSelect,
}: {
  draft: Draft;
  first: boolean;
  checked: boolean;
  selected: string | null;
  onSelect: (claimId: string) => void;
}) {
  const results = new Map(
    checked && draft.check ? draft.check.results.map((r) => [r.claim_id, r]) : [],
  );
  const unclaimed = checked && draft.check ? draft.check.unclaimed : [];
  const s = checked ? draft.check?.summary : undefined;
  return (
    <article className="draft">
      <p className="note">
        {first ? "First draft: the scored one." : "Final draft, after the checker's findings."}{" "}
        {s ? (
          <>
            {formatInteger(s.verified ?? 0)} verified, {formatInteger(s.contradicted ?? 0)}{" "}
            contradicted, {formatInteger(s.unsupported ?? 0)} unsupported,{" "}
            {formatInteger(s.unverifiable ?? 0)} unverifiable,{" "}
            {formatInteger(s.unclaimed_number ?? 0)} unclaimed numbers.
          </>
        ) : (
          "Not checked yet at this step of the replay."
        )}
      </p>
      <h3 className="draft__title">{draft.document.title}</h3>
      {draft.document.sections.map((section, i) => (
        <section key={i}>
          <h4>{section.heading}</h4>
          <p>
            {section.sentences.map((sentence, j) => (
              <SentenceView
                key={j}
                text={sentence.text}
                claims={sentence.claims}
                unclaimed={unclaimed
                  .filter((u) => u.section === i && u.sentence === j)
                  .map((u) => u.text)}
                results={results}
                selected={selected}
                onSelect={onSelect}
              />
            ))}
          </p>
        </section>
      ))}
    </article>
  );
}

function SentenceView({
  text,
  claims,
  unclaimed,
  results,
  selected,
  onSelect,
}: {
  text: string;
  claims: Claim[];
  unclaimed: string[];
  results: Map<string, ClaimResult>;
  selected: string | null;
  onSelect: (claimId: string) => void;
}) {
  const { segments, unplaced } = segmentSentence(text, claims, unclaimed);
  return (
    <>
      {segments.map((seg, k) => {
        if (seg.kind === "text") return <span key={k}>{seg.text}</span>;
        if (seg.kind === "unclaimed") {
          return (
            <mark key={k} className="unclaimed">
              {seg.text}
              <span className="claim__label">
                <span aria-hidden="true">!</span> unclaimed
              </span>
            </mark>
          );
        }
        return (
          <ClaimButton
            key={k}
            claim={seg.claim}
            text={seg.text}
            result={results.get(seg.claim.id)}
            selected={selected === seg.claim.id}
            onSelect={onSelect}
          />
        );
      })}
      {unplaced.map((claim) => (
        <ClaimButton
          key={claim.id}
          claim={claim}
          text={formatValue(claim.value, claim.unit)}
          result={results.get(claim.id)}
          selected={selected === claim.id}
          onSelect={onSelect}
          chip
        />
      ))}{" "}
    </>
  );
}

function ClaimButton({
  claim,
  text,
  result,
  selected,
  onSelect,
  chip = false,
}: {
  claim: Claim;
  text: string;
  result: ClaimResult | undefined;
  selected: boolean;
  onSelect: (claimId: string) => void;
  chip?: boolean;
}) {
  const verdict = result?.verdict;
  return (
    <button
      type="button"
      id={claimElementId(claim.id)}
      className={`claim claim--${verdict ?? "unchecked"}${chip ? " claim--chip" : ""}`}
      aria-pressed={selected}
      onClick={() => {
        onSelect(claim.id);
      }}
    >
      {text}
      <span className="claim__label">
        {verdict ? (
          <>
            <span aria-hidden="true">{GLYPHS[verdict]}</span> {verdict}
          </>
        ) : (
          "not checked"
        )}
      </span>
    </button>
  );
}

function Removed({ claims, numbers }: { claims: Claim[]; numbers: string[] }) {
  return (
    <div className="removed">
      <p className="note">
        What the revision took out of the first draft. The first draft is the scored one, so these
        still count in its figures.
      </p>
      <h3>Claims removed ({formatInteger(claims.length)})</h3>
      {claims.length === 0 ? (
        <p>None.</p>
      ) : (
        <ul>
          {claims.map((c) => (
            <li key={c.id}>
              <span className="mono">{c.id}</span> {formatValue(c.value, c.unit)}{" "}
              <span className="muted">
                ({c.what.metric}
                {scopeText(c) && `; ${scopeText(c)}`})
              </span>
            </li>
          ))}
        </ul>
      )}
      <h3>Numbers removed ({formatInteger(numbers.length)})</h3>
      {numbers.length === 0 ? <p>None.</p> : <p className="mono">{numbers.join(", ")}</p>}
    </div>
  );
}
