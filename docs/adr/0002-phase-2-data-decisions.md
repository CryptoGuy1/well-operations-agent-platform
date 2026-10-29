# 2. Phase 2 data decisions

Date: 2026-10-28

## Status

Accepted

## Context

The Phase 1 data audit (`docs/data/data-audit-report.md`) described the raw Volve, Sodir and CIRA
data and listed six decisions needed before the data platform is built. This record makes those
decisions, plus one more the audit implies: which wellbores are held out from development so that
agent evaluation is honest. Decisions made here must not be changed after evaluation results are
seen without a new ADR and an entry in `evaluation/CHANGELOG.md`.

## Decisions

### D1. Canonical wellbore key

- The key is the Sodir NPDID (`wlbNpdidWellbore`). The display name is the Sodir
  `wlbWellboreName`.
- Technical sidetracks share their parent's NPDID in Sodir and in the drilling reports. They are
  keyed as `<npdid>` for the parent and `<npdid>:T2` (or `:T3` and so on) for the sidetrack, with
  `is_technical_sidetrack = true` and a `parent_key` column. Affected in the audit: 15/9-F-11 T2
  (7078), 15/9-19 BT2 (3251), 15/9-19 ST2 (2043).
- Sources that carry an NPDID are matched on it. Other sources are matched by the normalised name
  rules already in `normalise_well_name`. Every source name, matched or not, is kept in a
  `wellbore_alias` table with its source and match method.

### D2. Names that are not wellbores

Kept, not dropped. They go into `wellbore_alias` with a status: `planning_object` (EDM relief
wells, casing-shoe and reservoir-intersection targets), `not_a_wellbore` (WITSML folders such as
`test`, `EcoScope_Customer_Run5`, `17 1/2" Final QAQCd Data`) or `unresolved` (for example WITSML
`15/9-F-15S`, EDM wells F-2, F-3, F-6, F-8, F-13). Nothing with these statuses reaches the agents.

### D3. Missing values

At ingestion, `-999.99` (drilling report status), the text `NULL` (workbook monthly sheet) and
blank cells (CIRA, workbook) all become a typed null. The original raw value is never written
back. A per-table data-quality summary records how many values were nulled and why.

### D4. Data-quality findings are flags, not fixes

Records the audit found doubtful are kept and flagged, never corrected or deleted:

- reports that end on or before the Sodir spud date of their wellbore (2 for 15/9-19 A, 1 for
  15/9-19 B, 10 for 15/9-19 S, 36 for 15/9-F-15, 1 for 15/9-F-15 C), flag `before_sodir_spud`.
  These may be legitimate (for example top-hole sections drilled before the date Sodir records)
  and must not be described as errors;
- the 9 reports with no activities, flag `no_activities`;
- the 24 reports whose activities leave a gap or overlap, flag `activity_gap_or_overlap`;
- status depths of `-999.99`, flag `depth_not_recorded`.

The console and the agents show these flags where they are relevant.

### D5. Time and depth conventions

- Activity timestamps are stored in UTC, with the original offset kept in a separate column.
- Depths are stored in metres as reported, labelled "measured depth, reference not stated" until
  open question 1 of the audit is resolved. `elevKelly` is stored but not applied.

### D6. WITSML scope in Phase 2

- All non-log WITSML objects (bhaRun, message, mudLog, rig, trajectory, tubular, wbGeometry,
  _wellboreInfo) are ingested for all wellbores. They total about 28 MB.
- Real-time `log` data (19.3 GB in the zip) is extracted on demand, one wellbore at a time, only for
  wellbores used in the demo or named in an evaluation question. The first is 15/9-F-11 T2.
  Extraction is recorded in `data/manifest.json`.

### D7. Lost-time definition

Lost time is measured in hours from activity durations, never in activity counts. Two tiers:

- **Lost time (primary, used in scored evaluation):** `interruption -- repair`,
  `interruption -- waiting on weather`, `interruption -- fish`, `interruption -- lost circulation`,
  `interruption -- well control`, `interruption -- wait`.
- **Possible lost time (reported separately, never added to the primary figure):**
  `interruption -- other`, `interruption -- maintain`, `interruption -- sidetrack`,
  `interruption -- rig up/down`, and the `wait` subcategory under `drilling`,
  `formation evaluation`, `plug abandon` and `workover`.

Reason for the second tier: the audit's example of `interruption -- sidetrack` describes planned
whipstock and milling work, and maintenance may be planned. Before the evaluation rules are frozen
(Phase 3 gate), a petroleum engineer reviews a random sample of 20 `comments` per second-tier code,
drawn only from development wellbores (D8), and may move a code to the first tier. Any move is
recorded as an amendment to this ADR before any scored run. This definition was set after seeing
activity counts per code only, not hours per wellbore or any agent output.

### D8. Held-out wellbores

- Evaluation population: 15/9-F wellbores with at least 20 drilling reports (17 wellbores in the
  audit).
- 15/9-F-11 T2 is always a development wellbore: it is the demo well and has already been examined
  in published work.
- Five wellbores are held out, drawn at random from the other 16 with Python's `random.Random`
  seeded with `20261028`, after this ADR is committed. The script and its output
  (`evaluation/splits.json`) are committed in their own commit. Held-out wellbores are not opened,
  plotted or used in prompt development until a scored release. Candidates are ordered by their D1
  key (NPDID as a number, then sidetrack suffix) and the draw is
  random.Random(20261028).sample(candidates, 5).
- The 15/9-19 wellbores (1990s appraisal wells) are ingested but are outside the evaluation
  population.

### D9. Production reference

No single source is treated as "true". Comparisons always state the basis of each side:
workbook per-wellbore volumes (allocated, sum-of-wells basis: matches Sodir gross within 1 % in
most months, see audit section 6), Sodir gross ("sum wellbores") and Sodir net
("saleable"; fuel and flare deducted, per Sodir's Green Book v1.1, section 2.1). The workbook
daily-sheet units are adopted as Sm3 only if daily volumes summed per month match the monthly
sheet; otherwise they stay unknown.

## Consequences

- The warehouse needs `wellbore`, `wellbore_alias` and data-quality flag tables from the start.
- Phase 2 needs about 30 MB of extra WITSML extraction instead of 19 GB.
- Lost-time figures are reproducible from codes and durations; the second tier keeps ambiguity
  visible instead of hiding it.
- Evaluation results on held-out wellbores can be trusted because those wellbores are fixed before
  any agent exists.
