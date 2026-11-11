// A run file (runs/<run_id>.json), as exported by well_ops.console_data.runs.

export type Scalar = string | number | boolean | null;

export type Verdict = "verified" | "contradicted" | "unsupported" | "unverifiable";

export interface Claim {
  id: string;
  type: string;
  value: string | number;
  unit: string | null;
  evidence_ids: string[];
  what: { metric: string } & Record<string, Scalar>;
}

export interface Sentence {
  text: string;
  claims: Claim[];
}

export interface Section {
  heading: string;
  sentences: Sentence[];
}

export interface Document {
  agent: string;
  title: string;
  sections: Section[];
}

export interface ClaimResult {
  claim_id: string;
  verdict: Verdict;
  reason: string;
  expected: string | number | null;
  detail: string | null;
}

export interface UnclaimedNumber {
  section: number;
  sentence: number;
  text: string;
}

export interface Check {
  results: ClaimResult[];
  unclaimed: UnclaimedNumber[];
  summary: Record<string, number>;
}

export interface Draft {
  seq: number;
  document: Document;
  check: Check | null;
}

export interface ModelCallStep {
  type: "model_call";
  seq: number;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_write_tokens: number | null;
  cache_read_tokens: number | null;
  stop_reason: string | null;
  cost_usd: number | null;
  latency_ms: number;
}

export interface ToolCallStep {
  type: "tool_call";
  seq: number;
  server: string;
  tool: string;
  arguments: Record<string, unknown>;
  is_error: boolean;
  error_code: string | null;
  matched: number | null;
  returned: number | null;
  capped: boolean | null;
  evidence_count: number;
  latency_ms: number;
}

export interface MarkerStep {
  type: "draft" | "check" | "approval";
  seq: number;
}

export type Step = ModelCallStep | ToolCallStep | MarkerStep;

export type EvidenceRow =
  | { status: "found"; relation: string; row: Record<string, unknown> }
  | { status: "not_found" | "not_a_single_row"; relation: string }
  | { status: "malformed" };

export interface RunFile {
  run_id: string;
  source: string;
  system: string | null;
  run: number | null;
  result_status: string | null;
  wellbore_key: string | null;
  wellbore_name: string | null;
  agent: string;
  model: string;
  prompt_path: string;
  prompt_sha256: string;
  started_at: string;
  status: string | null;
  error: string | null;
  cost_usd: number | null;
  elapsed_ms: number | null;
  model_calls: number | null;
  tool_calls: number | null;
  steps: Step[];
  drafts: Draft[];
  removed_in_revision: { claims: Claim[]; numbers: string[] } | null;
  evidence: Record<string, EvidenceRow>;
}

export function isRunFile(value: unknown): value is RunFile {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.run_id === "string" &&
    Array.isArray(v.steps) &&
    Array.isArray(v.drafts) &&
    typeof v.evidence === "object" &&
    v.evidence !== null
  );
}
