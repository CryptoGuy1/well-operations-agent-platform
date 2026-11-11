import type { Claim, ClaimResult, EvidenceRow, Verdict } from "../../data/runTypes";
import { formatValue } from "../../format";
import { Status, type StatusKind } from "../Status";
import { claimElementId, scopeText } from "../../data/claims";

const STATUS: Record<Verdict, StatusKind> = {
  verified: "verified",
  contradicted: "contradicted",
  unsupported: "unsupported",
  unverifiable: "unverifiable",
};

export function EvidencePanel({
  claim,
  result,
  evidence,
}: {
  claim: Claim | null;
  result: ClaimResult | undefined;
  evidence: Record<string, EvidenceRow>;
}) {
  if (claim === null) {
    return (
      <p className="note">Select a claim in the draft to see its value, check and evidence.</p>
    );
  }
  return (
    <>
      <h3 className="evidence__title">
        Claim <span className="mono">{claim.id}</span>
      </h3>
      <dl className="facts">
        <div>
          <dt>Value</dt>
          <dd className="mono">{formatValue(claim.value, claim.unit)}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd className="mono">{claim.type}</dd>
        </div>
        <div>
          <dt>Metric</dt>
          <dd className="mono">{claim.what.metric}</dd>
        </div>
        <div>
          <dt>Scope</dt>
          <dd className="mono">{scopeText(claim) || "none"}</dd>
        </div>
        <div>
          <dt>Checker</dt>
          <dd>
            {result ? (
              <>
                <Status kind={STATUS[result.verdict]} />{" "}
                <span className="mono">{result.reason.replace(/_/g, " ")}</span>
                {result.detail && <span className="evidence__detail">{result.detail}</span>}
              </>
            ) : (
              "Not checked yet at this step of the replay."
            )}
          </dd>
        </div>
        <div>
          <dt>Recomputed</dt>
          <dd className="mono">
            {result && result.expected !== null ? formatValue(result.expected, claim.unit) : "n/a"}
          </dd>
        </div>
      </dl>
      <h3 className="evidence__subtitle">
        Cited evidence ({claim.evidence_ids.length === 0 ? "none" : claim.evidence_ids.length})
      </h3>
      {claim.evidence_ids.length === 0 && <p className="note">The claim cites no evidence id.</p>}
      {claim.evidence_ids.map((id) => (
        <EvidenceItem key={id} id={id} row={evidence[id]} />
      ))}
      <button
        type="button"
        className="button button--secondary evidence__back"
        onClick={() => {
          const el = document.getElementById(claimElementId(claim.id));
          el?.focus();
          el?.scrollIntoView({ block: "center" });
        }}
      >
        Back to the claim
      </button>
    </>
  );
}

function EvidenceItem({ id, row }: { id: string; row: EvidenceRow | undefined }) {
  return (
    <section className="evidence-row">
      <p className="evidence-row__id mono">{id}</p>
      {row === undefined && <p className="note">Not in the bundle.</p>}
      {row?.status === "malformed" && <p className="note">Not a valid evidence id.</p>}
      {row && row.status !== "malformed" && (
        <p className="evidence-row__relation mono">{row.relation}</p>
      )}
      {row?.status === "not_found" && <p className="note">No warehouse row has this id.</p>}
      {row?.status === "not_a_single_row" && (
        <p className="note">This id names several rows, so no single row is shown.</p>
      )}
      {row?.status === "found" && (
        <table className="evidence-row__table">
          <tbody>
            {Object.entries(row.row)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([k, v]) => (
                <tr key={k}>
                  <th scope="row" className="mono">
                    {k}
                  </th>
                  <td className="mono">
                    {v === null ? "null" : typeof v === "string" ? v : JSON.stringify(v)}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
