// A fictional run: fictional wellbore, numbers, rows and run ids.
import type { RunIndexEntry } from "../data/runs";
import type { Claim, RunFile } from "../data/runTypes";

function claim(
  id: string,
  type: string,
  value: string | number,
  unit: string | null,
  metric: string,
  ids: string[],
): Claim {
  return {
    id,
    type,
    value,
    unit,
    evidence_ids: ids,
    what: { metric, wellbore: "9001:T2", section: 1 },
  };
}

const A1 = "ddr:activity:R1#1";
const SECTION = "ddr:hole-section:9001:T2#1";

const FIRST = {
  agent: "post_well_review",
  title: "End-of-well review: XX/1-A-1 T2",
  sections: [
    {
      heading: "Lost time",
      sentences: [
        {
          text: "Section 1 lost 2.5 h, from 2020-01-02, and drilled 1,108.0 m in 12 days.",
          claims: [
            claim("c1", "hours", 2.5, "h", "lost_hours", [A1]),
            claim("c2", "date", "2020-01-02", null, "section_start_date", [SECTION]),
            claim("c3", "depth_m", 1108.0, "m", "new_hole_drilled", []),
          ],
        },
        {
          text: "The hole size was 26.0 in.",
          claims: [claim("c4", "hole_size_in", 17.5, "in", "section_hole_size", [SECTION])],
        },
        {
          text: "Wait on weather was the main cause.",
          claims: [claim("c5", "hours", 9.0, "h", "code_hours", ["ddr:activity:R9#9"])],
        },
      ],
    },
  ],
};

const FINAL = {
  ...FIRST,
  sections: [
    {
      heading: "Lost time",
      sentences: [FIRST.sections[0]!.sentences[0]!, FIRST.sections[0]!.sentences[1]!],
    },
  ],
};

export const RUN: RunFile = {
  run_id: "run-fixture-1",
  source: "development",
  system: null,
  run: null,
  result_status: null,
  wellbore_key: "9001:T2",
  wellbore_name: "XX/1-A-1 T2",
  agent: "post_well_review",
  model: "test-model",
  prompt_path: "prompts/post_well_review/v3.md",
  prompt_sha256: "ab".repeat(32),
  started_at: "2020-01-01T00:00:00+00:00",
  status: "completed",
  error: null,
  cost_usd: 0.0123,
  elapsed_ms: 65000,
  model_calls: 2,
  tool_calls: 1,
  steps: [
    {
      type: "model_call",
      seq: 1,
      input_tokens: 10,
      output_tokens: 20,
      cache_write_tokens: 100,
      cache_read_tokens: 0,
      stop_reason: "tool_use",
      cost_usd: 0.001,
      latency_ms: 900,
    },
    {
      type: "tool_call",
      seq: 2,
      server: "drilling_reports",
      tool: "lost_time",
      arguments: { wellbore: "XX/1-A-1 T2" },
      is_error: false,
      error_code: null,
      matched: 3,
      returned: 3,
      capped: false,
      evidence_count: 3,
      latency_ms: 40,
    },
    { type: "draft", seq: 3 },
    { type: "check", seq: 4 },
    {
      type: "model_call",
      seq: 5,
      input_tokens: 5,
      output_tokens: 30,
      cache_write_tokens: 0,
      cache_read_tokens: 100,
      stop_reason: "tool_use",
      cost_usd: 0.002,
      latency_ms: 1200,
    },
    { type: "draft", seq: 6 },
    { type: "check", seq: 7 },
  ],
  drafts: [
    {
      seq: 3,
      document: FIRST,
      check: {
        results: [
          { claim_id: "c1", verdict: "verified", reason: "exact", expected: 2.5, detail: null },
          {
            claim_id: "c2",
            verdict: "verified",
            reason: "exact",
            expected: "2020-01-02",
            detail: null,
          },
          {
            claim_id: "c3",
            verdict: "unsupported",
            reason: "no_evidence",
            expected: 1108.0,
            detail: null,
          },
          {
            claim_id: "c4",
            verdict: "contradicted",
            reason: "mismatch",
            expected: 26.0,
            detail: "stated 17.5, computed 26.0",
          },
          {
            claim_id: "c5",
            verdict: "unverifiable",
            reason: "evidence_not_found",
            expected: null,
            detail: null,
          },
        ],
        unclaimed: [{ section: 0, sentence: 0, text: "12" }],
        summary: {
          verified: 2,
          contradicted: 1,
          unsupported: 1,
          unverifiable: 1,
          unclaimed_number: 1,
        },
      },
    },
    {
      seq: 6,
      document: FINAL,
      check: {
        results: [
          { claim_id: "c1", verdict: "verified", reason: "exact", expected: 2.5, detail: null },
          {
            claim_id: "c2",
            verdict: "verified",
            reason: "exact",
            expected: "2020-01-02",
            detail: null,
          },
          {
            claim_id: "c3",
            verdict: "unsupported",
            reason: "no_evidence",
            expected: 1108.0,
            detail: null,
          },
          {
            claim_id: "c4",
            verdict: "contradicted",
            reason: "mismatch",
            expected: 26.0,
            detail: null,
          },
        ],
        unclaimed: [{ section: 0, sentence: 0, text: "12" }],
        summary: {
          verified: 2,
          contradicted: 1,
          unsupported: 1,
          unverifiable: 0,
          unclaimed_number: 1,
        },
      },
    },
  ],
  removed_in_revision: {
    claims: [claim("c5", "hours", 9.0, "h", "code_hours", ["ddr:activity:R9#9"])],
    numbers: ["9.0"],
  },
  evidence: {
    [A1]: {
      status: "found",
      relation: "staging.stg_ddr__activity",
      row: {
        comments: "Waited on weather. [redacted] on deck.",
        duration_hours: 2.5,
        report_file: "R1",
      },
    },
    [SECTION]: { status: "found", relation: "marts.dim_hole_section", row: { hole_size_in: 26.0 } },
    "ddr:activity:R9#9": { status: "not_found", relation: "staging.stg_ddr__activity" },
  },
};

export const FAILED_RUN: RunFile = {
  ...RUN,
  run_id: "run-fixture-failed",
  status: "failed",
  error: "TestTimeout",
  steps: RUN.steps.slice(0, 2),
  drafts: [],
  removed_in_revision: null,
  evidence: {},
};

function entry(run: RunFile, over: Partial<RunIndexEntry>): RunIndexEntry {
  return {
    run_id: run.run_id,
    file: `runs/${run.run_id}.json`,
    source: run.source,
    system: run.system,
    run: run.run,
    result_status: run.result_status,
    wellbore_key: run.wellbore_key,
    wellbore_name: run.wellbore_name,
    agent: run.agent,
    model: run.model,
    prompt_path: run.prompt_path,
    status: run.status,
    error: run.error,
    started_at: run.started_at,
    cost_usd: run.cost_usd,
    elapsed_ms: run.elapsed_ms,
    model_calls: run.model_calls,
    tool_calls: run.tool_calls,
    drafts: run.drafts.length,
    first_draft_summary: run.drafts[0]?.check?.summary ?? null,
    ...over,
  };
}

export const INDEX: RunIndexEntry[] = [
  entry(RUN, {}),
  entry(FAILED_RUN, {}),
  entry(RUN, {
    run_id: "run-fixture-r9",
    source: "r9",
    system: "primary",
    run: 1,
    result_status: "scored",
    wellbore_name: "XX/1-A-2",
    model: "other-model",
    started_at: "2020-02-01T00:00:00+00:00",
  }),
];
