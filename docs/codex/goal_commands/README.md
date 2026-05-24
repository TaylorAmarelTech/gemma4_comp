# Goal command series

> Created 2026-05-24. Copy-paste `/goal` commands for dispatching multiple DueCare Codex handoff goals in one no-stop session.

These are agent commands, not shell commands. Paste one whole block into Codex when you want it to keep working across several goal handoffs without pausing after each one.

## Shared rules

Every command in this directory assumes:

- Repo: `C:\Users\amare\OneDrive\Documents\gemma4_comp`
- Branch: `master`
- Read first: `docs/codex/README.md`, `docs/codex/00_do_not_break.md`, `docs/codex/00_kernel_compatibility_gate.md`, and `docs/codex/00_execution_order.md`
- Skip Goal 10 because it is already DONE in `92f45ac`
- Use one implementation commit per goal
- Push after each goal commit
- Update the goal `handoff.md` status and `docs/codex/README.md` after completion
- Run `python scripts/validate_main_kaggle_kernels.py` before committing each goal
- Keep the five non-archived main Kaggle `kernel.py` files green; appendix and archived notebooks are out of scope unless Taylor explicitly says otherwise
- `CLAUDE.md` may be edited only for reconciliation of completed goal state, kernel constraints, or operating brief
- Do not stage unrelated dirty files, deleted generated/data artifacts, or user changes
- Stop only for unrecoverable verification failure, main-kernel gate failure, do-not-break conflict, destructive-action approval, or a user change that makes safe continuation impossible

## Pick a pack

| Pack | File | Goals | Use when |
|---|---|---|---|
| Full no-stop dispatch | [`01_full_no_stop.md`](01_full_no_stop.md) | 1, 6, 3, 4, 5, 8, 2, 9, 7 | You want every remaining handoff handled in dependency order |
| Reviewer-visible first wave | [`02_reviewer_visible_first_wave.md`](02_reviewer_visible_first_wave.md) | 1, 6, 3, 4 | You want the strongest recording/judge walkthrough improvements first |
| Templates deep pack | [`03_templates_deep_pack.md`](03_templates_deep_pack.md) | 6, 3, 2 | You want templates.html to become a full sample + preview + batch-fill flow |
| Polish pipeline pack | [`04_polish_pipeline_pack.md`](04_polish_pipeline_pack.md) | 1, 5, 8 | You want polish UX across manual, queued, and inline-diff flows |
| Vocab and diagnostics pack | [`05_vocab_diagnostics_pack.md`](05_vocab_diagnostics_pack.md) | 9, 7 | You want canonical vocabulary cleanup plus read-only auditing |

## Dependency notes

- Goal 8 comes after Goal 5. Do not paste a command that runs Goal 8 before Goal 5.
- Goal 2 comes after Goals 6 and 3. It can be implemented earlier, but the selector and tests are better after the sample bundle and dry-run preview are stable.
- Goal 7 is read-only diagnostics; run it after vocabulary-normalization work so the report reflects the current code.
