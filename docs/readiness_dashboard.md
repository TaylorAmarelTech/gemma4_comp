# Readiness Dashboard

Current as of 2026-07-27. This replaces the historical 2026-05-02
appendix-ladder dashboard; the active submission scope is now the active Kaggle
Gemma 4 path.

## Active Scope

| Surface | Live status checked 2026-07-27 | What It Proves |
|---|---|---|
| `kaggle/01-duecare-exploration-workbench/` | `COMPLETE` | Interactive harness comparison, chat, extraction, search controls, traces, and knowledge-pack flows. |
| `kaggle/02-live-demo/` | `CANCEL_ACKNOWLEDGED` | Focused live demo and video narrative path; rerun only for needed recording evidence. |
| `kaggle/A-00-omni-experiment-workbench/` | `CANCEL_ACKNOWLEDGED` | Quantitative proof path; the canceled run is not completion evidence. |

The public A-00 Kaggle page attaches
`taylorsamarel/duecare-proof-finetuning-data`, and Kaggle reports that proof
dataset ready. The latest notebook run is canceled; it needs a fresh successful
execution and artifact review before it is cited as completed proof. The existing
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
| Offline publication core | 11/11 composed gates passed in the 2026-07-27 closeout candidate, including provider-budget coverage, deferred-work integrity, and package-release ownership/install truth; rerun `python scripts/validate_publication_readiness.py --scope core` on the release commit. |
| Public deployment | Pull request 8 is the latest validated substantive baseline at `9385a837879209e18f8e013cf969a3e1ecbcfc91`; all 16 PR checks, six merge-triggered workflows, MkDocs Pages, website artifact, Render project status, and all six schema routes passed. The latest 588-link audit found zero confirmed broken links and nine transient/unverified hosts. |
| Curator governance | Inline grading guidance covers all 75 universal rubric dimensions; the strict curator validator reports zero errors and zero warnings, and CI now fails on either. |
| Broad tests | Closeout 18-package `packages tests` run under the zero-call transport lock: 4,637 passed, 9 skipped with no warning summary. The focused 43-test kit run also passes with `RuntimeWarning` promoted to an error. |
| Model/flywheel cost stop | All five recurring Windows tasks disabled, four daemon sentinels present, and zero verified repository daemon processes; inspect with `scripts/stop_ollama_stack.ps1 -Status`. |
| New training readiness | Intentionally red: five dense generic-corridor typologies; 25 privacy-safe curation tasks and a 75-row minimum expansion target. |
| Harness contract | Documented in [`harness_ecosystem.md`](harness_ecosystem.md), [`harness_pattern.md`](harness_pattern.md), and [`harness_standard_contract.md`](harness_standard_contract.md). |
| Model loading | Standardized through [`Gemma4Runtime.load()`](model_loading_trace.md) for inference, with active A-00 training as the only direct FastModel exception. |
| Active A-00 default harness | `chat_no_online`: Persona + GREP + RAG/context + deterministic tools, with internet/import off. |
| Active A-00 judging | Combined rule + LLM judging with local Gemma by default and optional external judge adapters. |
| Active A-00 exports | HTML, Markdown, JSON, CSV, charts, activity/evidence bundles, and report manifest under `/kaggle/working`. |
| Test baseline | Focused contract gates are listed in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). |

## Remaining Human Actions

The generated [`DEFERRED_WORK.md`](DEFERRED_WORK.md) register is authoritative
for owners, prerequisites, model/network boundaries, evidence, and acceptance.

1. Choose the first independently versioned Python package to release, freeze
   the intended commit/tag, and rerun the model-free core and handoff gates.
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
- Canonical deferred work: [`DEFERRED_WORK.md`](DEFERRED_WORK.md)
- Reviewer path: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual submitter checklist: [`USER_TODO.md`](USER_TODO.md)
- Current Kaggle inventory: [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Harness inventory: [`harness_ecosystem.md`](harness_ecosystem.md)
