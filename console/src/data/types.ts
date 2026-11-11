// Shapes of the data bundle (docs/adr/0005-console-architecture.md), as exported by
// well_ops.console_data. Only the fields the console reads are typed.

export interface Coverage {
  facts: number;
  covered: number;
  wrong: number;
  missing: number;
  rate: number | null;
}

export interface DraftScore {
  claims: number;
  verified: number;
  contradicted: number;
  unsupported: number;
  unverifiable: number;
  unclaimed: number;
  accuracy: number | null;
  unsupported_rate: number | null;
  unverifiable_rate: number | null;
  unclaimed_rate: number | null;
  coverage: Coverage;
}

export type RunStatus = "scored" | "task_failure" | "infrastructure_failure" | "budget_stopped";

export interface RunResult {
  run_id: string;
  system: string; // primary, baseline or secondary
  run: number;
  wellbore_key: string;
  wellbore_name: string;
  model: string;
  status: RunStatus;
  first_draft: DraftScore | null;
  final_draft: DraftScore | null;
  value_only: DraftScore | null;
  cost_usd: number | null;
  elapsed_ms: number | null;
}

export interface EvaluationRelease {
  release: string;
  summary_md: string | null;
  runs: RunResult[];
}
