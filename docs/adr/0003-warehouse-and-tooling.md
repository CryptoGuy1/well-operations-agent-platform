# 3. Warehouse and tooling

Date: 2026-10-29

## Status

Accepted

## Context

Phase 2 builds the data platform: every raw source in `data/raw/` is parsed, checked and loaded
into one warehouse that later phases read through typed, read-only tools. ADR 0002 fixes what the
warehouse must contain (a canonical wellbore key, an alias table, typed nulls, data-quality flags,
UTC timestamps). This record fixes how it is built.

The constraints are:

- The data fits on one machine. ADR 0002 D6 keeps the 19.3 GB of WITSML `log` data out of
  Phase 2, and the remaining sources are already held locally under `data/raw/`.
- The Phase 2 gate is a one-command rebuild from `data/raw/`. A rebuild must be reproducible
  and must not depend on a running server.
- The raw formats (WITSML XML, Excel, CSV) need real parsing code; SQL alone cannot read them.
- Every model key needs automated tests, so that agents in Phase 3 never see a duplicated or
  orphaned wellbore.
- Analytical data and application state (audit log, approvals) have different needs and should not
  share a store by default.

## Decision

### Parsing and staging

- Parsers are Python modules in `src/well_ops/ingestion/`, one per source, as in the repository
  layout. They read `data/raw/` and write typed Parquet files to `data/staging/<source>/`.
- Parsing applies only the rules that cannot be expressed in SQL: decoding XML and Excel, turning
  the missing-value markers of ADR 0002 D3 into typed nulls, and normalising timestamps to UTC with
  the original offset kept (D5). Keys, matching and flags are left to the warehouse.
- Parquet carries the column types, so the warehouse never guesses types from text.

### Warehouse

- DuckDB is the warehouse, in one file at `data/warehouse/well_ops.duckdb`. Like everything
  under `data/`, it is never committed and is rebuilt from `data/raw/`.
- The warehouse is built by dbt with the `dbt-duckdb` adapter. The dbt project lives in
  `warehouse/`. `warehouse/profiles.yml` points at the DuckDB file through a path relative to the
  repository root, so dbt is always run from the root (`make dbt-build`), and no credentials or
  machine-specific paths are stored.
- Models follow the standard dbt layers and names:
  - `models/staging/`, `stg_<source>__<entity>`: one view per staging Parquet table, renaming and
    casting only.
  - `models/intermediate/`, `int_<entity>_<verb>`: matching, key assignment (ADR 0002 D1, D2) and
    data-quality flags (D4).
  - `models/marts/`, `dim_*` and `fct_*`: the tables the connectors read, for example
    `dim_wellbore`, `dim_wellbore_alias` and `fct_drilling_activity`. The exact list is settled
    when the models are written.
- Every model key has dbt tests: `unique` and `not_null` on primary keys, `relationships` on
  foreign keys, and `accepted_values` on coded columns such as flag and alias status values. A
  failing test fails the build.

### Orchestration

- In Phase 2 the Makefile is the orchestrator. `make rebuild` will run the parsers, then
  `dbt build`, from `data/raw/` to a tested warehouse. `make dbt-build` runs the dbt step alone.
- A scheduler, needed for the monthly Sodir refresh, is deferred to Phase 5 and will be chosen in
  its own ADR.

### Application state

- PostgreSQL is deferred to Phase 5, for application state only: the append-only audit log, run
  replay and approvals. It is not used for analytics. Its schema and the way it reads from the
  warehouse are decided in a Phase 5 ADR.

## Alternatives considered

- **PostgreSQL as the warehouse.** It would give one database for analytics and, later,
  application state. It was not chosen because it needs a running server for every rebuild, test
  and CI run, which makes the one-command rebuild heavier. Its row-oriented storage also brings
  no benefit to the analytical queries here (monthly sums, per-wellbore activity totals). Mixing
  analytical tables with an append-only audit log would also blur two different retention and
  access models.
- **Plain pandas (or Python) without dbt.** It has fewer dependencies, and the parsers are Python
  already. It was not chosen because the key tests, the lineage between layers and the
  documentation of each model would all have to be written and kept up by hand. dbt gives them
  in a standard form that reviewers already know. Transformations written in SQL are also easier
  to review than DataFrame chains.
- **Dagster now.** It offers asset lineage, scheduling and a UI. It was not chosen for Phase 2:
  the pipeline is a short, linear chain (parse, then build) run by hand. A scheduler only becomes
  necessary with the monthly Sodir refresh in Phase 5. Adding it now would bring a service and a
  second way of describing the pipeline before either is needed. It stays a candidate for the
  Phase 5 scheduler ADR.

## Consequences

- The whole platform rebuilds on one machine with no running services: `make rebuild` from
  `data/raw/` to `data/warehouse/well_ops.duckdb`.
- Adds `duckdb` and `dbt-duckdb` (which brings in `dbt-core`) as dependencies. The adapter and
  core versions are pinned in `uv.lock`.
- dbt-core is pinned to 1.x, the version the dbt-duckdb adapter supports. Moving to dbt v2 is a
  separate decision for a later ADR.
- dbt must run from the repository root; Makefile targets pass --project-dir and --profiles-dir so
  this is never left to the user.
- Model logic is split between Python (parsing) and SQL (keys, matching, flags). The boundary is
  the staging Parquet files, which can be inspected directly.
- DuckDB allows one writer at a time. That is enough for a rebuild-then-read workflow, but the
  connectors must open the warehouse read-only.
- Moving the warehouse to a server database later would mean changing the dbt adapter and
  reviewing DuckDB-specific SQL, but the layer structure and tests would carry over.
