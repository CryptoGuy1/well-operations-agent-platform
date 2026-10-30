# 4. Agent architecture

Date: 2026-10-30

## Status

Accepted

## Context

Phase 2 built a tested DuckDB warehouse from the raw sources (ADR 0003), with the data decisions of
ADR 0002: canonical wellbore keys, typed nulls, flags instead of fixes, UTC timestamps, and five
held-out wellbores. Phase 3 adds the first agents. They read the warehouse through tools, write
engineering text, and a person approves the result.

The constraints are:

- Every number an agent states must be traceable to warehouse rows and checkable without trusting
  the model.
- Agents must not reach data they are not meant to see: held-out wellbores during development
  (ADR 0002 D8), and personal data in free-text fields.
- Runs must be reproducible enough to audit: which model, prompt, configuration and tool results
  produced a report, and the report must be re-renderable without calling the model again.
- The platform stays one-machine and server-free until Phase 5 (ADR 0003).

## Decision

### Connectors

- One MCP server per source: drilling reports, production, real-time (WITSML), and Sodir. Each
  lives in `src/well_ops/connectors/` and is built with the official MCP Python SDK.
- A server reads only the DuckDB warehouse (`data/warehouse/well_ops.duckdb`), opened in read-only
  mode. It never reads `data/raw/` or `data/staging/`, and never writes.

### Sodir connector: write our own

The published `sodir-mcp` package (version 0.1.0, MIT licence, the only release) was reviewed
from its source distribution before writing a Sodir connector. It exposes two read-only tools,
`wellbore_facts` and `field_production_monthly` (saleable, net volumes). Its code is careful:
typed inputs that are never echoed back, structured errors, row and size caps, a cache opened
read-only, and a download step that contacts only `factpages.sodir.no`.

It is not reused or forked, and the Sodir connector is written in this repository, because:

- It reads its own copy of the Sodir tables, downloaded by its `refresh` command into a SQLite
  cache in the user's cache folder (or, optionally, from another project's PostgreSQL tables).
  The answers could then differ from the warehouse that the claim checker verifies against.
- It has no row-level evidence ids. Its `source` object carries a query id and parameters, plus
  a trace id that is random on every call.
- It has no held-out guard: `wellbore_facts` answers for any wellbore.
- It has no redaction filter. It does flag instruction-like text and strips control characters.
- It does not know the D1 keys of technical sidetracks (`<npdid>:T<n>`), so 15/9-F-11 T2 cannot
  be resolved. It also does not serve gross production, which D9 compares with net.

A fork would replace the store, the name resolution, the outputs and the guards, which is most of
the package. Some of its ideas are adopted, and are written anew rather than copied: structured
errors without echoing the input, read-only tool annotations, and notes on what Sodir dates mean
(the completion date is the end of drilling, not production start-up). If any of its code is
copied later, its MIT notice is added to `NOTICE`.

### Tool rules

- Every tool has typed inputs (wellbore key or name, date range, depth range, code), validated
  before any query runs. Wellbore names are resolved to D1 keys through the alias table.
- There is no free-form SQL. Each tool runs a fixed, parameterised query.
- Results are capped at a configured number of rows (`tool_row_cap`). A capped result says that
  it was capped and how many rows matched.
- Every result row carries an evidence id: a stable id built from the row's natural key, for
  example `ddr:activity:<report_file>#<n>` or `prod:monthly:<npdid>:<yyyy-mm>`. The full id list
  is fixed with the connectors. Every result also states its source table and the query
  parameters used.

### Held-out guard

- Every tool refuses a held-out wellbore (`evaluation/splits.json`) unless the server was started
  in evaluation mode. The refusal is the same whether or not the wellbore has data.
- Evaluation mode is an environment flag (`WELL_OPS_EVALUATION_MODE`) set only by the evaluation
  harness. Development runs, prompt work and the console never set it, so they cannot see held-out
  wellbores.
- Per-wellbore results stay guarded: in development mode, a result that names or lists
  individual wellbores leaves held-out wellbores out.
- Field-level results (Sodir field production totals and the monthly production reconciliation)
  are allowed in development mode. Held-out wellbores are scored on drilling tasks, and
  field-level production reveals nothing about one wellbore's drilling.

### Redaction

- Every text field a tool returns passes a redaction filter before it leaves the server. The
  filter replaces email addresses, phone numbers, IP addresses, and names on a private deny-list
  of personal names. The deny-list is kept outside the repository; its path is configuration
  (`redaction_denylist_path`).
- The filter is deterministic and unit-tested. A run records how many values were redacted, never
  the redacted text.

### Agent runtime

- Each agent is a plain tool-use loop on the model provider's Messages API, through its official
  Python SDK. No agent framework is used. The loop sends the conversation and the tool
  definitions, runs the requested tool calls through MCP client sessions, and stops on a final
  answer or after the configured maximum number of steps.
- Model, temperature, maximum tokens and maximum steps come from configuration
  (`well_ops.settings`, environment variables with prefix `WELL_OPS_`), never from constants in
  agent code. The model has no default and must be set.
- Prompts live in `prompts/<agent>/v<N>.md`. A prompt file is never edited after a run has used
  it; a change is a new version. Each run records the prompt path and its SHA-256 hash.

### Output contract

- An agent returns structured JSON, not prose: sections, each a list of sentences, each sentence
  with its claims. A claim has a type, a value, a unit and the evidence ids it rests on. Every
  quantity, date or measurement in a sentence is a claim; identifiers (wellbore names, NPDIDs,
  activity codes, evidence ids) are not.
- The JSON is validated against a schema. It is rendered to Markdown only after the claim checker
  has run, and the rendering shows the result of each check.

### Claim checker

- The checker is deterministic code; no language model takes part.
- For each claim type (for example a duration total, a depth, a monthly volume, a date or a count)
  a checker function recomputes the value from the warehouse using the claim's evidence ids, and
  compares it with the stated value in the stated unit, within a tolerance fixed per type.
- A claim with an unknown type, a missing or unknown evidence id, or a mismatch fails. A failed
  claim is shown as failed; it is never silently dropped or corrected.

### Audit log and replay

- Each run writes an append-only JSONL file under `data/runs/`: configuration, prompt path and
  hash, code version, every model request and response, every tool call and result (with evidence
  ids), check results, approval decisions, and the end of the run. Lines are only ever appended.
- A DuckDB table is built from the JSONL files for querying runs; the files remain the record.
- Replay re-renders a run from its log, without calling the model. It can also re-run the claim
  checker against the current warehouse to show whether a past report still holds.
- PostgreSQL for application state stays deferred to Phase 5 (ADR 0003).

## Alternatives considered

- **An agent framework.** Frameworks offer ready-made loops, memory and tool wiring. They were not
  chosen because the loop needed here is short, and a framework would add its own abstractions
  between the code and the API calls that the audit log must record exactly. Framework upgrades
  would also change run behaviour outside the versioned prompts and configuration.
- **A language model as judge for checking.** A second model could grade claims and catch
  errors that a fixed checker cannot express. It was not chosen because the check must be
  reproducible and independent of the model being checked. A model judge can be wrong in the same
  way as the agent, and its verdicts change with model versions. Claims that cannot be checked
  deterministically are not allowed as claims.
- **Free-form SQL tools.** A single query tool would make agents more flexible and connectors
  smaller. It was not chosen because the held-out guard, row caps, redaction and evidence ids
  would then depend on what the agent writes, rather than being enforced in the tool code.

## Consequences

- Adds the official MCP Python SDK, the model provider's Python SDK and `pydantic-settings` as
  dependencies, pinned in `uv.lock`.
- Each new question type an agent can answer needs a tool, an evidence id format and, if it
  states numbers, a claim type with a checker. Agents are less flexible than with free SQL, and
  every number they state can be checked.
- The held-out guard depends on one environment flag. The evaluation harness must be the only
  code that sets it, and tests must cover both modes.
- Run logs contain tool results, which are redacted warehouse rows. They stay under `data/` and
  are never committed.
- Prompt versions and run logs make every report traceable to its model, prompt, configuration
  and data.
