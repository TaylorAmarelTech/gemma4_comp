# docs/codex/ — Codex handoff packages

> Created 2026-05-24 after the safe-text / standardize / polish layer landed (commits 84695fc through 92f45ac). One subdirectory per pickable improvement goal.

## What this directory is

A reference set Taylor pastes into Codex sessions to dispatch focused improvement work without losing context. Each `goal_NN_*/` directory is a self-contained handoff: scope, current state, target state, files to read, files to modify, files to create, acceptance criteria, do-not-break checklist, verification commands, and a copy-paste prompt.

The goals come from [`docs/codex_followup_goals.md`](../codex_followup_goals.md), expanded with the full handoff content Codex needs.

## How to use it

1. Pick a goal that matches what's painful right now (or follow [00_execution_order.md](00_execution_order.md)).
2. Open the goal's `handoff.md`.
3. Read the "Codex prompt" block at the bottom — that's what you paste.
4. Codex reads the named files, makes the change, and runs the verification commands.
5. Review the diff before merging.

For no-stop runs across multiple goals, use [`dispatch_all_goals.md`](dispatch_all_goals.md) or the copy-paste `/goal` packs in [`goal_commands/`](goal_commands/README.md).

## Foundation documents (apply to every goal)

- [`00_do_not_break.md`](00_do_not_break.md) — **mandatory contract**. Lists the kernels, endpoints, DOM IDs, activity-log handles, sample artifacts, and instructions Codex must not break. Every per-goal handoff links to this. If a proposed change would violate it, the change gets re-scoped.
- [`00_execution_order.md`](00_execution_order.md) — suggested order + dependencies between goals. Goal 10 is already done (commit `92f45ac`); Goal 1 is the natural next pickup since it reuses the contract Goal 10 locked in.
- [`00_kernel_compatibility_gate.md`](00_kernel_compatibility_gate.md) — global verification gate for the Kaggle root layout plus the four active/optional root `kernel.py` files. Run it before committing every goal.
- [`01_next_phase_kaggle_surface_goals.md`](01_next_phase_kaggle_surface_goals.md) — source review, next goal set, and verification matrix for cleaning the active `01`/`02` pages and improving the optional `03`/`04` benchmark kernels.
- [`dispatch_all_goals.md`](dispatch_all_goals.md) — prompt sizes for completing every remaining PENDING goal without routine checkpoints.
- [`goal_commands/`](goal_commands/README.md) — copy-paste `/goal` command packs for full, reviewer-visible, templates, polish, vocabulary/diagnostics, and Kaggle surface long-run dispatches.

## Goal directory map

| # | Directory | Status | Summary |
|---|---|---|---|
| 1 | [`goal_01_polish_button_search/`](goal_01_polish_button_search/handoff.md) | **DONE 2026-05-24 (`713444e`)** | Add "Polish further (Gemma 4)" button to search.html draft cards |
| 2 | [`goal_02_multi_template_fill/`](goal_02_multi_template_fill/handoff.md) | **DONE 2026-05-24 (`1c0d3ff`)** | Fill multiple complaint templates from one bundle in one batch |
| 3 | [`goal_03_field_source_preview/`](goal_03_field_source_preview/handoff.md) | **DONE 2026-05-24 (`8294b5a`)** | Show field-source colors on templates.html BEFORE Generate is clicked |
| 4 | [`goal_04_process_to_knowledge/`](goal_04_process_to_knowledge/handoff.md) | **DONE 2026-05-24 (`fc7d53f`)** | One-click "Draft as knowledge fact" on every typed edge in process.html |
| 5 | [`goal_05_auto_polish_queue/`](goal_05_auto_polish_queue/handoff.md) | **DONE 2026-05-24 (`2c7cbd1`)** | Checkbox that auto-polishes every new draft |
| 6 | [`goal_06_template_sample_bundle/`](goal_06_template_sample_bundle/handoff.md) | **DONE 2026-05-24 (`61c076e`)** | Synthetic case bundle + buttons so templates.html round-trips in 30s |
| 7 | [`goal_07_vocab_audit_script/`](goal_07_vocab_audit_script/handoff.md) | PENDING | Stdlib script that audits saved envelopes against canonical vocab |
| 8 | [`goal_08_inline_diff/`](goal_08_inline_diff/handoff.md) | **DONE 2026-05-24 (`5738729`)** | Word-level inline diff in the polish panel |
| 9 | [`goal_09_inline_vocab_normalize/`](goal_09_inline_vocab_normalize/handoff.md) | PENDING | Apply canonical vocab normalization to graph-chat synthesis free-text |
| 10 | [`goal_10_polish_e2e_tests/`](goal_10_polish_e2e_tests/handoff.md) | **DONE 2026-05-24 (`92f45ac`)** | End-to-end tests for /api/knowledge/polish-envelope |
| 11 | [`goal_11_hierarchical_gemma_graph/`](goal_11_hierarchical_gemma_graph/handoff.md) | PENDING | Budgeted Gemma node/edge passes across folder, document, page, chunk, media, person, case, and rollup levels |
| 12 | [`goal_12_kaggle_01_page_polish/`](goal_12_kaggle_01_page_polish/handoff.md) | PENDING | Source-first cleanup of the active Kernel 01 workbench pages and page-source regression gate |
| 13 | [`goal_13_kaggle_02_recording_polish/`](goal_13_kaggle_02_recording_polish/handoff.md) | PENDING | Recording-path polish for Kernel 02 `/start`, `/slides`, `/slides/setup`, and cached replay |
| 14 | [`goal_14_universal_llm_benchmark_upgrade/`](goal_14_universal_llm_benchmark_upgrade/handoff.md) | PENDING | Multi-target comparison/report upgrade for the Universal LLM Benchmark |
| 15 | [`goal_15_kaggle_community_benchmark_maturity/`](goal_15_kaggle_community_benchmark_maturity/handoff.md) | PENDING | Kaggle Community Benchmark local-preview, coverage, and registration-proof maturity |

## Handoff template

Every goal handoff follows the same 12 sections so you and Codex can scan them quickly:

1. **Goal** — one sentence
2. **Why it matters** — the user story behind the change
3. **Current state** — what exists today
4. **Target state** — what should exist after
5. **Files to read first** — Codex's required prep
6. **Files to modify** — table of path → what changes
7. **Files to create** — table of path → purpose
8. **Acceptance criteria** — numbered, testable
9. **Do-not-break checklist** — kernel-protective guards specific to this goal
10. **Verification commands** — paste-ready, all stdlib where possible
11. **The Codex prompt** — the copy-paste block to hand off
12. **Out of scope** — explicit non-goals so Codex doesn't sprawl

In addition to each goal's section 10 commands, every goal run should execute the global main-kernel gate:

```bash
python scripts/validate_main_kaggle_kernels.py
```

For goals that touch Kernel 01/02 pages or the optional benchmark kernels, also
run the source-level page gate:

```bash
py -3.12 scripts/validate_kaggle_page_sources.py
```

## Why the protective contract matters

Kaggle has a published notebook (`kaggle/01-duecare-exploration-workbench/kernel.py`) with documented run instructions. Reviewers may have bookmarked deep-links to specific pages, copied the kernel.py contents into their own Kaggle account, or invoked specific endpoints from external tools. Any improvement that breaks an existing route, renames a DOM ID, or changes the run instructions silently breaks the published submission.

The `00_do_not_break.md` contract enumerates exactly what's load-bearing so Codex always knows what it can and cannot touch.

## Adding a new goal

1. Create `docs/codex/goal_NN_short_slug/handoff.md`.
2. Use the 12-section template (any existing goal handoff works as scaffolding).
3. Link to `00_do_not_break.md` in the "Do-not-break checklist" section.
4. Add a row to the goal-directory map above.
5. Update `00_execution_order.md` if the new goal has dependencies.
