# Dispatch-all-goals prompts

> Created 2026-05-24, updated 2026-05-24. Prompt sizes for dispatching the 9 PENDING Codex goals without routine checkpoints. All prompts point at the same handoff packages.

## Current no-stop order

Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.

Goal 10 is already DONE in `92f45ac`. Goal 8 must stay after Goal 5 because `goal_08_inline_diff/handoff.md` depends on Goal 5.

## Tiny prompt - paste this first

```text
Read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md. Complete every PENDING goal in this order: 1,6,3,4,5,8,2,9,7. For each goal: read handoff.md, follow sections 5-9, run section 10 verification plus `python scripts/validate_main_kaggle_kernels.py`, verify section 8 acceptance criteria, commit + push only goal-scoped files, mark the handoff and docs/codex/README.md DONE with date + SHA, then continue. Skip Goal 10. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not stage unrelated dirty files. Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, or required destructive-action approval.
```

## `/goal` one-liner

Use this when you want Codex's goal runner to keep working across many goals:

```text
/goal Complete every remaining DueCare Codex goal in C:\Users\amare\OneDrive\Documents\gemma4_comp without routine checkpoints: read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md, then implement Goals 1,6,3,4,5,8,2,9,7 in that order. For each goal read its handoff.md, follow sections 5-9, run section 10 verification plus python scripts/validate_main_kaggle_kernels.py, satisfy section 8 acceptance criteria, stage only goal-scoped files, commit and push, update the handoff status plus docs/codex/README.md with DONE/date/SHA, and continue. Skip Goal 10. Keep the four active/optional root Kaggle kernel.py files working and keep root kaggle/ free of A-* folders and extra 04-* task snapshots; appendix and archived notebooks are otherwise out of scope. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief; do not stage unrelated dirty files. Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, or required destructive-action approval.
```

## Short prompt - use if the tiny prompt drifts

```text
Work through every PENDING goal in docs/codex/ using docs/codex/00_execution_order.md.

Order: Goal 1, Goal 6, Goal 3, Goal 4, Goal 5, Goal 8, Goal 2, Goal 9, Goal 7. Goal 10 is already DONE in 92f45ac.

Loop per goal:
1. Read the goal's handoff.md.
2. Read every file listed in section 5 before editing.
3. Make only the changes listed in sections 6 and 7.
4. Honor section 9 plus docs/codex/00_do_not_break.md.
5. Run every command in section 10.
6. Run the global main-kernel gate: `python scripts/validate_main_kaggle_kernels.py`.
7. Check every section 8 acceptance criterion.
8. Stage only files for this goal, commit, and push.
9. Update the goal handoff status and docs/codex/README.md with DONE, date, and SHA.
10. Continue to the next goal without asking for a checkpoint.

CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not pick up unrelated dirty files or deleted data artifacts. Keep the four active/optional root Kaggle kernel.py files and the Kaggle root layout green; appendix and archived notebooks are otherwise out of scope. Stop only if verification remains red after a focused fix attempt, the main-kernel gate fails, a do-not-break conflict appears, or a destructive action/user approval is required.
```

## Long prompt - fallback for less capable agents

```text
You are working on the gemma4_comp repo (TaylorAmarelTech/gemma4_comp).
Branch: master. Do not switch branches.

Start by reading these files in order:
1. docs/codex/README.md
2. docs/codex/00_do_not_break.md
3. docs/codex/00_kernel_compatibility_gate.md
4. docs/codex/00_execution_order.md

Then complete every PENDING goal in this exact order:
1. Goal 1  - docs/codex/goal_01_polish_button_search/handoff.md
2. Goal 6  - docs/codex/goal_06_template_sample_bundle/handoff.md
3. Goal 3  - docs/codex/goal_03_field_source_preview/handoff.md
4. Goal 4  - docs/codex/goal_04_process_to_knowledge/handoff.md
5. Goal 5  - docs/codex/goal_05_auto_polish_queue/handoff.md
6. Goal 8  - docs/codex/goal_08_inline_diff/handoff.md
7. Goal 2  - docs/codex/goal_02_multi_template_fill/handoff.md
8. Goal 9  - docs/codex/goal_09_inline_vocab_normalize/handoff.md
9. Goal 7  - docs/codex/goal_07_vocab_audit_script/handoff.md

Goal 10 is already DONE in commit 92f45ac. Skip it.

For each goal:
1. Open the goal's handoff.md.
2. Read all files listed in section 5 before making edits.
3. Implement only sections 6 and 7.
4. Enforce section 9 and the global contract in docs/codex/00_do_not_break.md.
5. Run all section 10 verification commands. If one fails, fix the implementation and rerun the relevant command.
6. Run `python scripts/validate_main_kaggle_kernels.py`.
7. Confirm every section 8 acceptance criterion is true.
8. Confirm section 12 out-of-scope items were not touched.
9. Stage only files required for that goal. Do not stage unrelated dirty files, deleted data artifacts, wheel removals, or user changes.
10. Commit with a scoped message that names the goal, then push to origin/master.
11. Update the goal handoff status from PENDING to DONE with the date and commit SHA. Update docs/codex/README.md with the same status. Commit and push the bookkeeping update.
12. Continue to the next goal automatically.

Hard rules:
- CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief.
- Do not rename existing API routes, DOM IDs, activity-log handles, sample artifact paths, or canonical vocabulary entries.
- Do not use innerHTML for user-derived strings.
- Do not combine unrelated goals into one implementation commit.
- Do not alter published Kaggle kernel boot flows.
- Keep `kaggle/01-duecare-exploration-workbench/kernel.py`, `kaggle/02-live-demo/kernel.py`, `kaggle/03-universal-llm-benchmark/kernel.py`, and `kaggle/04-kaggle-community-benchmark/kernel.py` green under `python scripts/validate_main_kaggle_kernels.py`. That same gate must also keep appendix `A-*` folders and extra `04-*` task snapshots out of root `kaggle/`.
- Do not spend time on appendix or archived notebooks unless Taylor explicitly asks.
- Use one goal-scoped commit per implementation. Bookkeeping may be a separate docs commit if needed.
- If local pytest is broken, run the handoff's AST/stdlib checks and say pytest was unavailable; do not claim a full test pass.

Stop only for:
- verification that remains red after a focused fix attempt,
- the main-kernel compatibility gate fails,
- a do-not-break conflict not covered by the handoff,
- required approval for destructive actions or restricted external operations,
- a merge conflict/user change that makes safe continuation impossible.

When all 9 goals are done, post a final summary listing every commit SHA, the verification run for each goal, and any deferred follow-ups.
```

## More copy-paste `/goal` packs

See [`goal_commands/README.md`](goal_commands/README.md) for smaller no-stop packs:

- Full no-stop dispatch
- Reviewer-visible first wave
- Templates deep pack
- Polish pipeline pack
- Vocab and diagnostics pack
