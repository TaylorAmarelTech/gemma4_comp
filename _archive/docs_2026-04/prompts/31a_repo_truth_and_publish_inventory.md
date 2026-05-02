# 31a: DueCare repo truth and publish inventory

Date captured: 2026-04-16
Audience: Claude Code or GPT-5.4 running inside this repo.

This is stage 1 of the 31-series. Run this before `31b` through `31e`.
Its job is to establish the actual current truth of the notebook suite,
the live/public slug state, the local source-of-truth ownership map, and
the exact push-ready versus edit-first queue.

Do not stop at a prose summary. Reconcile the repo against the current
checkpoint docs and leave a written handoff artifact that the next stage
can consume directly.

## Required inputs

Read these first:

1. `docs/prompts/30_project_checkpoint.md`
2. `docs/prompts/29_verified_continuation_and_improvement_plan.md`
3. `docs/prompts/README.md`
4. `/memories/repo/kaggle_notebooks.md`
5. `scripts/validate_notebooks.py`
6. `scripts/kaggle_live_slug_map.json`
7. `scripts/build_index_notebook.py`
8. `scripts/build_notebook_005_glossary.py`
9. `scripts/build_notebook_010_quickstart.py`
10. `scripts/build_notebook_130_prompt_corpus_exploration.py`
11. `scripts/build_section_conclusion_notebooks.py`
12. `scripts/align_kaggle_kernel_metadata.py`

Also inspect kernel metadata for at least these notebooks:

1. `kaggle/kernels/duecare_000_index/kernel-metadata.json`
2. `kaggle/kernels/duecare_005_glossary/kernel-metadata.json`
3. `kaggle/kernels/duecare_130_prompt_corpus_exploration/kernel-metadata.json`
4. `kaggle/kernels/duecare_220_ollama_cloud_comparison/kernel-metadata.json`
5. `kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion/kernel-metadata.json`
6. `kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion/kernel-metadata.json`
7. `kaggle/kernels/duecare_600_results_dashboard/kernel-metadata.json`

## Required output artifact

Create or update `docs/review/31a_repo_truth_inventory.md` with these
sections only:

1. `Verified repo truths`
2. `Contradictions resolved`
3. `Current builder ownership and gaps`
4. `Live slug table`
5. `Validation state`
6. `Exact publish queue`
7. `Exact edit-before-publish queue`
8. `Inputs for 31b`

If the repo contradicts `30_project_checkpoint.md`, update that file in
the same pass before writing the final artifact.

## Execution rules

- Trust the repo over stale markdown summaries.
- Edit builders, metadata maps, and checkpoint docs when needed. Do not
  hand-edit emitted notebook JSON.
- Re-run the repo validator during this stage. Do not rely on an old
  remembered result.
- Probe Kaggle status if needed, but do not spend the daily cap on blind
  pushes in this stage.
- Record exact live and local slug differences for `005` and `600`.
- Confirm whether `600` still has a real source-of-truth gap.

## Required tasks

1. Re-run `python scripts/validate_notebooks.py` and record the actual
   result.
2. Reconcile `005`, `130`, `220`, `299`, `399`, and `600` across:
   builder `KERNEL_ID`, kernel metadata, `kaggle_live_slug_map.json`,
   and any local override tables.
3. Reconfirm source-of-truth ownership for `230`, `240`, `250`, `260`,
   `270`, `299`, `399`, and `600`.
4. Identify which kernels are actually push-ready now and which still
   require code edits first.
5. Update `docs/prompts/30_project_checkpoint.md` anywhere it no longer
   matches the repo.
6. Write the handoff artifact with exact commands and exact file paths.

## Gate to leave 31a

- `docs/review/31a_repo_truth_inventory.md` exists and is accurate.
- `docs/prompts/30_project_checkpoint.md` is updated if any repo-truth
  contradiction was found.
- The artifact names the first file group `31b` must edit.

## Final response format

Return a single markdown document with these sections only:

1. `Reconciled truths`
2. `Checkpoint updates`
3. `Validation result`
4. `Push-ready queue`
5. `Edit-first queue`
6. `Input for 31b`

Do not ask follow-up questions.
