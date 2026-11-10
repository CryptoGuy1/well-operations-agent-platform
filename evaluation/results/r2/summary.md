# Evaluation release r2

- Date: 2026-11-10; code version: `9d230c15f5fa801690a90bea261e57d9977d8a2b`
- Rules: `evaluation/RULES.md` (SHA-256 `ac8170cdfc66`)
- Answer key: SHA-256 `15a6d5400ba64819fccaed094386c13aae09f6bf97d31d73f432b7a697867d0e`, built from commit `777f2bd83bc50a23b77f7764d143097d20d02a9a` (`evaluation/answers/answer_key.sha256`)
- Scored wellbores: 5 (held_out)
- primary: model `claude-haiku-5-5`, prompt `prompts/post_well_review/v3.md` (SHA-256 `497d75716a58`), connector tools and one revision turn; 3 runs per wellbore
- baseline: model `claude-haiku-5-5`, prompt `prompts/post_well_review_baseline/v1.md` (SHA-256 `4909ab2c000c`), no tools, no revision; 3 runs per wellbore
- Settings: effort default, max_tokens 128000, max_steps 20, tool_row_cap 200
- Budget: USD 8.0 cap; USD 4.9212 spent

## Runs

| System | Planned | scored | task failure | infrastructure failure | budget stopped | Not run |
|---|---|---|---|---|---|---|
| primary | 15 | 15 | 0 | 0 | 0 | 0 |
| baseline | 15 | 15 | 0 | 0 | 0 | 0 |

Each cell is the mean, with the minimum to maximum in brackets, over the runs of that wellbore; n is the number of runs behind a value when it is not every run.

## Primary system: first draft (scored)

| Metric | 15/9-F-14 | 15/9-F-12 | 15/9-F-4 | 15/9-F-9 A | 15/9-F-15 | All runs |
|---|---|---|---|---|---|---|
| Claim accuracy | 100.0 % (100.0 % to 100.0 %) | 99.8 % (99.5 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (99.5 % to 100.0 %) |
| Unsupported rate | 1.5 % (0.0 % to 3.9 %) | 4.9 % (1.7 % to 7.8 %) | 5.7 % (0.0 % to 13.0 %) | 3.4 % (0.6 % to 8.6 %) | 10.3 % (8.6 % to 13.5 %) | 5.1 % (0.0 % to 13.5 %) |
| Unverifiable rate | 0.0 % (0.0 % to 0.0 %) | 2.6 % (0.0 % to 7.8 %) | 0.0 % (0.0 % to 0.0 %) | 0.3 % (0.0 % to 1.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.6 % (0.0 % to 7.8 %) |
| Unclaimed-number rate | 4.5 % (0.0 % to 11.6 %) | 3.5 % (1.4 % to 6.8 %) | 1.0 % (0.0 % to 2.2 %) | 4.1 % (2.2 % to 7.3 %) | 1.4 % (0.0 % to 3.0 %) | 2.9 % (0.0 % to 11.6 %) |
| Answer-key coverage | 67.0 % (52.4 % to 77.7 %) | 56.2 % (51.4 % to 59.5 %) | 57.5 % (47.3 % to 69.2 %) | 66.1 % (59.6 % to 70.2 %) | 73.6 % (71.7 % to 77.4 %) | 64.1 % (47.3 % to 77.7 %) |
| Key facts wrong | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) |
| Claims | 240.3 (228 to 248) | 223.3 (206 to 232) | 218 (215 to 221) | 181.7 (165 to 198) | 162.3 (161 to 163) | 205.1 (161 to 248) |
| Cost (USD) | 0.3667 (0.3147 to 0.4538) | 0.2829 (0.1726 to 0.3716) | 0.3443 (0.2629 to 0.4583) | 0.3245 (0.2868 to 0.3448) | 0.2798 (0.1238 to 0.3846) | 0.3196 (0.1238 to 0.4583) |
| Latency (s) | 332 (275 to 397) | 307 (277 to 335) | 310 (268 to 379) | 280 (246 to 307) | 277 (239 to 310) | 301 (239 to 397) |

## Primary system: final draft after checker feedback

Reported separately; never a headline metric. Runs without a revision have no final draft.

| Metric | 15/9-F-14 | 15/9-F-12 | 15/9-F-4 | 15/9-F-9 A | 15/9-F-15 | All runs |
|---|---|---|---|---|---|---|
| Claim accuracy | 100.0 % (100.0 % to 100.0 %), n=2 | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %), n=2 | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %), n=13 |
| Unsupported rate | 0.0 % (0.0 % to 0.0 %), n=2 | 4.4 % (0.0 % to 13.2 %) | 0.0 % (0.0 % to 0.0 %), n=2 | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 1.0 % (0.0 % to 13.2 %), n=13 |
| Unverifiable rate | 0.0 % (0.0 % to 0.0 %), n=2 | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %), n=2 | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %), n=13 |
| Unclaimed-number rate | 0.0 % (0.0 % to 0.0 %), n=2 | 0.0 % (0.0 % to 0.0 %) | 0.2 % (0.0 % to 0.5 %), n=2 | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.5 %), n=13 |
| Answer-key coverage | 67.0 % (62.1 % to 71.8 %), n=2 | 57.1 % (51.4 % to 63.1 %) | 63.7 % (61.5 % to 65.9 %), n=2 | 71.9 % (61.4 % to 82.5 %) | 88.7 % (84.9 % to 92.5 %) | 70.3 % (51.4 % to 92.5 %), n=13 |
| Key facts wrong | 0 (0 to 0), n=2 | 0 (0 to 0) | 0 (0 to 0), n=2 | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0), n=13 |
| Claims | 246 (240 to 252), n=2 | 228.7 (208 to 242) | 220.5 (216 to 225), n=2 | 183.7 (167 to 198) | 164 (161 to 166) | 204.8 (161 to 252), n=13 |
| Removed during revision: claims | 1 (0 to 2), n=2 | 6 (0 to 18) | 0 (0 to 0), n=2 | 0.7 (0 to 2) | 1 (0 to 3) | 1.9 (0 to 18), n=13 |
| Removed during revision: numbers | 9 (1 to 17), n=2 | 3.7 (1 to 9) | 0.5 (0 to 1), n=2 | 7.3 (2 to 12) | 0 (0 to 0) | 4 (0 to 17), n=13 |

## Baseline and primary system, value only

The baseline (same model, no tools) is scored on value only, with the evidence requirement waived; the primary system's first draft is shown checked the same way.

### Baseline

| Metric | 15/9-F-14 | 15/9-F-12 | 15/9-F-4 | 15/9-F-9 A | 15/9-F-15 | All runs |
|---|---|---|---|---|---|---|
| Claim accuracy | n/a | n/a | n/a | n/a | n/a | n/a |
| Unsupported rate | n/a | n/a | n/a | n/a | n/a | n/a |
| Unverifiable rate | n/a | n/a | n/a | n/a | n/a | n/a |
| Unclaimed-number rate | n/a | n/a | n/a | n/a | n/a | n/a |
| Answer-key coverage | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) |
| Key facts wrong | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) |
| Claims | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) |
| Cost (USD) | 0.0008 (0.0006 to 0.0009) | 0.0007 (0.0005 to 0.0010) | 0.0008 (0.0006 to 0.0010) | 0.0007 (0.0005 to 0.0010) | 0.0007 (0.0006 to 0.0009) | 0.0007 (0.0005 to 0.0010) |
| Latency (s) | 7 (6 to 7) | 6 (5 to 7) | 6 (6 to 7) | 6 (5 to 7) | 6 (6 to 7) | 6 (5 to 7) |

### Primary system, first draft, value only

| Metric | 15/9-F-14 | 15/9-F-12 | 15/9-F-4 | 15/9-F-9 A | 15/9-F-15 | All runs |
|---|---|---|---|---|---|---|
| Claim accuracy | 100.0 % (100.0 % to 100.0 %) | 99.8 % (99.5 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (100.0 % to 100.0 %) | 100.0 % (99.5 % to 100.0 %) |
| Unsupported rate | 0.0 % (0.0 % to 0.0 %) | 0.3 % (0.0 % to 1.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.2 % (0.0 % to 0.6 %) | 0.1 % (0.0 % to 1.0 %) |
| Unverifiable rate | 0.0 % (0.0 % to 0.0 %) | 2.6 % (0.0 % to 7.8 %) | 0.0 % (0.0 % to 0.0 %) | 0.3 % (0.0 % to 1.0 %) | 0.0 % (0.0 % to 0.0 %) | 0.6 % (0.0 % to 7.8 %) |
| Unclaimed-number rate | 4.5 % (0.0 % to 11.6 %) | 3.5 % (1.4 % to 6.8 %) | 1.0 % (0.0 % to 2.2 %) | 4.1 % (2.2 % to 7.3 %) | 1.4 % (0.0 % to 3.0 %) | 2.9 % (0.0 % to 11.6 %) |
| Answer-key coverage | 70.2 % (61.2 % to 77.7 %) | 62.2 % (56.8 % to 66.7 %) | 65.6 % (61.5 % to 69.2 %) | 71.9 % (61.4 % to 82.5 %) | 87.4 % (84.9 % to 88.7 %) | 71.5 % (56.8 % to 88.7 %) |
| Key facts wrong | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) | 0 (0 to 0) |
| Claims | 240.3 (228 to 248) | 223.3 (206 to 232) | 218 (215 to 221) | 181.7 (165 to 198) | 162.3 (161 to 163) | 205.1 (161 to 248) |

## Secondary model (reported separately, never pooled with the primary results)

Not run.

## Infrastructure errors and reruns

| System | Wellbore | Run | Run id | Error | Kind |
|---|---|---|---|---|---|
| primary | 15/9-F-15 | 1 | `20261110T014706Z-68be67ec` | ReadTimeout | network |
