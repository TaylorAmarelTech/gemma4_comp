# 05 - Vocab and diagnostics pack

Use this when canonical vocabulary consistency and saved-envelope auditing are the focus.

## Goals

Goal 9 -> Goal 7.

Goal 9 changes inline vocabulary normalization. Goal 7 is a read-only audit script, so running it second makes the audit reflect the latest normalizer behavior.

## Copy-paste `/goal` command

```text
/goal Complete the DueCare vocab and diagnostics pack in C:\Users\amare\OneDrive\Documents\gemma4_comp without routine checkpoints. Work on master. Read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md first. Then implement Goal 9 and Goal 7 in that order. For each goal: read handoff.md, read every section 5 file before editing, implement sections 6-7, honor section 9 and docs/codex/00_do_not_break.md, run all section 10 verification commands plus python scripts/validate_main_kaggle_kernels.py, satisfy section 8 acceptance criteria, stage only goal-scoped files, commit and push, update the goal handoff plus docs/codex/README.md with DONE/date/SHA, and continue automatically. Keep canonical vocabulary entries backward-compatible: append or alias, never rename/remove. Goal 7's script must be read-only and pure stdlib. Keep the four active/optional root Kaggle kernel.py files working and keep root kaggle/ free of A-* folders and extra 04-* task snapshots; appendix and archived notebooks are otherwise out of scope. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not stage unrelated dirty files. Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, required destructive-action approval, or a user change that blocks safe continuation.
```

## Expected checks

Codex should show the inline normalization tests for Goal 9 and a read-only dry run or structural check for `scripts/audit_knowledge_vocabularies.py` from Goal 7.
