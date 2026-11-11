import { useState } from "react";

// Approval in the console is a demonstration (ADR 0005): the decision lives in this page's state
// only and is never saved or sent anywhere.

const DECISIONS = [
  { key: "approve", label: "Approve", done: "Approved" },
  { key: "changes", label: "Request changes", done: "Changes requested" },
  { key: "reject", label: "Reject", done: "Rejected" },
] as const;

type Decision = (typeof DECISIONS)[number]["key"];

export function Approval() {
  const [decision, setDecision] = useState<Decision | null>(null);
  const chosen = DECISIONS.find((d) => d.key === decision);
  return (
    <section className="approval" aria-labelledby="approval-heading">
      <h2 id="approval-heading" className="eyebrow">
        Reviewer decision
      </h2>
      <p className="approval__note">
        <strong>Demonstration: decisions are not saved.</strong>
      </p>
      <div className="approval__buttons" role="group" aria-label="Decision">
        {DECISIONS.map((d) => (
          <button
            key={d.key}
            type="button"
            className={`button button--${d.key === "approve" ? "primary" : "secondary"}`}
            aria-pressed={decision === d.key}
            onClick={() => {
              setDecision(decision === d.key ? null : d.key);
            }}
          >
            {d.label}
          </button>
        ))}
      </div>
      <p className="note" aria-live="polite">
        {chosen ? `${chosen.done} on this page only; reloading clears it.` : "No decision yet."}
      </p>
    </section>
  );
}
