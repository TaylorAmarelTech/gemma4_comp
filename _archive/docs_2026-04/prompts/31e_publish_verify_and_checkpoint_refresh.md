# 31e: DueCare publish, verify, and checkpoint refresh

Date captured: 2026-04-16
Audience: Claude Code or GPT-5.4 running inside this repo.

This is stage 5 of the 31-series. Run it only after `31d` has produced
`docs/review/31d_shared_builder_report.md`.

This stage is the publication and truth-refresh pass. It pushes the
ready kernels in the safest order, handles slug and cap fallout without
guessing, verifies live URLs, and refreshes the repo checkpoint docs so
the next operator starts from actual live state.

## Required inputs

Read these first:

1. `docs/review/31a_repo_truth_inventory.md`
2. `docs/review/31b_hardening_gate_report.md`
3. `docs/review/31c_dedicated_upgrades_report.md`
4. `docs/review/31d_shared_builder_report.md`
5. `docs/prompts/30_project_checkpoint.md`
6. `docs/prompts/README.md`
7. `docs/current_kaggle_notebook_state.md`
8. `scripts/align_kaggle_kernel_metadata.py`
9. `scripts/verify_kaggle_urls.py`
10. `scripts/kaggle_live_slug_map.json`

Also inspect kernel metadata for every kernel you intend to push in
this stage.

## Required output artifact

Create or update `docs/review/31e_publish_verify_report.md` with these
sections only:

1. `Pushed kernels`
2. `Status results`
3. `Live URL verification`
4. `Docs refreshed`
5. `Remaining blockers`
6. `Next exact commands`

## Execution rules

- Never pretend a push succeeded if Kaggle blocked it.
- Probe the cap before burning pushes.
- Align metadata for touched kernels before each push batch.
- If `Notebook not found` happens twice for the same kernel, change the
  builder `KERNEL_ID` once, rebuild once, retry once, and then record
  the resulting live slug everywhere it matters.
- If a kernel returns `ERROR`, fetch logs and report the first failing
  cell or step.
- Refresh checkpoint docs after publication, not before.

## Required tasks

1. Align metadata for the ready queue reported by `31a` through `31d`.
2. Probe Kaggle status with an already-live kernel before pushing.
3. Push in this order unless a report from an earlier stage justifies a
   different queue:
   - previously blocked queue from `31a`
   - dedicated-builder queue from `31c`
   - shared-builder queue from `31d`
4. Verify each pushed kernel with `kaggle kernels status`.
5. Run `python scripts/verify_kaggle_urls.py` after the publish pass.
6. Update `docs/prompts/30_project_checkpoint.md` and
   `docs/prompts/README.md` anywhere live state or queue assumptions
   changed.
7. If live public URLs changed, update the affected references in the
   writeup, video notes, index, glossary, and section conclusions.
8. Write the artifact with exact remaining commands if the cap blocked
   the full queue.

## Gate to leave 31e

- `docs/review/31e_publish_verify_report.md` exists.
- The current checkpoint docs match actual live or blocked state.
- Remaining blockers are stated as facts, not guesses.

## Final response format

Return a single markdown document with these sections only:

1. `Publish results`
2. `Verification results`
3. `Checkpoint and doc refresh`
4. `Remaining blockers`
5. `Next exact commands`

Do not ask follow-up questions.