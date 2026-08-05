# 03 - Templates deep pack

Use this when templates.html is the focus and you want sample loading, pre-generate field visibility, and batch template fill in one run.

## Goals

Goal 6 -> Goal 3 -> Goal 2.

Do not run Goal 2 before Goals 6 and 3 unless you intentionally want a harder refactor.

## Copy-paste `/goal` command

```text
/goal Complete the DueCare templates deep pack in <repo-root> without routine checkpoints. Work on master. Read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md first. Then implement Goal 6, Goal 3, and Goal 2 in that order. For each goal: read the handoff.md, read every section 5 file before editing, implement sections 6-7, honor section 9 and docs/codex/00_do_not_break.md, run section 10 verification plus python scripts/validate_main_kaggle_kernels.py, satisfy section 8 acceptance criteria, stage only goal-scoped files, commit and push, update the goal status plus docs/codex/README.md with DONE/date/SHA, and continue. Keep Goal 2's /api/templates/fill-batch additive; do not break /api/templates/fill. Keep the four active/optional root Kaggle kernel.py files working and keep root kaggle/ free of A-* folders and extra 04-* task snapshots; appendix and archived notebooks are otherwise out of scope. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not stage unrelated dirty files. Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, required destructive-action approval, or a user change that blocks safe continuation.
```

## Expected checks

Codex should at minimum run the structural checks from each handoff and any affected chat package tests named in the handoff.
