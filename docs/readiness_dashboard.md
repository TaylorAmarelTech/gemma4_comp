# Readiness Dashboard

Current as of 2026-05-17. This replaces the historical 2026-05-02
appendix-ladder dashboard; the active submission scope is now the three-kernel
Gemma 4 path.

## Active Scope

| Surface | Status | What It Proves |
|---|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Active | Interactive harness comparison, chat, extraction, search controls, traces, and knowledge-pack flows. |
| `kaggle/02-live-demo/` | Active | Focused live demo and video narrative path. |
| `kaggle/A-00-omni-experiment-workbench/` | Active | Quantitative proof run: baseline, harnessed run, synthetic rows, optional LoRA training, final judging, and export bundle. |

Archived A-series notebooks and old generated mirrors are not the active
competition path. See [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
and [`kaggle/_INDEX.md`](../kaggle/_INDEX.md).

## Current Green Checks

| Area | Current State |
|---|---|
| Harness contract | Documented in [`harness_ecosystem.md`](harness_ecosystem.md), [`harness_pattern.md`](harness_pattern.md), and [`harness_standard_contract.md`](harness_standard_contract.md). |
| Model loading | Standardized through [`Gemma4Runtime.load()`](model_loading_trace.md) for inference, with A-00 training as the only active direct FastModel exception. |
| A-00 default harness | `chat_no_online`: Persona + GREP + RAG/context + deterministic tools, with internet/import off. |
| A-00 judging | Combined rule + LLM judging with local Gemma by default and optional external judge adapters. |
| A-00 exports | HTML, Markdown, JSON, CSV, charts, activity/evidence bundles, and report manifest under `/kaggle/working`. |
| Test baseline | Focused contract gates are listed in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). |

## Remaining Human Actions

1. Run the three active Kaggle kernels on the intended GPU/runtime shape.
2. Produce at least one A-00 evidence run with checkpoint/resume enabled.
3. Download `/kaggle/working` artifacts before Kaggle shutdown.
4. Capture final demo screenshots/video clips from Kernel 01, Kernel 02, and
   A-00.
5. Submit with links pointing to the current three-kernel path.

The manual checklist lives in [`USER_TODO.md`](USER_TODO.md).

## A-00 Evidence Run Targets

For a fast proof run, use 4 prompts and training disabled or a very short LoRA
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
| Old docs confuse reviewers | Active entry docs now point to the three-kernel scope; legacy roadmap docs live under `docs/_archive/`. |
| Harness parity drifts | Contract tests pin Kernel 01/A-00 parity for runtime loading, default harness layers, and shared GREP/RAG/tool usage. |

## Start Here

- Reviewer path: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual submitter checklist: [`USER_TODO.md`](USER_TODO.md)
- Current Kaggle inventory: [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Harness inventory: [`harness_ecosystem.md`](harness_ecosystem.md)
