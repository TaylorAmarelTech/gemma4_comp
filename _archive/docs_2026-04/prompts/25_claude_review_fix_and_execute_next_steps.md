# Claude execution: review, fix, rebuild, validate, and execute next steps

This prompt is for Claude or Claude Code running against the current
DueCare repo. The job is to review the current notebook-suite state,
fix what is fixable now, rebuild affected notebooks, validate the
results, and continue into the next highest-value work without stopping
at a plan.

Do not return a recommendation-only answer. Inspect the repo, make the
changes that are clearly needed, rebuild what changed, run targeted
validation, and leave the Kaggle push queue and next execution order
explicitly ready.

## Voice and method

- Voice: terse, opinionated, plain English.
- No em dashes.
- No emojis.
- No filler.
- Use notebook IDs, cell numbers, exact strings, and file paths when
  reasoning.
- Use cell numbers only, never internal notebook cell IDs.
- If the repo contradicts any summary below, trust the repo and fix the
  relevant files instead of preserving stale assumptions.

## Execution rules

- Edit source-of-truth builders whenever they exist.
- Regenerate emitted notebooks and Kaggle kernel copies after builder
  edits.
- Rebuild only the notebooks affected by the work you actually changed.
- Run targeted validation after each logical batch.
- Preserve unrelated user changes.
- Preserve existing Kaggle slugs unless the repo already encodes an
  intentional override.
- If a safe fix is obvious, implement it instead of recommending it.
- If a new `140` notebook is clearly the right move, create it now and
  wire it into the section instead of deferring it.
- If the Kaggle cap blocks publishing, stop at a push-ready state and
  report exact push commands in order.
- Keep going until the current pass has produced real code changes,
  rebuilt notebooks, validation output, and a concrete next queue.

## Read these files first

Inspect these files before editing:

1. `scripts/build_notebook_210_oss_model_comparison.py`
2. `scripts/build_notebook_220_ollama_cloud_comparison.py`
3. `scripts/build_notebook_130_prompt_corpus_exploration.py`
4. `scripts/notebook_hardening_utils.py`
5. `scripts/build_index_notebook.py`
6. `scripts/build_section_conclusion_notebooks.py`
7. `scripts/validate_notebooks.py`
8. `docs/prompts/17_claudecode_cleanup_220_through_399.md`
9. `docs/prompts/18_claudecode_cleanup_300_400_410_420_499.md`
10. `docs/prompts/19_claudecode_cleanup_310_430_440_699.md`
11. `docs/prompts/20_claudecode_cleanup_320_450_799.md`
12. `docs/prompts/21_claudecode_cleanup_500_510_520_530_599.md`
13. `docs/prompts/22_claudecode_cleanup_600_610_899.md`
14. `docs/prompts/23_claudecode_full_suite_cleanup_orchestrator.md`
15. `docs/prompts/24_claude_reconcile_suite_state_and_next_steps.md`

Also inspect current kernel metadata for at least these notebooks:

1. `kaggle/kernels/duecare_000_index/kernel-metadata.json`
2. `kaggle/kernels/duecare_130_prompt_corpus_exploration/kernel-metadata.json`
3. `kaggle/kernels/duecare_210_oss_model_comparison/kernel-metadata.json`
4. `kaggle/kernels/duecare_220_ollama_cloud_comparison/kernel-metadata.json`
5. `kaggle/kernels/duecare_230_mistral_family_comparison/kernel-metadata.json`
6. `kaggle/kernels/duecare_240_openrouter_frontier_comparison/kernel-metadata.json`
7. `kaggle/kernels/duecare_250_comparative_grading/kernel-metadata.json`
8. `kaggle/kernels/duecare_260_rag_comparison/kernel-metadata.json`
9. `kaggle/kernels/duecare_270_gemma_generations/kernel-metadata.json`
10. `kaggle/kernels/duecare_299_baseline_text_evaluation_framework_conclusion/kernel-metadata.json`
11. `kaggle/kernels/duecare_399_baseline_text_comparisons_conclusion/kernel-metadata.json`

## Environment facts

- Workspace root: `C:\Users\amare\OneDrive\Documents\gemma4_comp`
- Shell: PowerShell
- Python prefix:
  `c:/Users/amare/OneDrive/Documents/gemma4_comp/.venv/Scripts/python.exe`
- Kaggle pushes use `kaggle kernels push -p <dir>`
- Kaggle can return daily `429 Too Many Requests`

## Current state to reconcile and act on

Treat the following as a starting claim set, not gospel:

1. `210` is complete, rebuilt in canonical style, and already live on
   Kaggle under an existing non-canonical public slug.
2. `220` is rebuilt locally in the canonical `200/210` style but has
   not yet been fully validated and pushed.
3. `130` now exists locally as a new corpus-oriented notebook and is
   already wired into the index, hardener, and section conclusion.
4. `scripts/validate_notebooks.py` currently reports `39 of 42 OK`,
   with only the three known playground notebooks still failing because
   they are missing a final summary code cell.
5. Kaggle push cap is currently hit, so `130`, `220`, and the updated
   `000` index are queued for the next reset.
6. The wider cleanup ladder is paused mid-stream. `230`, `240`, `250`,
   `260`, `270`, `399`, and most notebooks from `300` onward still need
   canonical cleanup.
7. There is still an open product question whether a dedicated `140`
   notebook should now exist to explain evaluation mechanics between the
   new corpus notebook and the rest of the baseline section.

## Your task

Review and fix the suite in this order, without asking follow-up
questions:

1. Reconcile `210`, `220`, `130`, `000`, `299`, and the current
   hardener, index, and conclusion state.
2. Finish `220` push readiness. If something is missing, fix it now.
3. Decide whether `140` should exist now. If yes, create it, wire it
   into the section, rebuild it, and validate it.
4. Canonicalize `230`, `240`, `250`, `260`, `270`, and `399` as far as
   can be done cleanly in one pass.
5. Propagate obvious cross-section fixes that reduce future churn.
6. Rebuild only what changed.
7. Run targeted validation.
8. If there is still capacity after finishing the `17` band work,
   continue into prompts `18` through `22` in order.
9. Leave the next Kaggle push queue ready if publishing is blocked.

## Minimum implementation requirements

### A. Push readiness and validation

- Verify `220` build command, header structure, final print, kernel
  metadata, and any `assert` or plotting safeguards that should mirror
  `210`.
- Prepare exact `kaggle kernels push -p <dir>` commands for every
  notebook made push-ready in this pass, including `130`, `220`, and
  `000` if they still belong in the queue.
- Decide whether `210` needs only a no-op confirm or an actual repush.

### B. Baseline comparison cleanup

- Inspect and fix `230`, `240`, `250`, `260`, `270`, and `399`.
- Confirm whether each notebook uses a dedicated builder or a shared
  builder and work at the correct source-of-truth layer.
- Apply the minimum structural fixes needed for consistency with the
  canonical `210/220` style: HTML header, single hardener install path,
  correct package pins, rgba Plotly fills, honest troubleshooting,
  and URL-bearing final handoff prints.
- Rewrite `399` if stale so it honestly closes the section, references
  `130` if appropriate, names the `210/220` comparison story, and hands
  off cleanly to `300`.

### C. Cross-section fixes

- Fix safe drift you can land now across the touched files, including:
  kernel-id vs title-slug mismatches, `PUBLIC_SLUG_OVERRIDES` drift,
  install pinning policy, rgba fill consistency, hardener final-print
  behavior, and shared constants such as `SAFETY_DIMENSIONS`.
- If you find a repeated fix pattern in this pass, apply it at the
  shared helper or shared-builder level instead of patching copies.

### D. Next-step execution

- If prompt `17` work fully lands and validates, continue directly into
  prompt `18`, then `19`, then `20`, then `21`, then `22`, stopping only
  if the shared-builder blast radius becomes too large for one safe pass
  or if the session budget is clearly exhausted.
- If you cannot continue, leave an exact next-pass sequence with pushable
  batches and file groups.

## Final response format

Return a single markdown document with these sections only:

1. Implemented changes
2. Rebuilt notebooks
3. Validation results
4. Kaggle push queue
5. Remaining next steps
6. Risks and blockers

Additional response rules:

- Use flat bullets inside each section.
- Put exact CLI commands in fenced code blocks where relevant.
- Report actual edits, rebuilds, and validation results, not just
  recommendations.
- Include exact file paths when you describe changed builders or shared
  helpers.
- Keep it compact.
- Do not add a preamble.
- Do not ask questions back.