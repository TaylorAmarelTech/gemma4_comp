# DueCare Project Status

Current as of 2026-05-17.

## Active Submission Scope

The active Kaggle path is exactly three script kernels:

| Kernel | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad interactive workbench for chat, harness comparison, extraction, search controls, knowledge packs, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo and video narrative path. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative experiment pipeline for baseline, harnessed output, synthetic rows, optional LoRA training, combined judging, and evidence exports. |

The retired A-series notebook ladder and older checklist/status docs are
archived under `docs/_archive/2026-05-16-legacy-notebook-era/`.

## Current Technical Posture

- Local Gemma inference is standardized through `Gemma4Runtime.load()`.
- A-00 uses the same offline default harness as the Kernel 01 comparison path:
  Persona + GREP + RAG/context + deterministic tools, with internet/import off.
- A-00 can run local Gemma judging by default and optional external judge paths
  when credentials are present.
- A-00 training supports checkpoint/resume, adapter save/load, and final report
  export.
- The harness system is documented as an ecosystem rather than a single
  monolithic harness.

## Current Docs To Trust

- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md) - reviewer verification path.
- [`USER_TODO.md`](USER_TODO.md) - manual actions before submission.
- [`readiness_dashboard.md`](readiness_dashboard.md) - current status snapshot.
- [`two_week_submission_plan.md`](two_week_submission_plan.md) - final execution
  plan.
- [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md) -
  active versus archived Kaggle inventory.
- [`harness_ecosystem.md`](harness_ecosystem.md),
  [`harness_pattern.md`](harness_pattern.md), and
  [`harness_standard_contract.md`](harness_standard_contract.md) - harness
  contract and inventory.
- [`model_loading_trace.md`](model_loading_trace.md) - Gemma 4 runtime contract.

## Remaining Work

1. Run and capture the three active Kaggle kernels.
2. Produce a reproducible A-00 evidence run and preserve `/kaggle/working`
   outputs before shutdown.
3. Use checkpoint/resume for any longer training run.
4. Attach the final report, activity log, prompt/response artifacts, training
   metadata, charts, and evidence ZIP to the writeup/video workflow.
5. Keep new documentation changes pointed at A-00 and the current three-kernel
   path.

## Verification

Use the focused commands in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). The docs
contract tests intentionally fail if current entry docs drift back toward the
retired appendix-ladder framing.
