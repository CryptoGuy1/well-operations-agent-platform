// The status language used everywhere. Colour is never the only signal: every status carries its
// text label and a glyph.

export type StatusKind = "verified" | "unsupported" | "flagged" | "contradicted" | "unverifiable";

const STATUSES: Record<StatusKind, { label: string; tone: string; glyph: string }> = {
  verified: { label: "Verified", tone: "accent", glyph: "✓" },
  unsupported: { label: "Unsupported", tone: "warning", glyph: "!" },
  flagged: { label: "Flagged", tone: "warning", glyph: "!" },
  contradicted: { label: "Contradicted", tone: "error", glyph: "✕" },
  unverifiable: { label: "Unverifiable", tone: "muted", glyph: "?" },
};

export function Status({ kind, label }: { kind: StatusKind; label?: string }) {
  const status = STATUSES[kind];
  return (
    <span className={`status status--${status.tone}`} data-status={kind}>
      <span className="status__glyph" aria-hidden="true">
        {status.glyph}
      </span>
      {label ?? status.label}
    </span>
  );
}
