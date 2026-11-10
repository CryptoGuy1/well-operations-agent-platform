# Evaluation changelog

The evaluation rules (`evaluation/RULES.md`) were frozen with the tag `v0.3.0-rules` on
2026-11-09, before any scored run. Every change after the first scored run, to the rules, the
prompts, the settings, the answer key or the code that scores, is dated here, with its reason
and the release number it applies from.

## Changes

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
