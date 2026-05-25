# 04 - Polish pipeline pack

Use this when the polish workflow is the focus across search, auto-polish, and inline diff.

## Goals

Goal 1 -> Goal 5 -> Goal 8.

Goal 8 depends on Goal 5. Keep this order.

## Copy-paste `/goal` command

```text
/goal Complete the DueCare polish pipeline pack in C:\Users\amare\OneDrive\Documents\gemma4_comp without routine checkpoints. Work on master. Read docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, and docs/codex/00_execution_order.md first. Then implement Goal 1, Goal 5, and Goal 8 in that order. For each goal: read handoff.md, read all section 5 files before editing, implement sections 6-7, honor section 9 and the global do-not-break contract, run section 10 verification plus python scripts/validate_main_kaggle_kernels.py, satisfy section 8 acceptance criteria, stage only goal-scoped files, commit and push, update the handoff and docs/codex/README.md status with DONE/date/SHA, and continue automatically. Use existing polish endpoint contracts and dcGemmaStats buckets exactly as the handoffs specify. Keep the four active/optional root Kaggle kernel.py files working and keep root kaggle/ free of A-* folders and extra 04-* task snapshots; appendix and archived notebooks are otherwise out of scope. CLAUDE.md may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief. Do not use innerHTML for user-derived strings. Do not stage unrelated dirty files or generated/data deletions. Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, required destructive-action approval, or a user change that blocks safe continuation.
```

## Expected checks

Goal 1 and Goal 5 should keep the polish endpoint response shape pinned by `packages/duecare-llm-chat/tests/test_polish_envelope.py`. Goal 8 must preserve safe text rendering.
