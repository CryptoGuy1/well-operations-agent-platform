# Evaluation rules

Status: **draft**. These rules are frozen, with the tag `v0.3.0-rules`, before any scored run.
After the freeze, every change is dated and disclosed in `evaluation/CHANGELOG.md`.

This draft covers claim checking (ADR 0004). Scoring is added before the freeze.

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
| count | | 0 | 0 |

The volume tolerance of 0.5 % admits a volume stated to three significant figures.

## Evidence

- Every claim cites at least one evidence id, and every cited id must name a row the recomputed
  value rests on. Citing a correct but unrelated row makes the claim unsupported.
- A metric scoped to a hole section also accepts the section's `ddr:hole-section` id. A metric
  scoped to a wellbore accepts `well:wellbore` where the matching tool returns it.
- `rt:log-value` ids cannot be cited: index values repeat within a log, so the id names no single
  row.

## Real-time curve statistics

Real-time curve statistics (count, minimum, maximum and mean from `curve_summary`) are not
checkable: no metric recomputes them, so a claim stating one is unverifiable.

## Production attribution

A wellbore's production is recomputed by `attributed_wellbore_key` (ADR 0002 D1, amendment of
2026-11-03). A cited `prod:monthly:<npdid>:<yyyy-mm>` id is matched through the published NPDID
it contains. A cited month that the workbook attributes to another wellbore contradicts the
claim.

## Metrics

Scope keys in brackets are optional. `section` is the hole-section number, `tier` is `primary`
or `possible`, `code` is `category -- subcategory`, months are `yyyy-mm`, and a volume metric
takes either `month` or `start` and `end` (inclusive).

| Metric | Claim type | Scope | Recomputed from |
|---|---|---|---|
| lost_hours | hours | wellbore, tier, [section], [code] | `fct_lost_time` hours |
| lost_time_activities | count | wellbore, tier, [section], [code] | `fct_lost_time` activities |
| code_hours | hours | wellbore, code, [section] | `fct_lost_time` hours, any tier |
| section_activity_hours | hours | wellbore, section | `dim_hole_section.activity_hours` |
| section_interruption_hours | hours | wellbore, section | `dim_hole_section.interruption_hours` |
| activity_duration | hours | [wellbore] | the cited activities' durations, summed |
| section_start_md | depth_m | wellbore, section | `dim_hole_section.start_md_m` |
| section_end_md | depth_m | wellbore, section | `dim_hole_section.end_md_m` |
| new_hole_drilled | depth_m | wellbore, section | `dim_hole_section.new_hole_drilled_m` |
| report_md | depth_m | wellbore, date | measured depth on that operations day's report |
| deepest_md | depth_m | wellbore | the deepest reported measured depth |
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
| section_report_count | count | wellbore, section | `dim_hole_section.report_count` |
| section_hole_size | hole_size_in | wellbore, section | `dim_hole_section.hole_size_in` |
| section_drilling_rate | rate_m_per_h | wellbore, section | new hole over hours coded drilling -- drill |
| wellbore_volume | volume_sm3 | wellbore, fluid, month or start and end | workbook monthly sheet by attributed wellbore; fluid `oil`, `gas`, `water`, `gas_injected` or `water_injected` |
| field_volume | volume_sm3 | field, fluid, basis, month or start and end | `fct_production_monthly_reconciliation`; field `VOLVE`, fluid `oil`, `gas` or `water`, basis `workbook`, `sodir_gross` or `sodir_net` |
| activity_code | code | [wellbore] | the cited activities' codes |
| quote | quote | [wellbore] | exact substring of a text field of a cited row, after redaction |

## Reporting results

Every scored result reports claim accuracy together with the unsupported rate and the
unverifiable rate; accuracy is never reported alone. The unsupported and unverifiable rates are
the shares of all claims with those results. Claim accuracy is defined with the scoring rules,
before the freeze.

## Held-out wellbores

Outside evaluation mode, a claim about a held-out wellbore, or one citing a held-out wellbore's
row, is unsupported (ADR 0002 D8).
