# DueCare Project Status

Current as of 2026-07-15.

## Active Submission Scope

The active Kaggle path is exactly three script-kernel folders:

| Kernel | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad interactive workbench for chat, harness comparison, extraction, search controls, knowledge packs, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo and video narrative path. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline vs harnessed arms, synthetic data, fine-tune, judging, and report artifacts. |

The public A-00 Kaggle page attaches
`taylorsamarel/duecare-proof-finetuning-data`. That dataset is a guarded
preview, not the full advanced corpus, and Kaggle reports it ready. The Kaggle
execution still needs a terminal status and artifact review before it is cited
as a completed proof run, and no production adapter is published.

The interim training collection is public: the SFT and preference dataset views
both report ready, and the integrity, CPU training-plan, and four-arm evaluation
notebooks all completed on 2026-07-15. These are exact-row companions to the
small approved proof release. The completed training starter emitted a plan but
did not execute GPU training, so this does not close the adapter or model-lift
work.

The retired A-series notebook ladder other than active A-00, task-notebook
snapshots, and older checklist/status docs are archived under
`docs/_archive/2026-05-16-legacy-notebook-era/` or
`kaggle/_archive/notebooks/`. Root `kaggle/` should not contain appendix
`A-*` folders other than `A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`.

## Current Technical Posture

- Local Gemma inference is standardized through `Gemma4Runtime.load()`.
- Active A-00 uses the same offline default harness as the Kernel 01 comparison path:
  Persona + GREP + RAG/context + deterministic tools, with internet/import off.
- Active A-00 can run local Gemma judging by default and optional external judge paths
  when credentials are present.
- Active A-00 training supports checkpoint/resume, adapter save/load, and final report
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

1. Run and capture the two active Kaggle kernels.
2. Optional only: produce a reproducible A-00 evidence run and
   preserve `/kaggle/working` outputs before shutdown if new proof artifacts
   are needed.
3. Use checkpoint/resume for any longer training run.
4. Attach the final report, activity log, prompt/response artifacts, training
   metadata, charts, and evidence ZIP to the writeup/video workflow.
5. Keep new documentation changes pointed at the current active Kaggle path; treat
   A-00 as archived proof material unless Taylor explicitly restores it.

## Verification

Use the focused commands in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). The docs
contract tests intentionally fail if current entry docs drift back toward the
retired appendix-ladder framing.
