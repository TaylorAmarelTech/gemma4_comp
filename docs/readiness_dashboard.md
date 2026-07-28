# Readiness Dashboard

Current as of 2026-07-28. This replaces the historical 2026-05-02
appendix-ladder dashboard; the active submission scope is now the active Kaggle
Gemma 4 path.

## Active Scope

| Surface | Live status checked 2026-07-28 | What It Proves |
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
| Offline publication core | 12/12 composed gates pass in the model-free maintenance candidate, including provider-budget coverage, zero-item deferred-work integrity, the dated 11-item resolution receipt, and package-release ownership/install truth; rerun `python scripts/validate_publication_readiness.py --scope core` on any future release commit. |
| Public deployment | Pull request 16 at `1c8f6b25729da869b2775a29321ab3b74bd4715f` is the immediate fully merged predecessor to this closeout; all 16 checks passed. Render remains production through competition grading; the independent 51-route read-only `duecare-ai-site` and this repository's MkDocs site have distinct Pages ownership. After grading is owner-confirmed, centralized-host retirement is gated by [`POST_COMPETITION_HOSTING_TRANSITION.md`](POST_COMPETITION_HOSTING_TRANSITION.md); the fallback does not preserve mutable APIs. |
| Kimi/Gemini directional campaign | Frozen 500-candidate topology: 500 Kimi answers, deterministic grades, 500 Gemini 3.1 Pro cross-family contextual judgments, and 500 separately labeled Kimi self-judgments. Maximum 1,500 hosted calls under a US$35 ceiling. External access is blocked and all result counts remain zero. |
| Curator governance | Inline grading guidance covers all 75 universal rubric dimensions; the strict curator validator reports zero errors and zero warnings, and CI now fails on either. |
| Broad tests | Current maintenance-candidate `packages tests` run under the zero-call transport lock and offline provider/model flags: 4,669 passed, 9 skipped in 7 minutes 57 seconds. The registered Python cleanup slice also passes without file-wide suppression. |
| Model/flywheel cost stop | All five recurring Windows tasks disabled, four daemon sentinels present, and zero verified repository daemon processes; inspect with `scripts/stop_ollama_stack.ps1 -Status`. |
| New training readiness | Intentionally red: five dense generic-corridor typologies; 25 privacy-safe curation tasks and a 75-row minimum expansion target. |
| Harness contract | Documented in [`harness_ecosystem.md`](harness_ecosystem.md), [`harness_pattern.md`](harness_pattern.md), and [`harness_standard_contract.md`](harness_standard_contract.md). |
| Model loading | Standardized through [`Gemma4Runtime.load()`](model_loading_trace.md) for inference, with active A-00 training as the only direct FastModel exception. |
| Active A-00 default harness | `chat_no_online`: Persona + GREP + RAG/context + deterministic tools, with internet/import off. |
| Active A-00 judging | Combined rule + LLM judging with local Gemma by default and optional external judge adapters. |
| Active A-00 exports | HTML, Markdown, JSON, CSV, charts, activity/evidence bundles, and report manifest under `/kaggle/working`. |
| Test baseline | Focused contract gates are listed in [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md). |

## Closeout Actions

There are no remaining current human-review or owner-decision actions. The
dated [closeout resolution receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md) records
all 11 outcomes, and the [deferred-work register](DEFERRED_WORK.md) contains
zero items. Human curation, provider runs, package publication, Kaggle reruns,
and private transfer become work only when their specific reopen conditions are
met; they are not implied obligations of maintenance mode.

Future funded comparison work must include Kimi K3 and Meta Muse Spark 1.1 as
required lanes after exact provider IDs, access, capability, context, and
pricing are reverified. Unavailable access is a reportable result, not a reason
to substitute a different model silently.

The 2026-07-28 owner-authorized Kimi K3 access check reached the verified
Ollama model but all five capped requests returned HTTP 402 for empty extra
usage. It yielded zero completions, provider tokens, or actual ledger cost; the
500-prompt study was not run and no Kimi quality claim exists.

A later two-attempt baseline/full-harness smoke produced the same HTTP 402
access outcome and no answers. It did close the local implementation gap: the
full-harness adapter now sends structured messages to the deterministic tool
layer, and the frozen intervention verifiably contains GREP, eight RAG
documents, four tools, and the reasoning contract. Kimi testing remains a
funded-later next step, not an open closeout action; see the
[`paired receipt`](../configs/duecare/benchmarks/kimi_k3_harness_lift_smoke_20260728.json).

The resolved owner ledger lives in [`USER_TODO.md`](USER_TODO.md).

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

- Coding-agent handoff: [`CLAUDE_CODE_HANDOFF.md`](CLAUDE_CODE_HANDOFF.md)
- Stopping point and next work: [`PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md)
- Canonical deferred work: [`DEFERRED_WORK.md`](DEFERRED_WORK.md)
- Reviewer path: [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- Manual submitter checklist: [`USER_TODO.md`](USER_TODO.md)
- Current Kaggle inventory: [`current_kaggle_notebook_state.md`](current_kaggle_notebook_state.md)
- Harness inventory: [`harness_ecosystem.md`](harness_ecosystem.md)
