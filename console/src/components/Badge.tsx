import type { ReactNode } from "react";

// A small label for states that are not claim statuses (run status, release, system).

export type Tone = "accent" | "warning" | "error" | "muted";

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`status status--${tone}`}>{children}</span>;
}
