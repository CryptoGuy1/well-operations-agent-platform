# 5. Console architecture

Date: 2026-11-10

## Status

Accepted

## Context

The platform has a tested DuckDB warehouse (ADR 0003), read-only connectors, the post-well review
agent with its claim checker and append-only run log (ADR 0004), and a first scored evaluation
release, r2 (`evaluation/results/r2/`). The two other agents planned for the platform are not
built yet; the console starts with what exists and grows as they are added.

The console is the public face of this work: a reader should be able to open a wellbore, see its
drilling history and data-quality flags, open an agent run, follow its tool calls, read its
drafts claim by claim with the evidence each claim cites, and see the evaluation results.

The constraints are:

- The warehouse cannot be built in CI: it is built from raw data that is downloaded by the user
  and never committed (ADR 0003).
- The public demo must hold no secrets and must not be able to spend money on model calls.
- Held-out wellbores (ADR 0002 D8) may appear in the evaluation and run views now that release r2
  is scored, and nowhere else: the well views show development wellbores and wellbores outside
  the evaluation population, and list held-out wellbores by name and split only. Held-out
  wellbores are still never used for prompt or checker development, examples or test fixtures.
- Every view must keep the data attributions of `NOTICE`.

## Decision

### A static single-page app

- The console is a static single-page app written in React and TypeScript and built with Vite, in
  `console/`. It is deployed to GitHub Pages by a GitHub Actions workflow.
- It makes no API calls and holds no secrets. Everything it shows comes from the data bundle.

### The data bundle

- All data comes from a committed bundle of small JSON files in `console/public/data/`, exported
  from the warehouse, the local run logs and the committed evaluation results by
  `make console-data` (`well_ops.console_data`).
- CI cannot build the warehouse, so the bundle is built locally and committed. CI only builds and
  deploys the front end.
- The export is deterministic: sorted keys and rows, and no timestamps other than recorded ones
  (the warehouse build time recorded by dbt, and the times in the run logs). Exporting twice from
  the same inputs gives the same bytes, so a bundle change in a diff is a data change.
- The files are:
  - `wells.json`: Volve wellbores with drilling reports, with key, name and split role; report
    span, campaigns and flag counts for every wellbore that is not held out.
  - `wells/<key>.json` (`:` in a key becomes `-`), not held-out wellbores only: hole sections, lost
    time by section, tier and cause, campaigns, one depth-against-time point per report (date,
    reported depth, deepest depth so far) and the data-quality flags.
  - `runs/index.json` and `runs/<run_id>.json`: every development run and every run of release r2,
    with its steps (model calls with tokens, cost and latency; tool calls with arguments and row
    counts, never the rows), first and final drafts with their check results, what the revision
    removed, cost, latency, model and prompt hash, and the warehouse row each cited evidence id
    names. A development run on a held-out wellbore is refused by the export.
  - `evaluation/r1.json` and `evaluation/r2.json`: each release's `summary.md` and run results.
  - `reconciliation.json`: the field's monthly production in the workbook and in Sodir's gross and
    net series, the basis of each, and the production attribution override.
  - `data_health.json`: aggregate row, null and flag counts, dbt test results, the warehouse build
    time and tool versions. The dbt results come from the copy `make dbt-build` writes beside the
    warehouse (`data/warehouse/dbt_run_results.json` and `dbt_manifest.json`), never from
    `warehouse/target/`, which every dbt command rewrites.
- Every string of every exported warehouse row, tool argument, draft and check result goes
  through the connectors' redactor (ADR 0004). The export then scans the whole bundle for emails, IP
  addresses, phone numbers and deny-listed names, prints the counts only, and fails if any is
  found.

### Precomputed runs; approval is a demonstration

- The runs shown are precomputed: the development runs and the runs of release r2.
- Approve and reject in the console are a demonstration only. The decision lives in the browser's
  state, is not persisted and is not written to any run log, and the interface says so on the
  control itself.
- This supersedes the plan in ADR 0003 for PostgreSQL application state in Phase 5 (amended there
  on the same date).

### Live runs stay local

- Running an agent remains a local-only feature (`make review`), with the provider key in the
  local `.env`. No live run, model call or provider key is part of the public build.

### Attribution

- Every page carries the data attributions from `NOTICE`: Equinor ASA and the Volve licence
  partners under the Equinor Open Data Licence, and the Norwegian Offshore Directorate's FactPages
  under NLOD 2.0. `NOTICE` records that the bundle distributes data derived from these sources.

## Alternatives considered

- **A hosted backend with live agent runs.** Readers could start a review and see it run. It was
  not chosen because it needs a server, a database and the warehouse in the cloud, a provider key
  on a public service, and limits against abuse and cost. A recorded run, with every tool call and
  every check result, shows the same behaviour reproducibly and at no cost per visit. Live runs
  stay available locally.
- **A dashboard framework (Streamlit).** It would reuse the Python code and give charts quickly.
  It was not chosen because it needs a running Python server for every visitor, so it cannot be
  served from GitHub Pages, and its page-rerun model fits the claim-by-claim reading of a run and
  its evidence less well than a single-page app with client-side routing.

## Consequences

- The public demo is a set of static files: free to host, nothing to patch, no secret to leak and
  no model spend.
- The bundle is a committed artefact. It must be re-exported and committed after a warehouse
  rebuild, a new run or a new release, and a reviewer sees every data change in the diff.
- The console shows what the bundle holds and nothing more; a question the bundle cannot answer
  needs a new export, not a query.
- Adds a Node toolchain (Vite, React, TypeScript) to the repository and a deploy workflow to CI.
  The Python CI job is unchanged.
- The repository now distributes derived data from Volve and Sodir, so `NOTICE` and the
  attribution on every page must be kept in step with the bundle.
