# 31d: DueCare shared-builder canonical upgrades

Date captured: 2026-04-16
Audience: Claude Code or GPT-5.4 running inside this repo.

This is stage 4 of the 31-series. Run it only after `31c` has produced
`docs/review/31c_dedicated_upgrades_report.md`.

This stage upgrades the remaining high-value shared-builder notebooks,
refreshes section conclusions so they match what actually shipped, and
extracts shared helpers only when the extraction clearly reduces live
duplication without destabilizing unrelated notebooks.

## Required inputs

Read these first:

1. `docs/review/31a_repo_truth_inventory.md`
2. `docs/review/31b_hardening_gate_report.md`
3. `docs/review/31c_dedicated_upgrades_report.md`
4. `docs/prompts/30_project_checkpoint.md`
5. `scripts/build_grading_notebooks.py`
6. `scripts/build_showcase_notebooks.py`
7. `scripts/build_section_conclusion_notebooks.py`
8. `scripts/notebook_hardening_utils.py`

If they exist, also inspect any extracted helpers such as:

1. `scripts/_public_slugs.py`
2. `scripts/_canonical_notebook.py`

## Required output artifact

Create or update `docs/review/31d_shared_builder_report.md` with these
sections only:

1. `Shared helper changes`
2. `Notebook upgrades`
3. `Rebuild scope`
4. `Validation results`
5. `Push-ready shared-builder queue`
6. `Remaining shared risks`
7. `Inputs for 31e`

## Execution rules

- Respect shared-builder blast radius. Rebuild every sibling affected by
  a changed shared builder.
- Upgrade the smallest safe surface first inside each shared builder.
- Only extract helpers when the extraction removes real duplication that
  is already causing drift.
- Keep the suite validator green throughout.

## Required tasks

1. Canonicalize `250` inside `build_grading_notebooks.py` by editing
   the `NB11_CELLS` block only.
2. Canonicalize `260` inside `build_showcase_notebooks.py` by editing
   the `RAG_CELLS` block only.
3. Reconfirm and refresh `299` and `399` inside
   `build_section_conclusion_notebooks.py` so their recap and handoff
   text matches the notebooks that are actually ready or live after
   `31c`.
4. If shared duplication is still painful across index, glossary, and
   conclusion builders, extract `_public_slugs.py` and or
   `_canonical_notebook.py` now.
5. Rebuild every touched shared builder, sync mirrors, run targeted
   validation if present, and then run the full suite validator.
6. Write the artifact with the exact push order for `250`, `260`,
   `299`, and `399`, plus any other siblings that became push-ready
   because of the rebuild.

## Gate to leave 31d

- The suite validator remains green.
- `docs/review/31d_shared_builder_report.md` exists.
- The artifact identifies the exact publish order `31e` should use.

## Final response format

Return a single markdown document with these sections only:

1. `Shared-builder upgrades`
2. `Rebuild and validation`
3. `Push-ready shared batch`
4. `Publish handoff`

Do not ask follow-up questions.
