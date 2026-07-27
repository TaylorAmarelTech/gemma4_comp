# Readiness Dashboard

Current as of 2026-07-26. This replaces the historical 2026-05-02
appendix-ladder dashboard; the active submission scope is now the active Kaggle
Gemma 4 path.

## Active Scope

| Surface | Status | What It Proves |
|---|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Active | Interactive harness comparison, chat, extraction, search controls, traces, and knowledge-pack flows. |
| `kaggle/02-live-demo/` | Active | Focused live demo and video narrative path. |
| `kaggle/A-00-omni-experiment-workbench/` | Active | Quantitative proof path: baseline vs harnessed arms, synthetic data, fine-tune, judging, and report artifacts. |

The public A-00 Kaggle page attaches
`taylorsamarel/duecare-proof-finetuning-data`, and Kaggle reports that proof
dataset ready. The notebook run still needs a terminal Kaggle status and
artifact review before it is cited as a completed proof run. The existing
adapter artifact is smoke-only, and no production adapter or full advanced
corpus is published.

The auxiliary interim collection is green for publication mechanics: both
exact-row dataset views are ready, and the integrity audit, CPU training-plan,
and four-arm evaluation notebooks reached `COMPLETE` on 2026-07-15. This proves
manifested data handoff and frozen evaluation planning. It does not prove GPU
training success or model improvement; no adapter weights are attached.

Archived A-series notebooks, task-notebook snapshots, and old generated
mirrors are not the active competition path. Root `kaggle/` should not contain
appendix `A-*` folders other than active `A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
`04-kaggle-community-benchmark`. See [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
and [`kaggle/_INDEX.md`](../kaggle/_INDEX.md).

## Current Green Checks

| Area | Current State |
|---|---|
| Offline publication core | 8/8 composed gates passed on 2026-07-26; rerun `python scripts/validate_publication_readiness.py --scope core` on the release commit. |
| Broad tests | Clean locked 18-package `packages tests` run: 4,582 passed, 9 skipped with no warning summary. The focused 43-test kit run also passes with `RuntimeWarning` promoted to an error. |
| New training readiness | Intentionally red: five dense generic-corridor typologies; 25 privacy-safe curation tasks and a 75-row minimum expansion target. |
| Harness contract | Documented in [`harness_ecosystem.md`](harness_ecosystem.md), [`harness_pattern.md`](harness_pattern.md), and [`harness_standard_contract.md`](harness_standard_contract.md). |
| Model loading | Standardized through [`Gemma4Runtime.load()`](model_loading_trace.md) for inference, with active A-00 training as the only direct FastModel exception. |
| Active A-00 default harness | `chat_no_online`: Persona + GREP + RAG/context + deterministic tools, with internet/import off. |
| Active A-00 judging | Combined rule + LLM judging with local Gemma by default and optional external judge adapters. |
| Active A-00 exports | HTML, Markdown, JSON, CSV, charts, activity/evidence bundles, and report manifest under `/kaggle/working`. |
| Test baseline | Focused contract gates are listed in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). |

## Remaining Human Actions

1. Freeze the intended release commit and rerun the model-free publication core.
2. Run the two primary demo kernels on the intended GPU/runtime shape only when
   new recording evidence is needed.
3. Optional only: produce an A-00 evidence run with checkpoint/resume
   enabled if new proof artifacts are needed.
4. Download `/kaggle/working` artifacts before Kaggle shutdown.
5. Capture final demo screenshots/video clips from Kernel 01 and Kernel 02.
6. Submit with links pointing to the current active Kaggle path.

The manual checklist lives in [`USER_TODO.md`](USER_TODO.md).

## Active A-00 Evidence Run Targets

Model quota is deliberately deferred during the current wrap-up. Plan and hash
the run first; do not start a model merely to make the dashboard greener. For a
later fast proof run, use 4 prompts and training disabled or a very short LoRA
smoke path. For a writeup-quality run, use the highest prompt count that fits
inside the remaining Kaggle wall-clock budget, keep checkpoints enabled, and
prefer a larger Gemma/frontier judge only if credentials and runtime allow.

Required exported evidence:

- Full activity log with all step details.
- Prompt/response JSONL for every arm.
- Synthetic SFT rows when generation is enabled.
- Training config, checkpoints, adapter path, and resume metadata when training
  is enabled.
- Final rule + LLM judging rows.
- HTML/Markdown/JSON report plus charts and manifest.

## Current Risks

| Risk | Mitigation |
|---|---|
| Kaggle runtime hits the time limit | Keep checkpoint/resume enabled and save artifacts after each major phase. |
| A-00 judging takes too long | Use local small Gemma for proof runs; reserve larger/frontier judges for final scoring or post-run regrade. |
| Old docs confuse reviewers | Active entry docs now point to the current Kaggle scope; legacy roadmap docs live under `docs/_archive/`. |
| Harness parity drifts | Contract tests pin Kernel 01 and active A-00 parity for runtime loading, default harness layers, and shared GREP/RAG/tool usage. |
| Model quota is spent before the scope is frozen | Keep `DUECARE_MAX_PLANNED_MODEL_CALLS=0`, use the rich-harness `--plan`, and unlock only a finite sampled allowance. |
| A new training claim learns corridor shortcuts | Clear the strict 75-row diversification target without weakening the audit threshold, then refresh append-only provenance. |

## Start Here

- Stopping point and next work: [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md)
- Reviewer path: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual submitter checklist: [`USER_TODO.md`](USER_TODO.md)
- Current Kaggle inventory: [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Harness inventory: [`harness_ecosystem.md`](harness_ecosystem.md)
