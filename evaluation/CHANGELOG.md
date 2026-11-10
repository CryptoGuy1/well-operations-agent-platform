# Evaluation changelog

The evaluation rules (`evaluation/RULES.md`) were frozen with the tag `v0.3.0-rules` on
2026-11-09, before any scored run. Every change after the first scored run, to the rules, the
prompts, the settings, the answer key or the code that scores, is dated here, with its reason
and the release number it applies from.

## Changes

### 2026-11-10: release r2 completed

r2 ran on commit `9d230c1` with the changes of the 2026-11-09 entry and nothing else changed: 30 of 30 runs
scored (15 primary, 15 baseline), no task failures, USD 4.9212 of the USD 8 cap. One primary run
hit a streaming `ReadTimeout`; it was classified as a network error and rerun once, and the
rerun scored. The secondary model was not configured and did not run.

- Primary system, first draft (scored): claim accuracy 100.0 % over all runs (lowest run
  99.5 %); 1 contradicted claim of 3077 first-draft claims, in one run, not on an answer-key
  fact; 0 answer-key facts wrong; answer-key coverage 64.1 % (47.3 % to 77.7 %); unsupported
  rate 5.1 %, unverifiable rate 0.6 %, unclaimed-number rate 2.9 %.
- Final draft after checker feedback (reported separately, 13 runs; 2 runs had no findings and
  no revision): 0 contradicted claims, coverage 70.3 %.
- Baseline (same model, no tools): every draft completed with 0 claims and 0 unclaimed numbers,
  so coverage is 0.0 % and the claim rates are not defined. 9 of its 146 sentences, in 7 of 15
  drafts, state that information is unknown or unavailable (keyword count); no sentence holds
  a number the checker counts as a quantity. The baseline therefore does not measure value
  accuracy without tools.

### 2026-11-09: release r1 failed; applies from release r2

r1 failed: all 3 completed primary runs hit max_tokens 64000 before submitting a draft (task
failures, no draft); the harness then stopped on a streaming timeout it did not classify as a
network error (harness bug). r2 changes: max_tokens 128000 (the model's documented maximum) and
transport-error classification. Both changes were made after observing held-out failures; they
change output capacity and error handling only, not the prompt, tools, checker, effort or answer
key.

- `max_tokens` is 128000 in the frozen settings, the settings default and `RULES.md`.
- `classify()` counts the HTTP library's transport errors (a read timeout or a dropped
  connection while a response streams, which the SDK does not wrap) as network errors, rerun at
  most twice as the rules already say.
- A streamed response waits up to 1800 s between two bytes (connect 5 s), so a whole
  128000-token response cannot time out while it streams; the default was 600 s.
- r1's partial results are kept in `evaluation/results/r1/` as the record of the failed release.
  r2 has its own USD 8 cap.
