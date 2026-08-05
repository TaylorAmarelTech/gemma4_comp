# 06 - Kaggle surface long-run dispatch

Use this when you want Codex to spend a few hours improving the active Kaggle
surfaces from source without drifting into archived notebooks.

## Goals

Goal 12 -> Goal 13 -> Goal 11 -> Goal 14 -> Goal 15.

Priority:

1. Stabilize and polish the active Kernel 01 workbench pages.
2. Stabilize and polish the active Kernel 02 recording path.
3. Implement the hierarchical Gemma graph pass for Bulk File Review.
4. Improve the optional Universal LLM Benchmark.
5. Improve the optional Kaggle Community Benchmark.

Goal 11 is larger than the page-polish goals. If it cannot be fully completed
inside the run, ship a verified, goal-scoped slice only if the slice has tests,
does not weaken deterministic extraction, and the handoff clearly lists the
remaining acceptance criteria. Do not mark Goal 11 DONE unless all of its
acceptance criteria are satisfied.

## Copy-paste `/goal` command

```text
/goal Run a multi-hour source-first Kaggle surface improvement pass in <repo-root> without routine checkpoints. Work on master and do not switch branches. Start by reading docs/codex/README.md, docs/codex/00_do_not_break.md, docs/codex/00_kernel_compatibility_gate.md, docs/codex/00_execution_order.md, and docs/codex/01_next_phase_kaggle_surface_goals.md. Then work in this order: Goal 12, Goal 13, Goal 11, Goal 14, Goal 15. For each goal, open its handoff.md, read every section 5 file before editing, implement only the scoped changes in sections 6-7, honor section 9 plus docs/codex/00_do_not_break.md, run all section 10 verification commands that are available, run python scripts/validate_main_kaggle_kernels.py, and if the goal touches Kernel 01/02 pages or benchmark kernels also run py -3.12 scripts/validate_kaggle_page_sources.py. Preserve the root kaggle/ layout: active 01 and 02, optional 03 and 04, no A-* folders in root, no extra root 04-* task snapshots. Appendix and archived notebooks under kaggle/_archive are out of scope unless Taylor explicitly asks. Do not stage unrelated dirty files, deleted generated/data artifacts, wheel removals, or user changes. Keep routes, DOM IDs, activity-log handles, localStorage keys, sample artifact paths, and Kaggle kernel boot tokens stable. Do not add per-page model-loading popovers; use the shared workbench chrome. Do not imply that the current gemma_case_brief is per-document, per-page, or per-paragraph analysis. For Goal 11, implement a budgeted hierarchical Gemma graph pass with reviewable node/edge provenance across folder, document, page, paragraph/chunk, table row, media item, person/case, and rollup levels; deterministic extraction must run first and remain the fallback. If Goal 11 is too large for one run, commit only a verified slice and leave the handoff PENDING with exact remaining acceptance criteria. For Goals 14 and 15, keep optional benchmark kernels dependency-tolerant, local-preview safe, and free of live paid API calls during local verification. Commit and push goal-scoped implementation changes when verification is green enough for the scope, then update the goal handoff and docs/codex/README.md with DONE/date/SHA only for goals whose acceptance criteria are fully met. Stop only for unrecoverable verification failure, main-kernel gate failure, page-source gate failure, a do-not-break conflict, required approval for destructive/restricted operations, or a user change that makes safe continuation impossible. At the end, report completed goals, commit SHAs, verification commands, any blocked tests or missing dependencies, and remaining next steps.
```

## Expected output

At the end, Codex should report:

- Completed goals and commit SHA for each fully completed goal
- Any partial Goal 11 slice and the remaining acceptance criteria
- Verification commands run for each goal
- Main-kernel gate and page-source gate results
- Tests that were blocked by local environment dependencies
- Files intentionally left uncommitted, if any

## Preflight notes

- If the repo already has uncommitted setup files for Goals 12-15, inspect and
  preserve them. Do not revert them.
- If local pytest fails before collection because of missing packages such as
  `typing_extensions`, record the exact import failure, run the available
  stdlib gates, and do not claim a full test pass.
- If a live Kaggle, Cloudflare, or paid-model check would be required, leave it
  as an explicit manual verification item instead of blocking local progress.
