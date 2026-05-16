# Focused Copilot prompts

Five band-scoped prompts for Copilot GPT 5.4x. Each prompt reviews
one slice of the Kaggle notebook curriculum and keeps to that slice
only. All five share a common discipline layer in
`_shared_discipline.md` and treat
`docs/current_kaggle_notebook_state.md` as the single source of
truth for kernel inventory.

| File | Bands | Scope |
|---|---|---|
| `_shared_discipline.md` | all | Voice, engineering discipline, curriculum principles, full curriculum map, orphan decision gate |
| `01_exploration_and_basic_eval.md` | 100 to 290 | Load Gemma 4, free-form playground, evaluation framework walkthrough, sample evaluations, sample cross-model comparisons. Also owns the decision for `forge_llm_core_demo.ipynb` |
| `02_data_pipeline_and_prompt_generation.md` | 300 to 390 | Document scraping, categorization, distillation, prompt generation from facts, prompt remixing, Anonymizer gate, training-JSONL assembly |
| `03_advanced_model_testing_and_evaluation.md` | 400 to 590 | Full-corpus evaluation, enhanced cross-model evaluation with prompt engineering and RAG, ablations, self-learning adversarial harness |
| `04_tools_templates_and_function_calling.md` | 600 to 690 | Native function calling, tool call evaluation, tool generation and maintenance, template library, adversarial tool abuse |
| `05_demo_implementation_and_architecture.md` | 800 to 990 | Enterprise server-side demo, client-side on-device demo, NGO public API demo, suitability scorecard, final results dashboard, writeup and video companions, business model |
| `06_build_fix_publish_all_notebooks.md` | all bands | Execution prompt. Takes review outputs and actually builds, fixes, renames, validates, and publishes every notebook to Kaggle. Nine sequential phases with validation gates. |

## How to use

1. Read `docs/current_kaggle_notebook_state.md` to confirm today's
   kernel state.
2. Run prompts 01 through 05 first (review and design). Each
   produces one markdown file under `docs/review/`.
3. Run prompt 06 last (execution). It reads the review outputs and
   builds, fixes, renames, and publishes notebooks to Kaggle. It
   produces `docs/review/notebook_publish_report.md`.

## ClaudeCode cleanup ladder

These newer prompts are execution-first prompts for ClaudeCode inside
this repo. They are scoped to the current DueCare Kaggle suite rather
than the older Copilot review bands above.

| File | Scope | Mode |
|---|---|---|
| `16_claude_cumulative_review_through_210.md` | 000 through 210 | Cumulative review checkpoint, with deep review on 210 |
| `17_claudecode_cleanup_220_through_399.md` | 220, 230, 240, 250, 260, 270, 399 | Execute cleanup for the rest of baseline text comparisons |
| `18_claudecode_cleanup_300_400_410_420_499.md` | 300, 400, 410, 420, 499 | Execute cleanup for advanced evaluation |
| `19_claudecode_cleanup_310_430_440_699.md` | 310, 430, 440, 699 | Execute cleanup for advanced prompt-test generation |
| `20_claudecode_cleanup_320_450_799.md` | 320, 450, 799 | Execute cleanup for adversarial prompt-test evaluation |
| `21_claudecode_cleanup_500_510_520_530_599.md` | 500, 510, 520, 530, 599 | Execute cleanup for model improvement opportunities |
| `22_claudecode_cleanup_600_610_899.md` | 600, 610, 899 | Execute cleanup for solution surfaces and closing arc |
| `23_claudecode_full_suite_cleanup_orchestrator.md` | full suite | Run the whole cleanup ladder in order |
| `24_claude_reconcile_suite_state_and_next_steps.md` | full suite | Reconcile current state, implement the next fixes, and leave the next push queue ready |
| `25_claude_review_fix_and_execute_next_steps.md` | full suite | Direct execution prompt to review, fix, rebuild, validate, and continue into the next work |

Suggested order:

1. Run `16` first if you want a fresh cumulative read-through before
   editing.
2. Run `17` through `22` section by section to land fixes.
3. Run `23` only when you want one end-to-end execution pass.
4. Run `24` when you want one repo-grounded pass that both reconciles
   state and lands the next batch of concrete fixes before retrying
   Kaggle pushes.
5. Run `25` when you want the most direct execution prompt: review the
   current state, fix what is fixable now, rebuild, validate, and keep
   going into the next safe batch.

## Status And Action Docs

These are continuation documents rather than direct execution prompts.
They capture the current suite state and the exact next work queue.

| File | Purpose |
|---|---|
| `26_suite_status_snapshot.md` | Snapshot of what changed, what validated, and what remains open as of 2026-04-16 |
| `27_next_steps_action_plan.md` | First-pass ordered action plan derived from the 26 snapshot |
| `28_confirmed_detailed_action_plan.md` | Refined, more explicit continuation plan with Windows-safe commands and clarified ownership gaps |
| `29_verified_continuation_and_improvement_plan.md` | Post-28 verification-first continuation plan that requires builder proof before trusting emitted notebooks and pulls shared fixes forward only when they reduce duplicate work |
| `30_project_checkpoint.md` | Full project checkpoint and handoff that supersedes narrower continuation docs when repo-truth reconciliation is needed |

## Chained Publish And Hardening Prompts

These prompts split the remaining notebook work into five sequential
execution stages. Each stage must write a concrete markdown artifact
under `docs/review/`, and the next stage must read that artifact before
acting. The chain is designed for real repo execution, not recommendation-only review.

| File | Stage | Output artifact |
|---|---|---|
| `31a_repo_truth_and_publish_inventory.md` | Reconcile repo truth, live slugs, validation state, and immediate publish queue | `docs/review/31a_repo_truth_inventory.md` |
| `31b_builder_hardening_and_validator_gate.md` | Land structural hardening fixes, source-of-truth repairs, and preserve the validator gate | `docs/review/31b_hardening_gate_report.md` |
| `31c_dedicated_notebook_canonical_upgrades.md` | Canonicalize dedicated comparison builders `230`, `240`, and `270` and add their validators | `docs/review/31c_dedicated_upgrades_report.md` |
| `31d_shared_builder_canonical_upgrades.md` | Canonicalize shared-builder notebooks `250`, `260`, `299`, and `399`, plus safe helper extraction | `docs/review/31d_shared_builder_report.md` |
| `31e_publish_verify_and_checkpoint_refresh.md` | Push ready kernels, verify public URLs, and refresh the project checkpoint/docs | `docs/review/31e_publish_verify_report.md` |

Suggested order:

1. Run `31a` first. It is the gatekeeper for actual repo truth.
2. Run `31b` second to preserve or restore structural safety before wider notebook edits.
3. Run `31c` for dedicated-builder upgrades.
4. Run `31d` for shared-builder upgrades after the dedicated pattern is proven.
5. Run `31e` last for Kaggle publication, URL verification, and checkpoint refresh.

## Single-Notebook Improvement Prompts

These prompts are for a deep execution pass on one notebook after it
already exists in the repo. They still require repo context, but the
edit scope stays narrow and centered on one source-of-truth builder and
its direct continuity surfaces.

| File | Target | Mode | Output artifact |
|---|---|---|---|
| `32_claudecode_improve_140_evaluation_mechanics.md` | `140` | Improve the evaluation-mechanics bridge notebook, rebuild it, validate it, and repair direct 140 continuity drift | `docs/review/32_140_improvement_report.md` |
| `33_claudecode_improve_600_results_dashboard.md` | `600` | Improve the video-facing results dashboard, rebuild it, validate it, and repair direct 600 continuity drift | `docs/review/33_600_improvement_report.md` |

Suggested order:

1. Use `32` when `140` already exists and you want one focused pass on the scoring-mechanics explainer between `130` and `299`.
2. Use `33` when you want one focused pass on the dashboard that carries the strongest video, writeup, and live-demo burden in the solution-surfaces section.
3. Prefer `31a` through `31e` for suite-wide publish and hardening work. Prefer `32` or `33` when the work should stay scoped to a single notebook.

Why `33` exists:

- `600` is the fastest judge-facing proof surface in the repo: one CPU notebook that turns upstream evaluation outputs into the charts used in the video, writeup, and demo.

## Corrective Writing And Publishing Prompts

These prompts are for repo-truth correction after notebooks land
locally but the human-facing docs, shared continuity files, or Kaggle
publication state lag behind.

| File | Scope | Mode | Output artifact |
|---|---|---|---|
| `34_claudecode_corrective_writing_and_publish_action.md` | post-170/190/460/540 landing and blocked publish session | Correct stale docs, repair partial-batch continuity drift, publish if auth is available, and verify real Kaggle state | `docs/review/34_corrective_writing_and_publish_report.md` |

Suggested order:

1. Use `34` after builders and validators are green but the repo still mixes local-only notebook landings, stale live-count docs, and unfinished Kaggle publication proof.
2. Prefer `31e` for a clean publish session from already-reconciled repo state. Prefer `34` when the repo must first stop overstating what is live, what is built, and what is still only queued.

Why `34` exists:

- The suite can outrun its own docs. `34` is the corrective pass for that exact failure mode: local builders and validators moved forward, but publication proof and continuity writing did not.

## Ownership of cross-cutting concerns

- Orientation band 000 to 090 (glossary, index, quickstart) is not
  owned by any of the five; it remains in the parent
  `copilot_review_prompt.md`.
- Fine-tuning band 700 to 790 is covered incidentally by prompts 03
  (evaluation of SuperGemma vs stock) and 05 (loading fine-tuned
  weights into demos); no standalone prompt owns it yet.
- The orphan `forge_llm_core_demo.ipynb` is owned by prompt 01.

## Why step of 10, not step of 1

Three-digit IDs step by 10 inside each 100-slot band (000 index,
010, 020, 030, and so on). Step of 10 leaves 9 insertion slots
between siblings so a new notebook drops in without renumbering.
A step-of-1 scheme (001, 002, 003) would force a cascading rename
every time a notebook is added; it is rejected by the shared
discipline layer.
