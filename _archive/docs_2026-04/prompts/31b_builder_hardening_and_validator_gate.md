# 31b: DueCare builder hardening and validator gate

Date captured: 2026-04-16
Audience: Claude Code or GPT-5.4 running inside this repo.

This is stage 2 of the 31-series. Run it only after `31a` has produced
`docs/review/31a_repo_truth_inventory.md`.

Its job is to land structural fixes that make the notebook suite safer
to edit and publish: validator preservation, hardener fixes, slug/source-
of-truth repairs, and any missing builder ownership that blocks the
closing arc.

## Required inputs

Read these first:

1. `docs/review/31a_repo_truth_inventory.md`
2. `docs/prompts/30_project_checkpoint.md`
3. `scripts/notebook_hardening_utils.py`
4. `scripts/validate_notebooks.py`
5. `scripts/build_notebook_150_free_form_gemma_playground.py`
6. `scripts/build_notebook_155_tool_calling_playground.py`
7. `scripts/build_notebook_160_image_processing_playground.py`
8. `scripts/build_index_notebook.py`
9. `scripts/build_notebook_005_glossary.py`
10. `scripts/build_notebook_010_quickstart.py`
11. `scripts/build_notebook_130_prompt_corpus_exploration.py`
12. `scripts/build_section_conclusion_notebooks.py`
13. `scripts/build_kaggle_notebooks.py`
14. `scripts/align_kaggle_kernel_metadata.py`

If `31a` reported a real `600` builder gap, also inspect the live local
artifacts for `600` and the files that reference it.

## Required output artifact

Create or update `docs/review/31b_hardening_gate_report.md` with these
sections only:

1. `Implemented changes`
2. `Rebuilt notebooks`
3. `Validation results`
4. `Hardening decisions`
5. `Remaining blockers`
6. `Inputs for 31c`

## Execution rules

- Preserve a green validator run if the suite is already green.
- If the validator is not green, repair that first before other work.
- Edit source-of-truth builders and shared helpers, not emitted notebooks.
- If `005` slug repair touches multiple files, centralize the live slug
  mapping instead of copying overrides again.
- If `600` has no real builder and that gap blocks `610`, `799`, `899`,
  or closing docs, create a dedicated builder now rather than deferring.
- Keep the blast radius explicit. Rebuild everything changed by a shared
  helper edit.

## Required tasks

1. Preserve or restore the `validate_notebooks.py` gate.
2. Fix any remaining `005` slug drift across builders, cross-links,
   kernel metadata alignment, and local override tables.
3. Resolve the `600` source-of-truth gap if it still exists.
   - If a real generator is found, record it and use it.
   - If not, create `scripts/build_notebook_600_results_dashboard.py`
     from the existing local kernel artifact and treat that as source
     from here onward.
4. Normalize hardener-controlled install behavior and final summary
   behavior only where the touched files require it.
5. Rebuild affected notebooks, sync the Kaggle mirror if needed, and
   run targeted validation plus the full validator.
6. Write the artifact with exact changed files and the first notebook
   batch `31c` should upgrade.

## Gate to leave 31b

- The suite validator is green and not regressed.
- Any live `005` and `600` structural blockers are either fixed or
  written down precisely in the artifact.
- `docs/review/31b_hardening_gate_report.md` exists.

## Final response format

Return a single markdown document with these sections only:

1. `Structural fixes landed`
2. `Rebuild and validation`
3. `Slug and source-of-truth decisions`
4. `Remaining blockers`
5. `Input for 31c`

Do not ask follow-up questions.
