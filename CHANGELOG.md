# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed

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
