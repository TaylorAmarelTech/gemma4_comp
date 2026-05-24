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
- [`00_kernel_compatibility_gate.md`](00_kernel_compatibility_gate.md) — global verification gate for the five non-archived Kaggle `kernel.py` files. Run it before committing every goal.
- [`dispatch_all_goals.md`](dispatch_all_goals.md) — prompt sizes for completing every remaining PENDING goal without routine checkpoints.
- [`goal_commands/`](goal_commands/README.md) — copy-paste `/goal` command packs for full, reviewer-visible, templates, polish, and vocabulary/diagnostics runs.

## Goal directory map

| # | Directory | Status | Summary |
|---|---|---|---|
| 1 | [`goal_01_polish_button_search/`](goal_01_polish_button_search/handoff.md) | PENDING | Add "Polish further (Gemma 4)" button to search.html draft cards |
| 2 | [`goal_02_multi_template_fill/`](goal_02_multi_template_fill/handoff.md) | PENDING | Fill multiple complaint templates from one bundle in one batch |
| 3 | [`goal_03_field_source_preview/`](goal_03_field_source_preview/handoff.md) | PENDING | Show field-source colors on templates.html BEFORE Generate is clicked |
| 4 | [`goal_04_process_to_knowledge/`](goal_04_process_to_knowledge/handoff.md) | PENDING | One-click "Draft as knowledge fact" on every typed edge in process.html |
| 5 | [`goal_05_auto_polish_queue/`](goal_05_auto_polish_queue/handoff.md) | PENDING | Checkbox that auto-polishes every new draft |
| 6 | [`goal_06_template_sample_bundle/`](goal_06_template_sample_bundle/handoff.md) | PENDING | Synthetic case bundle + buttons so templates.html round-trips in 30s |
| 7 | [`goal_07_vocab_audit_script/`](goal_07_vocab_audit_script/handoff.md) | PENDING | Stdlib script that audits saved envelopes against canonical vocab |
| 8 | [`goal_08_inline_diff/`](goal_08_inline_diff/handoff.md) | PENDING | Word-level inline diff in the polish panel |
| 9 | [`goal_09_inline_vocab_normalize/`](goal_09_inline_vocab_normalize/handoff.md) | PENDING | Apply canonical vocab normalization to graph-chat synthesis free-text |
| 10 | [`goal_10_polish_e2e_tests/`](goal_10_polish_e2e_tests/handoff.md) | **DONE 2026-05-24 (`92f45ac`)** | End-to-end tests for /api/knowledge/polish-envelope |

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

## Why the protective contract matters

Kaggle has a published notebook (`kaggle/01-duecare-exploration-workbench/kernel.py`) with documented run instructions. Reviewers may have bookmarked deep-links to specific pages, copied the kernel.py contents into their own Kaggle account, or invoked specific endpoints from external tools. Any improvement that breaks an existing route, renames a DOM ID, or changes the run instructions silently breaks the published submission.

The `00_do_not_break.md` contract enumerates exactly what's load-bearing so Codex always knows what it can and cannot touch.

## Adding a new goal

1. Create `docs/codex/goal_NN_short_slug/handoff.md`.
2. Use the 12-section template (any existing goal handoff works as scaffolding).
3. Link to `00_do_not_break.md` in the "Do-not-break checklist" section.
4. Add a row to the goal-directory map above.
5. Update `00_execution_order.md` if the new goal has dependencies.
