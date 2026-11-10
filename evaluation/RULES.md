# Evaluation rules

Status: **frozen** with the tag `v0.3.0-rules` (2026-11-09), before any scored run. Any change
after the first scored run needs an entry in `evaluation/CHANGELOG.md` and a new release number.

These rules cover what is evaluated, how claims are checked, the answer key, the metrics, the
baseline, the secondary model, failures and the budget. The harness (`well_ops.evaluation`,
`make evaluate RELEASE=r<n>`) implements them and refuses settings that differ.

## Evaluated system and scored set

- **Primary system**: the post-well review agent with prompt
  `prompts/post_well_review/v3.md`, model `claude-haiku-5-5` at default effort (no effort
  sent), `max_tokens` 128000 (64000 in release r1), `max_steps` 20 and `tool_row_cap` 200,
  on a committed code version (a working tree with changes is refused).
- **Scored set**: the 5 held-out wellbores of `evaluation/splits.json`, only. Development
  wellbores are never scored, and nothing is tuned on held-out wellbores.
- **Runs**: 3 runs per wellbore and system, run 1 on every wellbore before run 2. Each run is
  one full review of one wellbore; it is scored on its own claims, with no separate targeted
  questions.
- The first draft is scored. The final draft is reported separately as "after checker
  feedback" (see Scored draft).

## Claims

An agent returns a document of sections, sentences and claims (`well_ops.agents.schema`). Every
quantity, date, measurement, activity code or quotation in a sentence is a claim. Identifiers
(wellbore names, NPDIDs, evidence ids) are not claims.

A claim has an id, a type, a value, a unit fixed by its type, the evidence ids it rests on, and a
`what`: the metric it states and the metric's scope, for example
`{"metric": "lost_hours", "wellbore": "15/9-F-11 T2", "section": 2, "tier": "primary"}`.

## Results

The claim checker (`well_ops.agents.checker`) is deterministic code. It gives every claim one
result:

| Result | Meaning |
|---|---|
| verified | The recomputed value matches within the tolerance, and every cited evidence id is a row the value rests on. |
| contradicted | The evidence is valid but the value does not match, the warehouse holds no value for the metric, a quotation is not in the cited text, or a cited production month is attributed to another wellbore. |
| unsupported | No evidence, a malformed or unknown evidence id, evidence that is not a row the value rests on, or a wellbore that cannot be resolved or is held out in development mode. |
| unverifiable | An unknown metric, a metric that does not fit the claim type, or a scope the checker cannot read (a missing or unknown scope key). |

A failed claim is shown as failed; it is never dropped or corrected.

The checks run in this order, and the first failure decides the result: metric and type, scope,
evidence present, every evidence id parsed and found (and not of a held-out wellbore in
development mode), the metric recomputed, every cited id among the rows the value rests on, and
the value compared.

## Tolerances

A number matches when |stated − recomputed| ≤ absolute + relative × |recomputed|. Dates, codes
and quotations must match exactly.

Date claims are local dates, from the source timestamp's original offset. A drilling report's
date is its operations day, the local date of its start; a hole section's start and end dates are
the operations days of its first and last reports.

| Claim type | Unit | Absolute | Relative |
|---|---|---|---|
| hours | h | 0.25 | 0 |
| depth_m | m | 1 | 0 |
| rate_m_per_h | m/h | 0 | 0.02 |
| hole_size_in | in | 0.01 | 0 |
| volume_sm3 | Sm3 | 0 | 0.005 |
| days | d | 0.05 | 0 |
| percent | % | 0.1 | 0 |
| count | | 0 | 0 |

The volume tolerance of 0.5 % admits a volume stated to three significant figures. A percent
claim's tolerance is in percentage points.

## Evidence

- Every claim cites at least one evidence id, and every cited id must name a row the recomputed
  value rests on. Citing a correct but unrelated row makes the claim unsupported.
- A metric scoped to a hole section also accepts the section's `ddr:hole-section` id. A metric
  scoped to a wellbore accepts `well:wellbore` where the matching tool returns it.
- `rt:log-value` ids cannot be cited: index values repeat within a log, so the id names no single
  row.

## Unclaimed numbers

Every number and date in a sentence's text must be stated by a claim of that sentence. A number
is covered when a claim's value, rounded to the precision written, equals it; a date when a date
claim has the same value; a month (`yyyy-mm`) when a claim's scope names it; a bare year when a
date claim of the sentence is in that year; and any number when it appears in the text of a
quote claim of the sentence, which the checker verifies against the cited row. Casing sizes are
numbers, not identifiers: a casing size must be backed by a quote claim from the report text
that states it. Identifiers are not numbers: digits inside wellbore names and codes
(`15/9-F-11 T2`), section numbers ("section 2", "sections 1, 2 and 4"), campaign numbers
("campaign 1", "campaigns 2 and 3"), NPDIDs ("Sodir wellbore 5794", "NPDID 5794") and evidence
ids in backticks. Every other number is flagged as
`unclaimed_number`. Unclaimed numbers are reported as their own rate (see Metrics reported).

## Real-time curve statistics

Real-time curve statistics (count, minimum, maximum and mean from `curve_summary`) are not
checkable: no metric recomputes them, so a claim stating one is unverifiable.

## Production attribution

A wellbore's production is recomputed by `attributed_wellbore_key` (ADR 0002 D1, amendment of
2026-11-03). A cited `prod:monthly:<npdid>:<yyyy-mm>` id is matched through the published NPDID
it contains. A cited month that the workbook attributes to another wellbore contradicts the
claim.

## Metrics

Scope keys in brackets are optional. `section` is the hole-section number (section 0 holds the
activities before the first stated hole section; its evidence id ends in
`#before_first_section`), `campaign` the
campaign number (a gap of more than 30 days between reports starts a new campaign), `tier` is `primary`
or `possible`, `code` is `category -- subcategory`, months are `yyyy-mm`, and a volume metric
takes either `month` or `start` and `end` (inclusive).

| Metric | Claim type | Scope | Recomputed from |
|---|---|---|---|
| lost_hours | hours | wellbore, tier, [section], [code] | `fct_lost_time` hours |
| lost_time_activities | count | wellbore, tier, [section], [code] | `fct_lost_time` activities |
| code_hours | hours | wellbore, code, [section] | `fct_lost_time` hours, any tier |
| section_activity_hours | hours | wellbore, section | `dim_hole_section.activity_hours` |
| section_interruption_hours | hours | wellbore, section | `dim_hole_section.interruption_hours` |
| total_activity_hours | hours | wellbore | all activity hours (sum over hole sections) |
| lost_time_share | percent | wellbore, tier, [section] | lost hours of the tier over the activity hours of the wellbore or section, × 100 |
| activity_duration | hours | [wellbore] | the cited activities' durations, summed |
| activity_date | date | [wellbore] | local start date of the cited activities |
| section_start_md | depth_m | wellbore, section | `dim_hole_section.start_md_m` |
| section_end_md | depth_m | wellbore, section | `dim_hole_section.end_md_m` |
| new_hole_drilled | depth_m | wellbore, section | `dim_hole_section.new_hole_drilled_m` |
| section_start_casing_shoe_md | depth_m | wellbore, section | `dim_hole_section.start_casing_shoe_md_m`: deepest casing shoe when the section starts |
| section_casing_shoe_md | depth_m | wellbore, section | `dim_hole_section.casing_shoe_md_m`: shoe of casing set during the section |
| section_end_tvd | depth_m | wellbore, section | `dim_hole_section.end_tvd_m`: tvd on the section's deepest-md report |
| report_md | depth_m | wellbore, date | measured depth on that operations day's report |
| deepest_md | depth_m | wellbore | the deepest reported measured depth |
| deepest_tvd | depth_m | wellbore | tvd on the deepest-md report |
| report_tvd | depth_m | wellbore, date | tvd on that operations day's report |
| total_depth | depth_m | wellbore | Sodir total depth (a technical sidetrack takes its parent's) |
| section_start_date | date | wellbore, section | operations day of the section's first report |
| section_end_date | date | wellbore, section | operations day of the section's last report |
| first_report_date | date | wellbore | first report operations day |
| last_report_date | date | wellbore | last report operations day |
| first_unflagged_report_date | date | wellbore | first report day without a before-spud flag |
| entry_date | date | wellbore | Sodir entry date (parent's for a technical sidetrack) |
| completion_date | date | wellbore | Sodir completion date (parent's for a technical sidetrack) |
| report_count | count | wellbore | daily drilling reports |
| flagged_report_count | count | wellbore | reports with a before-spud flag |
| report_span_days | days | wellbore | from the start of the first report without a before-spud flag to the end of the last report, in days of 24 h |
| active_days | count | wellbore | operations days with a report without a before-spud flag |
| campaign_count | count | wellbore | campaigns in `dim_campaign` |
| campaign_start_date | date | wellbore, campaign | `dim_campaign.start_date_local` |
| campaign_end_date | date | wellbore, campaign | `dim_campaign.end_date_local` |
| campaign_days | days | wellbore, campaign | `dim_campaign.span_days` |
| campaign_active_days | count | wellbore, campaign | `dim_campaign.active_days` |
| campaign_operation_phase | code | wellbore, campaign | `dim_campaign.operation_phase` |
| section_report_count | count | wellbore, section | `dim_hole_section.report_count` |
| section_hole_size | hole_size_in | wellbore, section | `dim_hole_section.hole_size_in` |
| section_drilling_rate | rate_m_per_h | wellbore, section | new hole over hours coded drilling -- drill |
| wellbore_volume | volume_sm3 | wellbore, fluid, month or start and end | workbook monthly sheet by attributed wellbore; fluid `oil`, `gas`, `water`, `gas_injected` or `water_injected` |
| field_volume | volume_sm3 | field, fluid, basis, month or start and end | `fct_production_monthly_reconciliation`; field `VOLVE`, fluid `oil`, `gas` or `water`, basis `workbook`, `sodir_gross` or `sodir_net` |
| activity_code | code | [wellbore] | the cited activities' codes |
| quote | quote | [wellbore] | exact substring of a text field of a cited row, after redaction |

## Scored draft

An agent run can hold two drafts: the first one the agent submits, and a final one revised after
the checker's findings. The first draft is scored. The final draft is reported separately,
labelled as the final draft after checker feedback, and never used for headline metrics,
because the checker that drives the revision is the same checker that scores. Baselines get no
revision turn. The revision turn is given when the first draft has a contradicted or unsupported
claim or an unclaimed number; unverifiable claims alone do not trigger it.

The revision findings give claim ids, results and reasons, never recomputed values. They tell
the agent to back each unclaimed number with a claim rather than remove it: a date with an
`activity_date` claim, a number from a report's text with a quote claim, any other number with
the metric that gives it. A number is to be removed only if no tool row supports it.

Every run report lists, next to the final-draft results, what was removed during revision: the
claims of the first draft that the final draft does not have (matched by type, value and
`what`, so a claim kept with corrected evidence or another id is not removed) and the numbers
and dates of the first draft's text, as written and identifiers excluded, that the final
draft's text does not have (counted over the whole document). This is reported, not scored;
first-draft scoring is unchanged.

A claim whose value changed in revision counts as removed (its first-draft value is gone).

A run with no checked first draft (the step budget ran out, the output never fitted the
contract, or the model refused) is a task failure (see Failures).

## Value-only checking

The baseline is checked on values only: the evidence requirement is waived. A claim's metric is
recomputed from its scope, and its value compared with the same tolerances; its cited evidence
ids, if any, are ignored. Metrics defined by the cited rows (`activity_duration`,
`activity_date`, `activity_code` and `quote`) cannot be recomputed without evidence and keep the
full check. The primary system's first draft is also reported value-only, for comparison.

## Answer key

The answer key (`well_ops.evaluation.answer_key`, `make answer-key`) is computed from the
warehouse by code, with the checker's own metric code, for every wellbore of the evaluation
population. It holds held-out facts: the key file is kept out of the repository and never
printed. Its SHA-256 and the commit it was built from are committed in
`evaluation/answers/answer_key.sha256`. The harness rebuilds the key from the warehouse and
refuses to run if the rebuilt key's SHA-256 differs from the committed one, and every summary
gives that SHA-256 and commit. Per wellbore, the key facts are:

| Fact | Metric and scope |
|---|---|
| Report date range | `first_report_date`, `last_report_date` |
| Campaign count and dates | `campaign_count`; `campaign_start_date`, `campaign_end_date` per campaign |
| Section count | the number of hole sections (see below) |
| Per hole section: depth range, hole size, new hole, drilling rate | `section_start_md`, `section_end_md`, `section_hole_size`, `new_hole_drilled`, `section_drilling_rate` |
| Per hole section: primary and possible lost hours | `lost_hours` with `tier` and `section` |
| Largest primary cause and its hours | `lost_hours` with `tier` primary and the `code` with the most primary hours (ties: the first code alphabetically) |
| Total primary and possible lost hours | `lost_hours` with `tier` only |

Section 0 (activities before the first stated hole section) is not a hole section: it gives no
facts and is not counted. A fact whose value is unknown (null in the warehouse) or zero is left
out of the key; both are counted in the key file.

A key fact is **covered** by a verified claim of the same metric and scope (the claim's
wellbore resolved to its key), **wrong** when such a claim is contradicted and none is verified,
and **missing** otherwise. The section count has no metric in prompt v3: it is covered when
every hole section has a verified claim scoped to it and no claim names a section the wellbore
does not have, and wrong when a claim names such a section. Answer-key coverage is covered key
facts / key facts.

## Metrics reported

Every scored result reports all of these together; claim accuracy is never reported alone.

| Metric | Definition |
|---|---|
| Claim accuracy | verified / (verified + contradicted) |
| Unsupported rate | unsupported claims / claims |
| Unverifiable rate | unverifiable claims / claims |
| Unclaimed-number rate | unclaimed numbers / (claims + unclaimed numbers) |
| Answer-key coverage | covered key facts / key facts, with the count of wrong key facts |
| Removed during revision | claims and numbers of the first draft absent from the final draft |
| Cost and latency | USD from the logged tokens and the configured prices; elapsed seconds per run |

Each metric is reported per wellbore as the mean and the minimum to maximum over its 3 runs,
and over all runs of the system. A metric a run cannot define (accuracy with no verified or
contradicted claim, for example) is left out of that mean, and the number of runs behind the
value is shown. A task failure counts as zero answer-key coverage.

## Baseline

The baseline is the same model with no data tools, given only the wellbore name and the output
contract (`prompts/post_well_review_baseline/v1.md`); it hands in its document through
`submit_review`, the only tool it has, and gets no revision turn. It is scored on value only
(see Value-only checking), with the same answer key, 3 runs per held-out wellbore.

## Secondary model

If the primary system and the baseline finish within the budget, the primary system is run once
per held-out wellbore with `claude-sonnet-5-5` (same prompt and settings; its prices are the
`WELL_OPS_SECONDARY_*` settings). It is reported separately and never pooled with the primary
results.

## Failures

- **Infrastructure errors** (provider credit, network, rate limit, provider 5xx) may be rerun,
  at most twice per run; every attempt has its own run log and is listed in the summary.
- **Agent failures** (the step budget runs out, the output never fits the contract, or the model
  refuses) without a checked first draft are task failures: counted, never rerun.
- Any other error stops the harness.

## Budget

The release has a hard cap of USD 8 for every model call of the primary system, the baseline
and the secondary model, earlier attempts of the same release included. Before each call the
harness counts the request's prompt tokens and bounds its cost (the prompt plus 10 % at the
highest input-side price of either price tier, plus the whole `max_tokens` at the highest
output price); if the spend so far plus that bound would exceed the cap, the call is not made,
the release stops and the summary reports what ran. Prices must be set; otherwise the release is
refused.

## Releases

A release (`r1`, `r2`, ...) is run once and writes `evaluation/results/<release>/`: one JSON file
per run and `summary.md`. Any change after the first scored run, to these rules, the prompts,
the settings, the answer key or the code that scores, needs an entry in
`evaluation/CHANGELOG.md` and a new release number.

## Held-out wellbores

Outside evaluation mode, a claim about a held-out wellbore, or one citing a held-out wellbore's
row, is unsupported (ADR 0002 D8).
