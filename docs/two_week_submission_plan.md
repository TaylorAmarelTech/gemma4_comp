# Final Submission Execution Plan

Current as of 2026-07-26. This document replaces the old 2026-05-02 two-week
appendix-ladder plan. The remaining work is no longer broad notebook publishing;
it is validating the active kernels and preserving optional evidence from
the active A-00 pipeline.

## Scope

Run and verify:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`
- `kaggle/A-00-omni-experiment-workbench/`

Everything under `kaggle/_archive/notebooks/` is historical unless explicitly
revived later, including legacy notebook wrappers and task-notebook snapshots. Root `kaggle/`
should not contain appendix `A-*` folders other than active A-00, and the only root `04-*` folder
should be `04-kaggle-community-benchmark`.

## Priority Order

1. Run the model-free core publication gate and freeze the intended release
   commit, versions, citation metadata, and claim set.
2. Confirm the official Kaggle submission requirements and final deadline.
3. Decide whether to publish the existing bounded evidence now or first clear
   the separate 75-row corridor-diversity training blocker.
4. Run Kernel 01 and capture the default harness comparison path only if a new
   recording is needed.
5. Run Kernel 02 and capture the live demo/video path only if a new recording
   is needed.
6. Optional only: run active A-00 with a small proof configuration to confirm
   exports and report links if new proof artifacts are needed.
7. Optional only: run active A-00 again with the best available prompt
   count/training settings that fit the remaining wall-clock budget.
8. Download `/kaggle/working` outputs after every meaningful phase.
9. Submit with the current active Kaggle story, not the archived A-series story.

## Active A-00 Runtime Strategy

Use the preconfigured pipeline for the main proof. Keep options narrow:

- Small Gemma 4 model for generation/fine-tuning smoke runs.
- Offline harness default: Persona + GREP + RAG/context + deterministic tools.
- Combined rule + LLM judging at the end.
- Checkpoint/resume enabled for training.
- Larger Gemma/frontier/Ollama judge only if credentials and runtime allow.

If the run approaches Kaggle's time limit, stop at a saved checkpoint or after a
completed response/judging phase, download artifacts, and resume in a later
session.

## Evidence To Preserve

- Activity log export.
- Run manifest and pipeline request.
- Prompt/response artifacts for all arms.
- Harness traces for harnessed arms.
- Synthetic SFT rows.
- Training script, config, logs, checkpoint metadata, and final adapter path.
- Judge model configuration and per-response combined scores.
- HTML, Markdown, JSON, CSV, chart, and ZIP report artifacts.

## Do Not Spend Time On

- Rebuilding archived notebook-era surfaces.
- Reintroducing duplicate model-selection UI.
- Refactoring the canonical GREP/RAG corpus during final proof runs.
- Spending Ollama quota before an offline plan, frozen prompt/model/rubric
  scope, finite call allowance, and checkpoint-reuse decision exist.
- Adding broad new docs that compete with `FOR_PEER_REVIEW.md`,
  `USER_TODO.md`, and this execution plan.

## Related Current Docs

- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md) - reviewer verification path.
- [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) - canonical stopping
  point, offline gate, dataset blocker, and prioritized pickup backlog.
- [`USER_TODO.md`](USER_TODO.md) - manual actions.
- [`readiness_dashboard.md`](readiness_dashboard.md) - current status.
- [`model_loading_trace.md`](model_loading_trace.md) - model-loading contract.
- [`harness_ecosystem.md`](harness_ecosystem.md) - harness inventory.
