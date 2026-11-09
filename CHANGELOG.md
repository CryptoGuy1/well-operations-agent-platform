# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- ADR 0004 (agent architecture): one MCP server per source over the read-only warehouse, typed
  tools with evidence ids, held-out guard, redaction, plain tool-use loop, structured output,
  deterministic claim checker and append-only run log with replay. The published `sodir-mcp`
  package was reviewed and is not reused; the Sodir connector is written here.
- `well_ops.settings`: runtime configuration from `WELL_OPS_*` environment variables and `.env`.
- Empty `well_ops.connectors` and `well_ops.agents` packages; the MCP and model-provider SDKs and
  `pydantic-settings` dependencies.
- Connector building blocks: `well_ops.connectors.redaction` (emails, phone numbers, IP addresses
  and deny-listed names become `[redacted]`), `well_ops.connectors.evidence` (evidence id builders
  and parsers for every table a tool can return), `well_ops.connectors.guard` (held-out guard)
  and structured `ToolError`s.
- `make stage` also builds the private redaction deny-list (`data/private/`, never committed)
  from EDM user attributes, WITSML user names and the CIRA README emails; only its size is
  printed.
- `docs/architecture.md`: tool conventions (deterministic output, structured errors, read-only
  annotations, date meanings).
- Drilling-report MCP server (`well_ops.connectors.drilling_reports`, `make serve-ddr`) with
  seven read-only tools: `list_wellbores`, `well_overview`, `hole_sections`, `lost_time`,
  `activities`, `report` and `drilling_rate`. Every tool resolves wellbore names, applies the
  held-out guard, caps rows, redacts text and returns evidence ids; errors never echo the input.
- Production (`make serve-prod`), Sodir (`make serve-sodir`) and real-time (`make serve-rt`)
  MCP servers: `monthly_production`, `reconciliation`, `data_quality_flags`, `wellbore_facts`,
  `field_production`, `list_logs` and `curve_summary`, with the same guard, redaction, row caps
  and evidence ids. The Sodir server reads the warehouse copy of FactPages, never the internet.
- Production attribution (ADR 0002 D1 amendment of 2026-11-03): the
  `production_attribution_overrides` seed and the `int_production__monthly_attributed` and
  `int_production__daily_attributed` models keep the workbook's published NPDID and add
  `attributed_wellbore_key`, `attribution_source` ('npdid' or 'override') and
  `attribution_reason`. `int_production__monthly_flag` flags `attribution_override` and
  `production_before_completion`.
- Agent output contract (`well_ops.agents.schema`): documents of sections, sentences and typed
  claims (hours, depth_m, date, count, hole_size_in, rate_m_per_h, volume_sm3, code, quote), each
  with a unit, evidence ids and a metric with its scope.
- Claim checker (`well_ops.agents.checker`): recomputes each claim's metric from the warehouse,
  requires every cited evidence id to be a row the value rests on, and returns verified,
  contradicted, unsupported or unverifiable. Production claims are checked by attributed
  wellbore, with `prod:monthly` ids matched through their published NPDID. Draft tolerances and
  the metric list in `evaluation/RULES.md`.
- Run audit log (`well_ops.agents.audit_log`): append-only, hash-chained JSONL run records under
  `data/runs/`, a DuckDB loader (`make runs-db`) and replay from the log alone
  (`make replay RUN=<id>`, optionally re-checked against the current warehouse). Run cost is
  computed from logged tokens and the `WELL_OPS_PRICE_*` settings (prices and the date they
  were checked; no defaults); without them it stays unknown.
- `dim_hole_section.start_date_local` and `end_date_local`: the operations days (local dates)
  of each section's first and last reports, also returned by the `hole_sections` tool and
  checkable as `section_start_date` and `section_end_date`.
- Post-well review agent (`well_ops.agents.post_well_review`, prompt
  `prompts/post_well_review/v1.md`, `make review WELLBORE=<key>`): a tool-use loop on the
  Messages API over the four connector servers (`well_ops.agents.runtime`), with the step budget
  from settings. The agent submits a typed document; contradicted claims get one revision turn
  with the checker's findings (never the recomputed values), and what remains is shown in the
  rendered review. Every run writes its audit log.
- Settings: `effort` (sent only when set), cache-write and cache-read prices, and the provider
  API key (read as a secret, never logged); `max_tokens` defaults to 64000 (responses are
  streamed).
- `evaluation/RULES.md`: the first draft is scored; the final draft after checker feedback is
  reported separately and never used for headline metrics; baselines get no revision turn.
- `dim_hole_section.start_casing_shoe_md_m`, `casing_shoe_md_m` (casing set during the section,
  from report mdCsgLast) and `end_tvd_m`; `hole_sections` returns them. `well_overview` returns
  `duration_days`, `total_activity_hours`, lost hours and shares per tier and `deepest_tvd_m`;
  `lost_time` by section returns lost-time shares of the section's activity hours.
- Checker: claim types `days` and `percent`; metrics `activity_date`, casing shoe, tvd,
  `well_duration`, `total_activity_hours` and `lost_time_share`; the unclaimed-number check
  (numbers and dates in sentence text that no claim states), logged, rendered and counted with
  unsupported claims (`evaluation/RULES.md`).
- `prompts/post_well_review/v2.md` (v1 unchanged): casing summary, well duration, lost-time
  share, tvd, the Sodir completion date, and the new metrics. The agent uses v2.
- `dim_campaign`: drilling-report campaigns per wellbore (a gap of more than 30 days between
  reports starts a new one) with dates, span, active days and dominant operation phase;
  `ddr:campaign` evidence ids. `well_overview` returns `report_span_days` (was `duration_days`),
  `active_days` and the campaigns.
- Checker: metrics `report_span_days` (was `well_duration`), `active_days` and the campaign
  metrics; bare years covered by a date claim in that year; NPDIDs masked as identifiers; numbers
  covered by a quote claim's text, so casing sizes must be quoted from the reports.
- The revision turn is triggered by contradicted or unsupported claims or unclaimed numbers; the
  first draft stays the scored one.
- `prompts/post_well_review/v3.md` (v1 and v2 unchanged): campaigns, quote-backed casing sizes
  and exact evidence scoping. The agent uses v3.
- Run reports (`make review`, `make replay`) list what was removed during revision: the
  first-draft claims and numbers the final draft does not have (`well_ops.agents.revision`).
- `prompts/post_well_review/CHANGELOG.md`: prompt versions and their status.
- Checker: campaign numbers ("campaign 1") are identifiers, not unclaimed numbers.
- Two-tier model pricing: `WELL_OPS_PRICE_TIER_THRESHOLD_TOKENS` and the
  `WELL_OPS_PRICE_ABOVE_*` prices. A call whose prompt (input, cache-write and cache-read tokens)
  is above the threshold is priced at the upper tier; cost stays per model call.
- The revision findings ask the agent to back an unclaimed number with a claim (a date with
  `activity_date`, report text with a quote) and to remove it only if no tool row supports it.

### Removed

- `bit_size_evidence_in` from the `hole_sections` tool output (kept in the warehouse as
  evidence only).

- The `temperature` setting (ADR 0004 amendment of 2026-11-04): API version `2026-10-21`, which
  the SDK sends, rejects `temperature`, `top_p` and `top_k`. Reproducibility rests on a fixed
  model, a fixed prompt version and 3 runs per task.

### Changed

- Lost-time tiers (ADR 0002 D7 amendment of 2026-11-04, after the lost-time review):
  `interruption -- wait` moves from primary to possible; `interruption -- rig up/down` and
  `drilling -- wait` move from possible to primary. The `lost_time_codes` seed matches.

- Production for workbook NPDID 7078 ("NO 15/9-F-11 H") is attributed to 15/9-F-11 B (7080):
  15/9-F-11 is an observation well, plugged and abandoned in May 2013. Field totals are
  unchanged.
- `int_production__daily_flag`, `int_production__daily_units_check` and the production tools are
  keyed by the attributed wellbore and carry `published_npdid`; evidence ids still cite the
  published NPDID.

## [0.2.0-platform] - 2026-10-30

### Added

- ADR 0003 (warehouse and tooling) and the dbt project under `warehouse/` with the dbt-duckdb
  adapter; `make dbt-build` builds and tests `data/warehouse/well_ops.duckdb`.
- `make stage`: parses Sodir wellbores to `data/staging/sodir/wellbore.parquet` and every Volve
  source well name to `data/staging/identifiers/wellbore_alias.parquet`, with its D1 key and D2
  status (ADR 0002).
- dbt models `stg_sodir__wellbore`, `stg_identifiers__wellbore_alias`,
  `stg_evaluation__heldout_wellbore` and `dim_wellbore`, with key and relationship tests.
- Daily drilling reports staged to `data/staging/ddr/` (report, activity) with UTC timestamps
  and original offsets, and -999.99 as null with the nulled elements listed; dbt models
  `stg_ddr__report`, `stg_ddr__activity` and `int_ddr__report_flag` (D4 flags) with tests.
- Hole sections and lost time: dbt models `int_ddr__hole_section`, `int_ddr__activity_section`
  and `fct_lost_time`, and the `lost_time_codes` seed with the ADR 0002 D7 tiers. Each section
  records `hole_size_source` ('report' or 'unknown').
- `dim_hole_section`: each hole section with its `operation_phase`, activity hours,
  `new_hole_drilled_m` and `bit_size_evidence_in` (evidence only). WITSML bit size was evaluated
  and rejected as a hole-size source; see `docs/data/hole-size-bit-source-experiment.md`.
- Production staging (ADR 0002 D9): the Volve workbook daily and monthly sheets to
  `data/staging/production/`, and Sodir net and gross monthly field production (all fields) to
  `data/staging/sodir/`. dbt models `int_production__daily_units_check` (daily volume unit
  decision) and `fct_production_monthly_reconciliation` (workbook, Sodir gross and Sodir net per
  month, each with its basis), and `int_production__daily_flag` (`negative_volume`).
- `well_ops.keys`: the D1 wellbore key builder, shared by identifiers and production staging.
- WITSML staging (ADR 0002 D6): trajectory stations, BHA runs, tubular components, wellbore
  geometry sections, mud log intervals, rigs and messages for all wellbores to
  `data/staging/witsml/`, keyed through the alias table; personal fields are never read. dbt
  `stg_witsml__*` models convert angles to degrees and diameters to inches, with unit tests.
- `make extract-log WELLBORE=<key>`: extracts one wellbore's real-time logs from the zip to
  `data/raw/volve/witsml_logs/<key>/` and records them in the manifest; held-out wellbores are
  refused unless explicitly allowed. Log and curve summaries are staged to
  `data/staging/witsml_log/`, curve values to one Parquet file per log under
  `data/staging/witsml_log_values/<key>/` (dbt view `stg_witsml__log_value`), and
  `int_witsml__log_flag` flags logs outside the drilling-report period.
- `make rebuild`: deletes `data/staging/` and the warehouse, then stages every source and runs
  `dbt build`; fails on any test failure.
- `make quality`: computes `docs/data/data-quality-report.md` (row counts, nulls by column, values
  read as null, flag counts, daily unit check and dbt test results; aggregate only) with
  `well_ops.warehouse.quality`.
- `docs/architecture.md`: layers and data flow.
- CI compiles the dbt project without data (`make dbt-compile`).

### Changed

- ADR 0003 amended (2026-10-30): real-time log values are staged in Phase 2 for wellbores
  extracted on demand.
- Report helpers (`fill_report`, `table`) moved from the audit to `well_ops.markdown`; the audit
  report is unchanged.
- ADR 0002 amended (2026-10-30): D3 also treats -999.25, the WITSML null value, as missing.
- ADR 0002 amended: D4 uses two spud flags (`before_sodir_spud`, `before_report_spud`), and
  `depth_not_recorded` applies to the status `md` only.
- Name matching moved from the audit to `well_ops.ingestion.identifiers`; drilling report,
  production workbook and WITSML name readers moved to per-source modules. The audit report is
  unchanged.

## [0.1.0-data-audit] - 2026-10-28

### Added

- Repository scaffold: Python package `well_ops` (src layout, uv, Python 3.12), Makefile,
  CI running ruff, mypy and pytest, licence and data attribution files, and ADR 0001.
- `make download`: fetches the CIRA pump dataset from Zenodo (MD5-verified) and four Sodir
  FactPages tables (header-checked) into `data/raw/`, and writes `data/manifest.json`.
- `make download-volve`: resumable copy of the Volve drilling reports, WITSML data, production
  data, well picks, perforations, EDM file and licence terms from Databricks into
  `data/raw/volve/`, recorded in `data/manifest.json`. See `docs/data/volve-access.md`.
- Manifest entries now include a `source` field.
- `make audit`: Phase 1 data audit (`well_ops.ingestion.audit`) computed from `data/raw/` and
  written into `docs/data/data-audit-report.md`.
- Sodir `field_production_gross_monthly` (sum wellbores) download, and a three-way monthly
  comparison of workbook, Sodir gross and Sodir net production in the data audit.
