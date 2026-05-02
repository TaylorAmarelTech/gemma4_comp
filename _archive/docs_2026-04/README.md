# Archived docs (2026-04-18 cleanup pass)

These documents belong to completed phases of the project. They are
archived rather than deleted so that decisions and justifications made
along the way are still recoverable, but future AI sessions stop
treating them as current-state tooling.

## Top-level plans archived

| Doc                                     | Purpose                                                                                                          | Why archived                                                                                                               |
|-----------------------------------------|------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| `notebook_renumbering_plan.md`          | Step-by-step plan to move from `00`/`00a`/`00b` IDs to the hundreds-band `100`/`110`/`120` scheme.              | Renumbering landed 2026-04-17. The plan is now history; the live layout is in `docs/project_phases.md` and the index.      |
| `the_forge.md`                          | 2026-04-11 "agentic universal safety harness" north-star vision. Written at the user's request to explore.        | Not adopted as the execution plan; the current plan is `docs/project_phases.md` + `docs/architecture.md`.                  |
| `copilot_review_prompt.md`              | Prompt template handed to Copilot GPT 5.4x for a one-time architecture + curriculum review pass.                  | Review completed 2026-04-15. The report is archived alongside under `review/`.                                             |
| `publishing_plan_jailbreak_family.md`   | Command sequence to publish the 181-189 jailbreak notebook family.                                                | Slug assumptions (`duecare-18N-*`) are now handled by `scripts/_public_slugs.py`; publish runs through `publish_kaggle.py`. |

## Review reports archived (docs/review/)

| Doc                                                   | Purpose                                                                                                     |
|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `31a_repo_truth_inventory.md`                         | Checkpoint 31-series inventory of the suite.                                                                |
| `31b_hardening_gate_report.md`                        | Checkpoint 31 hardening-gate pass.                                                                          |
| `31c_dedicated_upgrades_report.md`                    | Checkpoint 31 per-notebook upgrade pass.                                                                    |
| `31d_shared_builder_report.md`                        | Checkpoint 31 shared-builder refactor report.                                                               |
| `31e_publish_verify_report.md`                        | Checkpoint 31 publish + verification pass.                                                                  |
| `32_140_improvement_report.md`                        | 32-series editorial improvement on notebook 140.                                                            |
| `33_600_improvement_report.md`                        | 33-series editorial improvement on notebook 600.                                                            |
| `100-290_exploration_and_basic_eval.md`               | Band-level review of 100-290 notebooks; references pre-renumber kernel dirs (`duecare_00_*`, `duecare_01_*`).|
| `300-390_data_pipeline.md`                            | Same for 300-390; references pre-renumber kernel dirs.                                                      |
| `notebook_publish_report.md`                          | One-time publish-attempt log.                                                                               |
| `push_with_fallback_report.md`                        | One-time fallback-push-attempt log.                                                                         |
| `notebook_quality_report.md`                          | 2026-04-15 quality snapshot; superseded by `docs/CHECKPOINT_2026-04-18.md` and the current suite state.      |
| `_audit_raw.json`                                     | Raw JSON audit output behind one of the reports.                                                            |

If you need to re-run any of these review passes, write a fresh report
with a current timestamp rather than updating an archived one.
