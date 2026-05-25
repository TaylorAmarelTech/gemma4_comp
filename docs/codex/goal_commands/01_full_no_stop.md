# 01 - Full no-stop dispatch

Use this when you want every remaining Codex handoff goal completed in dependency order.

## Goals

Goal 1 -> Goal 6 -> Goal 3 -> Goal 4 -> Goal 5 -> Goal 8 -> Goal 2 -> Goal 9 -> Goal 7.

Goal 10 is already done in `92f45ac`.

## Copy-paste `/goal` command

```text
/goal Complete every remaining DueCare Codex handoff goal in C:\Users\amare\OneDrive\Documents\gemma4_comp without routine checkpoints. Work on master. First read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md. Then implement Goals 1,6,3,4,5,8,2,9,7 in that exact order. For each goal: open its handoff.md, read all section 5 files before editing, implement sections 6-7, honor section 9 and docs/codex/00_do_not_break.md, run every section 10 verification command plus python scripts/validate_main_kaggle_kernels.py, prove every section 8 acceptance criterion, confirm section 12 stayed out of scope, stage only goal-scoped files, commit with the goal number in the message, push to origin/master, update that goal's handoff status plus docs/codex/README.md with DONE/date/SHA, commit and push the bookkeeping if separate, then continue automatically to the next goal. Skip Goal 10. Keep the four active/optional root Kaggle kernel.py files working and keep root kaggle/ free of A-* folders and extra 04-* task snapshots; appendix and archived notebooks are otherwise out of scope. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not stage unrelated dirty files, deleted generated/data artifacts, wheel removals, or user changes. Stop only for unrecoverable verification failure, main-kernel gate failure, a do-not-break conflict, required destructive-action approval, or a user change that makes safe continuation impossible.
```

## Expected output

At the end, Codex should report:

- Commit SHA for each completed goal
- Verification command(s) run for each goal
- Main-kernel gate result for each goal
- Any goal not completed and the exact blocking reason
