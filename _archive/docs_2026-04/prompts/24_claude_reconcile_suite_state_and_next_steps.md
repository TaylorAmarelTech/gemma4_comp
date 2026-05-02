# Claude execution: reconcile DueCare suite state and implement next fixes

This prompt is for Claude or Claude Code running against the current
DueCare repo. The job is to reconcile the actual notebook-suite state,
correct stale assumptions, and then actively implement the next
high-value fixes.

Do not stop at analysis. Read the repo, make the changes that are
clearly required, rebuild affected notebooks, run targeted validation,
and leave the next Kaggle push queue ready.

## Voice and method

- Voice: terse, opinionated, plain English.
- No em dashes.
- No emojis.
- No filler.
- Use notebook IDs, cell numbers, exact strings, and file paths when
  reasoning.
- Use cell numbers only, never internal notebook cell IDs.
- If the current repo contradicts any summary below, trust the repo and
  fold the correction into the relevant section of your execution work.

## Execution rules

- Edit source-of-truth builders whenever they exist.
- Regenerate emitted notebooks and Kaggle kernel copies after builder
  edits.
- Rebuild only the notebooks affected by the work you actually change.
- Run targeted validation after each logical batch.
- Preserve existing Kaggle slugs unless the repo already encodes an
  intentional override.
- Preserve unrelated user changes.
- If the Kaggle cap blocks publishing, stop at a push-ready state and
  report exact commands for the next reset.
- If a dedicated `140` notebook is clearly warranted and can be wired in
  cleanly, create it now instead of merely recommending it.

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

## Current state to reconcile

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

Execute the reconciliation work top to bottom without asking follow-up
questions. Inspect the repo, correct the state as needed, implement the
highest-value improvements you can complete in this pass, and only then
return a compact execution report.

Work in this order:

1. Reconcile `210`, `220`, `130`, `000`, `299`, and the current
   hardener, index, and conclusion state.
2. Finish `220` push readiness if anything is still missing.
3. Decide whether `140` should exist now. If yes, build and wire it in
   during this pass.
4. Canonicalize `230`, `240`, `250`, `260`, `270`, and `399` as far as
   can be done cleanly in one pass.
5. Propagate cross-section fixes that obviously reduce future churn.
6. Rebuild only what changed.
7. Run targeted validation.
8. Leave the next Kaggle push queue ready if publishing is blocked.

## Required execution coverage

### 1. Immediate retry queue after Kaggle cap reset

Prepare exact `kaggle kernels push -p <dir>` commands in execution
order for what is actually push-ready after your edits. Cover:

- `130` push
- `220` push
- `000` push
- whether `210` needs only a no-op confirm or an actual repush

### 2. `220` validation checklist before push

Verify and, if needed, fix all of the following:

- exact build command
- exact grep or search targets
- exact assertions or markers that should exist in the builder
- exact final-print marker to confirm in the emitted notebook
- exact kernel-metadata fields to confirm before pushing

### 3. Canonical rewrite order for `230`, `240`, `250`, `260`, `270`

For each notebook, inspect the current builder arrangement and then
implement the structural fixes that are clearly needed. In your final
report, state:

- live Kaggle slug if one exists, or say to verify with Kaggle CLI
- canonical title
- whether it belongs to a dedicated builder or a shared builder
- minimum structural fixes landed
- whether it should be grouped into one push batch or split

Assume `250` and `260` may live under a shared grading or showcase
builder. Confirm that from the repo before you answer.

### 4. `399` rewrite brief

Rewrite `399` if the current conclusion is stale. The conclusion must:

- honestly close the Baseline Text Comparisons section
- mention the real `210/220` comparison story
- reference `130` as the reader's map of the inputs if that still fits
- hand off cleanly to `300`
- spell out recap and key-point language the author can directly accept

### 5. Cross-section consistency fixes

Implement the safe cross-section fixes you can land during this pass,
then call out anything still deferred. Cover:

- kernel-id vs title-slug mismatches
- `PUBLIC_SLUG_OVERRIDES` drift across builders
- install pinning policy: `duecare-llm==0.1.0` meta package vs split
  packages
- plotly rgba fills
- hardener final-print patching
- shared constants such as `SAFETY_DIMENSIONS`
- any new pattern introduced by `130` that should propagate elsewhere

### 6. Next-section execution order across prompts `18` through `22`

If you finish the `17` band work early enough, continue into prompts
`18` through `22` in order. If not, leave an exact next-pass sequence.
Break the remaining work into pushable batches that respect:

- Kaggle daily cap
- `scripts/validate_notebooks.py` as a gate
- shared-builder blast radius

You must explicitly flag:

- notebooks that share builders
- notebooks with dedicated builders
- whether a new `140` notebook should be created now or deferred
- if `140` should be created now, exactly which files were touched

### 7. Explicit risk call-outs

Be blunt about what is still bent, deferred, or fragile after your
edits. At minimum cover:

- `210` live slug is non-canonical
- `220` may create a new kernel or collide with an unexpected existing
  slug
- `150/155/160` still block a clean `42 of 42` validator pass
- `130` may degrade to a small fallback pack when the full dataset is
  missing
- any contradictions you discovered while inspecting the repo

### 8. Done definition

Define what green looks like for each of:

- code repo
- Kaggle notebook suite
- writeup
- 3-minute video
- HF Hub weights
- live demo

Keep this section short.

## Output format

- Return a single markdown document.
- Use numbered top-level sections `1` through `8` only.
- Use flat bullets inside each section.
- Put exact CLI commands in fenced code blocks.
- Keep the whole response under `1,200` words.
- Do not add a preamble.
- Do not add a separate findings section.
- Do not ask questions back.
- Report implemented changes, rebuilds, and validation results, not just
  recommendations.