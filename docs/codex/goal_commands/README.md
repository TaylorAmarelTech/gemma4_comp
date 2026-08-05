# Goal command series

> Created 2026-05-24. Copy-paste `/goal` commands for dispatching multiple DueCare Codex handoff goals in one no-stop session.

These are agent commands, not shell commands. Paste one whole block into Codex when you want it to keep working across several goal handoffs without pausing after each one.

## Shared rules

All command packs assume:

- Repo: `<repo-root>`
- Branch: `master`
- Read first: `docs/codex/README.md`, `docs/codex/00_do_not_break.md`, `docs/codex/00_kernel_compatibility_gate.md`, and `docs/codex/00_execution_order.md`
- Keep the four active/optional root Kaggle `kernel.py` files and the Kaggle root layout green; appendix and archived notebooks are out of scope unless Taylor explicitly says otherwise
- `CLAUDE.md` may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief
- Do not stage unrelated dirty files, deleted generated/data artifacts, or user changes
- Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, destructive-action approval, or a user change that makes safe continuation impossible

Original per-goal packs also assume:

- Skip Goal 10 because it is already DONE in `92f45ac`
- Use one implementation commit per goal
- Push after each goal commit
- Update the goal `handoff.md` status and `docs/codex/README.md` after completion
- Run `python scripts/validate_main_kaggle_kernels.py` before committing each goal

Later long-run packs (`07` through `13`) define their own commit cadence,
validation scope, and stopping rules inside each command file. The specific
command file wins when it is stricter or more current than this shared summary.

## Pick a pack

| Pack | File | Goals | Use when |
|---|---|---|---|
| Full no-stop dispatch | [`01_full_no_stop.md`](01_full_no_stop.md) | 1, 6, 3, 4, 5, 8, 2, 9, 7 | You want every remaining handoff handled in dependency order |
| Reviewer-visible first wave | [`02_reviewer_visible_first_wave.md`](02_reviewer_visible_first_wave.md) | 1, 6, 3, 4 | You want the strongest recording/judge walkthrough improvements first |
| Templates deep pack | [`03_templates_deep_pack.md`](03_templates_deep_pack.md) | 6, 3, 2 | You want templates.html to become a full sample + preview + batch-fill flow |
| Polish pipeline pack | [`04_polish_pipeline_pack.md`](04_polish_pipeline_pack.md) | 1, 5, 8 | You want polish UX across manual, queued, and inline-diff flows |
| Vocab and diagnostics pack | [`05_vocab_diagnostics_pack.md`](05_vocab_diagnostics_pack.md) | 9, 7 | You want canonical vocabulary cleanup plus read-only auditing |
| Kaggle surface long-run dispatch | [`06_kaggle_surface_long_run.md`](06_kaggle_surface_long_run.md) | 12, 13, 11, 14, 15 | You want a few-hour source-first pass over the active 01/02 pages, hierarchical Gemma graph, and optional benchmark kernels |
| Verification and showcase hardening | [`07_verification_showcase_hardening.md`](07_verification_showcase_hardening.md) | post-Goals 11-15 | You want a clean Python env, runtime smoke tests, manual path tracing, and Gemma 4 ecosystem/design polish without exceeding `/goal` length |
| Pages and number hardening | [`08_pages_number_hardening.md`](08_pages_number_hardening.md) | same-day launch polish | You need GitHub Pages enabled/deploying ASAP while removing fragile public magic numbers and keeping Kaggle gates green |
| Major-case multi-hour research benchmark expansion | [`09_major_case_research_benchmark_expansion.md`](09_major_case_research_benchmark_expansion.md) | benchmark capability growth | You want a 3-8 hour no-stop pass with web research, casefile-derived dimensions, scenario mixing, knowledge facts, repeated commits, and strict private-data safety |
| Global research corpus + multi-turn benchmark expansion | [`10_global_research_corpus_multiturn_benchmark.md`](10_global_research_corpus_multiturn_benchmark.md) | autonomous long-run capability growth | You want an 8-24+ hour run that profiles 1,000+ public sources, continuously improves dimensions/facts/prompts, adds multi-turn conversations, and resumes without human re-planning |
| Iterative branching research frontier | [`11_iterative_branching_research_frontier.md`](11_iterative_branching_research_frontier.md) | tool-assisted source-frontier branching and repeated capability loops | You want a 24-72 hour run that first searches for better search/crawl/extraction/spider tools and then branches from every useful source/profile/fact/gap into deeper dorks, more source profiles, knowledge objects, dimensions, tests, prompts, conversations, and pushed resume states |
| UI/UX + backend + research quality loop | [`12_ui_ux_backend_research_quality_loop.md`](12_ui_ux_backend_research_quality_loop.md) | workflow-driven quality loop | You want a long autonomous pass across workbench UI clarity, backend wiring, research-frontier tools, and harness-lift judging quality |
| Project bible continuation loop | [`13_project_bible_continuation.md`](13_project_bible_continuation.md) | current-state continuation | You want Claude Code / Codex to resume from the project bible, keep improving safe handoff/review-gate/domain-planning gaps, and avoid restarting the paused judging engine |
| GPT-5.6 SOL training-data and Kaggle flywheel | [`14_training_dataset_kaggle_flywheel_gpt56.md`](14_training_dataset_kaggle_flywheel_gpt56.md) | training-data, grading, Kaggle datasets, and notebooks | You want a paste-ready continuation prompt for turning response data and multi-perspective synthetic data into validated SFT, preference, reward, and Kaggle-ready artifacts |
| GPT-5.6 SOL Kaggle hackathon showcase | [`15_kaggle_hackathon_showcase_gpt56.md`](15_kaggle_hackathon_showcase_gpt56.md) | Kaggle hackathon polish, visual notebooks, dataset presentation | You want a paste-ready continuation prompt for maintaining public Kaggle datasets and notebooks as professional, reviewer-friendly, educational releases while keeping future candidates gated |

## Dependency notes

- Goal 8 comes after Goal 5. Do not paste a command that runs Goal 8 before Goal 5.
- Goal 2 comes after Goals 6 and 3. It can be implemented earlier, but the selector and tests are better after the sample bundle and dry-run preview are stable.
- Goal 7 is read-only diagnostics; run it after vocabulary-normalization work so the report reflects the current code.
- For Kaggle surface work, run Goal 12 before Goal 13, then Goal 11. Goals 14 and 15 are optional benchmark improvements after the active recording/workbench path is stable.
