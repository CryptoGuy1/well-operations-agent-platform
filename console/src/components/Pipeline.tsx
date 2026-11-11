// The platform's pipeline, from the data to the reviewer, as an ordered list drawn as connected
// steps (left to right on wide screens, top to bottom on narrow ones).

const STEPS = [
  {
    name: "Data sources",
    detail: "Volve daily drilling reports, WITSML real-time data and production; Sodir FactPages",
  },
  { name: "Warehouse", detail: "Parsed, keyed and tested with dbt; doubtful records flagged" },
  { name: "Connectors", detail: "Read-only typed tools; personal data redacted" },
  { name: "Agent", detail: "Writes the review; every number is a claim citing its evidence" },
  {
    name: "Checker",
    detail: "Recomputes each claim from the warehouse, without the model",
    label: "deterministic",
  },
  { name: "Reviewer", detail: "A person approves or rejects the checked review" },
] as const;

export function Pipeline() {
  return (
    <figure className="pipeline">
      <ol className="pipeline__steps">
        {STEPS.map((step, i) => (
          <li
            key={step.name}
            className={"label" in step ? "pipeline__step pipeline__step--key" : "pipeline__step"}
          >
            <span className="pipeline__number mono" aria-hidden="true">
              {i + 1}
            </span>
            <span className="pipeline__name">
              {step.name}
              {"label" in step && <span className="pipeline__label">{step.label}</span>}
            </span>
            <span className="pipeline__detail">{step.detail}</span>
          </li>
        ))}
      </ol>
      <figcaption className="visually-hidden">
        The pipeline, in order: {STEPS.map((s) => s.name).join(", then ")}.
      </figcaption>
    </figure>
  );
}
