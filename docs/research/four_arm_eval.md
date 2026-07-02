# Four-arm evaluation (stock vs trained x harness off/on)

_generated 2026-06-29T15:21:30Z - git b4f44a9e_

This is a status report, not an evaluation result.

No paired data yet: no prompts graded for BOTH models in both off/on arms (run --run after training, or check the model labels).

Inputs checked: `reports/rich_lift/panel.jsonl` for stock arms A/B and `reports/four_arm/panel.jsonl` for trained arms C/D.

Run `python scripts/four_arm_eval.py --run --adapter reports/training/adapter` on a GPU after training to populate arms C/D, then rerun `python scripts/four_arm_eval.py --analyze` on CPU to refresh this report.

## Input preflight coverage

| input arm | unique prompts |
|---|---:|
| stock baseline (A) | 1595 |
| stock harness_full (B) | 1595 |
| trained baseline (C) | 0 |
| trained harness_full (D) | 0 |

Stock prompts ready for `--run` (both stock arms plus prompt text): **1595**.
Requested `--n=100` would run **100** prompts.
Four-arm paired prompts currently analyzable: **0**.
Blocking inputs: `trained_baseline_missing`, `trained_harness_full_missing`, `trained_paired_prompts_missing`.
No prompt IDs, prompt text, responses, or judge content are copied into this status report.

## Generalisation by typology

_no four-arm rows yet -- run --run after training to populate the trained arms (C/D)_
