# Author's Notes

Current as of 2026-05-17.

## What Still Matters Most

The strongest part of DueCare is the inspectable harness trace. The important
claim is not that Gemma 4 can answer a prompt; it is that the system can show
what was wrapped around the model before it answered:

- Persona instructions.
- GREP rule hits.
- RAG/context snippets.
- Deterministic tool outputs.
- Search/import context only when explicitly enabled.
- Final prompt/response artifacts.
- Combined rule + LLM judging outputs.

That trace is what lets a worker, caseworker, lawyer, regulator, reviewer, or
researcher ask what the model actually saw before producing an answer.

## What Changed Late

The early submission plan used a wide appendix-notebook ladder. That was useful
for exploration but created too many places for stale state. The current plan is
intentionally narrower:

1. `kaggle/01-duecare-exploration-workbench/` shows the broad harness surface.
2. `kaggle/02-live-demo/` supports the focused demo and video story.
3. `kaggle/A-00-omni-experiment-workbench/` produces the quantitative evidence
   run: baseline, harnessed output, synthetic rows, optional LoRA training,
   combined judging, and exports.

The old A-series ladder remains historical design provenance, not the current
reviewer path.

## Model Judgment

The smaller Gemma path is practical for Kaggle proof runs. Larger Gemma variants
or frontier judges can produce better synthetic training data and more nuanced
final grading. A-00 keeps this distinction explicit by separating:

- generation/fine-tuning model,
- optional fine-tuned adapter,
- final judge model.

The demo does not need a frontier judge, but the architecture should allow one.

## Harness Judgment

The project should describe itself as a harness ecosystem, not a single
harness. The current registered harnesses and broader pipeline families are
documented in:

- [`harness_ecosystem.md`](harness_ecosystem.md)
- [`harness_pattern.md`](harness_pattern.md)
- [`harness_standard_contract.md`](harness_standard_contract.md)

The default A-00 proof path intentionally uses the offline harness: Persona +
GREP + RAG/context + deterministic tools, with internet and import disabled.

## Remaining Constraint

The practical constraint is time. For final proof runs, the best evidence is a
complete exported A-00 report bundle with prompts, responses, traces, training
metadata, judging rows, charts, and the full activity log preserved from
`/kaggle/working`.
