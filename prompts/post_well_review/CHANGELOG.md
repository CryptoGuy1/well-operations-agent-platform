# Post-well review prompt versions

A prompt version is never edited once committed; a change is a new version. The agent uses the
version named by `PROMPT_VERSION` in `well_ops.agents.post_well_review.agent`.

| Version | Added | Status | Changes |
|---|---|---|---|
| v1 | 2026-11-04 | superseded by v2 | First version. |
| v2 | 2026-11-04 | superseded by v3 | Casing summary, well duration, lost-time share, true vertical depth, the Sodir completion date and the new metrics. |
| v3 | 2026-11-04 | in use | Campaigns, quote-backed casing sizes and exact evidence scoping. |

v2 names the metric `well_duration`, since renamed `report_span_days`; a v2 claim of it is
unverifiable with the current checker. v2 is kept unchanged as the record of the runs made with
it.
