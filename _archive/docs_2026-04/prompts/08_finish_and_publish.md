# Finish everything and publish all 28 notebooks to Kaggle

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

The renumbering pass is 80% done. All 28 kernel directories, notebook
files, and local mirrors have been renamed to the three-digit scheme.
But 14 kernels still have old Kaggle ids and titles in their
`kernel-metadata.json`. This prompt finishes the job and publishes.

## Step 1. Verify Kaggle authentication

Run:

```
python scripts/publish_kaggle.py auth-check
```

If it fails, check that `~/.kaggle/kaggle.json` exists and contains
valid `username` and `key` fields. If the file is missing, the user
must create it manually at `C:\Users\amare\.kaggle\kaggle.json` with:

```json
{"username": "taylorsamarel", "key": "<KAGGLE_API_KEY>"}
```

The key is stored in Kaggle account settings under "API > Create New
Token". Do not proceed until auth-check exits 0.

## Step 2. Fix the 14 inconsistent kernel-metadata.json files

The following 14 kernels have stale `id` and `title` fields that
still use the old naming. The `code_file` is already correct. For
each one, update `kernel-metadata.json` so `id` and `title` match
the new scheme:

```
Directory                              | Current id (WRONG)                                    | Correct id                                          | Correct title
duecare_100_gemma_exploration          | taylorsamarel/duecare-gemma-exploration                | taylorsamarel/duecare-100-gemma-exploration          | 100: Gemma 4 on 50 Trafficking Prompts (Phase 1 Baseline)
duecare_110_prompt_prioritizer         | taylorsamarel/duecare-prompt-prioritizer               | taylorsamarel/duecare-110-prompt-prioritizer         | 110: Select 2000 High-Value Prompts from 74K Corpus
duecare_120_prompt_remixer             | taylorsamarel/duecare-prompt-remixer                   | taylorsamarel/duecare-120-prompt-remixer             | 120: Generate 15 Adversarial Variations per Base Prompt
duecare_210_oss_model_comparison       | taylorsamarel/duecare-gemma-vs-oss-comparison          | taylorsamarel/duecare-210-oss-model-comparison       | 210: Gemma 4 vs Llama, Mistral, Gemma 2B on Trafficking
duecare_220_ollama_cloud_comparison    | taylorsamarel/duecare-ollama-cloud-oss-comparison      | taylorsamarel/duecare-220-ollama-cloud-comparison    | 220: Gemma 4 vs 6 OSS Models via Ollama Cloud
duecare_240_openrouter_frontier_comparison | taylorsamarel/duecare-openrouter-frontier-comparison | taylorsamarel/duecare-240-openrouter-frontier-comparison | 240: DueCare vs Large Cloud Models (OpenRouter)
duecare_270_gemma_generations          | taylorsamarel/duecare-270-gemma-generations            | (already correct)                                   | 270: DueCare Gemma 2 vs 3 vs 4 Generations Comparison
duecare_320_supergemma_safety_gap      | taylorsamarel/duecare-finding-gemma-4-safety-line      | taylorsamarel/duecare-320-supergemma-safety-gap      | 320: DueCare Red-Team (Finding Gemma 4 Safety Line)
duecare_440_per_prompt_rubric_generator | taylorsamarel/duecare-per-prompt-rubric-generator     | taylorsamarel/duecare-440-per-prompt-rubric-generator | 440: Per-Prompt Rubric Generator with Failure Classification
duecare_450_contextual_worst_response_judge | taylorsamarel/duecare-contextual-judge            | taylorsamarel/duecare-450-contextual-worst-response-judge | 450: Contextual Worst-Response Judge
duecare_510_phase2_model_comparison    | taylorsamarel/duecare-phase2-comparison                | taylorsamarel/duecare-510-phase2-model-comparison    | 510: Gemma 4 2B vs 9B Parameters on Safety
duecare_520_phase3_curriculum_builder  | (already correct)                                     | (already correct)                                   | 520: DueCare Phase 3 Curriculum Builder
duecare_530_phase3_unsloth_finetune    | (already correct)                                     | (already correct)                                   | 530: Gemma 4 LoRA Fine-Tuning and Local Model Export
```

For each kernel directory listed above where the id is wrong:

a. Open `kaggle/kernels/<directory>/kernel-metadata.json`.
b. Set the `id` field to the value in the "Correct id" column.
c. Set the `title` field to the value in the "Correct title" column.
d. Leave all other fields unchanged (`code_file`, `language`,
   `kernel_type`, `is_private`, `enable_gpu`, `enable_tpu`,
   `enable_internet`, `dataset_sources`, `competition_sources`,
   `kernel_sources`, `model_sources`).
e. Save the file.

Also update the titles for the three kernels marked "already correct"
on id but with old-style titles (270, 520, 530).

After all 14 files are fixed, also verify the other 14 are correct
by scanning every `kernel-metadata.json` and confirming:

- The `id` matches the pattern `taylorsamarel/duecare-NNN-<kebab>`.
- The `title` starts with `NNN:`.
- The `code_file` matches `NNN_<snake>.ipynb`.
- The `code_file` actually exists in the same directory.

Check: `python scripts/publish_kaggle.py --dry-run push-notebooks`
discovers all 28 and exits 0.

## Step 3. Fix stale references inside builder scripts

The 14 builder scripts under `scripts/build_notebook_*.py` generate
the notebook content. Some still contain old titles or old slugs
inside their `md()` cell strings. For each builder script:

a. Open the file.
b. Search for the old title string (from the "Current id (WRONG)"
   column or old human titles like "00 - DueCare Gemma Exploration"
   or "00a - DueCare Prompt Prioritizer").
c. Replace with the new title from the "Correct title" column.
d. Search for any remaining references to old directory names (like
   `duecare_00_gemma_exploration` or `duecare_phase2_comparison`).
e. Replace with the new directory names.
f. Save the file.

After fixing, rebuild all notebooks:

```
python scripts/build_notebook_100.py
python scripts/build_notebook_110.py
python scripts/build_notebook_120.py
python scripts/build_notebook_210_oss_model_comparison.py
python scripts/build_notebook_220_ollama_cloud_comparison.py
python scripts/build_notebook_230_mistral_family_comparison.py
python scripts/build_notebook_240_openrouter_frontier_comparison.py
python scripts/build_notebook_270_gemma_generations.py
python scripts/build_notebook_320_supergemma_safety_gap.py
python scripts/build_notebook_440_per_prompt_rubric_generator.py
python scripts/build_notebook_450_contextual_worst_response_judge.py
python scripts/build_notebook_510_phase2_model_comparison.py
python scripts/build_notebook_520_phase3_curriculum_builder.py
python scripts/build_notebook_530_phase3_unsloth_finetune.py
```

Every script must exit 0. If one fails, read the traceback and fix
the specific line.

Check: rerun the metadata consistency scan from step 2 after rebuild
to confirm builder scripts did not overwrite the fixed metadata.

## Step 4. Set all notebooks to public

Every `kernel-metadata.json` must have `"is_private": false` so
judges can see them. Scan all 28 and flip any that say `true`.

Check: `grep -r '"is_private": true' kaggle/kernels/` returns no
results.

## Step 5. Ensure competition source is present

Every `kernel-metadata.json` must include the competition source:

```json
"competition_sources": ["gemma-4-good-hackathon"]
```

Scan all 28 and add the field to any that are missing it.

Check: `grep -rL 'gemma-4-good-hackathon' kaggle/kernels/*/kernel-metadata.json`
returns no results.

## Step 6. Pin package versions in notebook install cells

The current package version is 0.1.0 (check
`packages/duecare-llm-core/pyproject.toml` to confirm). In every
notebook (both the builder script source and any raw `.ipynb` that
has no builder), find the `pip install` cell and ensure every
duecare package is pinned:

```python
!pip install duecare-llm-core==0.1.0 duecare-llm-domains==0.1.0
```

Not:

```python
!pip install duecare-llm-core duecare-llm-domains
```

After fixing builders, rebuild the affected notebooks again.

Check: search all `.ipynb` files for `pip install duecare` and
confirm every instance includes `==0.1.0`.

## Step 7. Publish all notebooks to Kaggle

Run:

```
python scripts/publish_kaggle.py push-notebooks
```

This creates new kernel versions on Kaggle. The Kaggle API will
create new kernels for ids it has not seen before and version-bump
existing kernels whose ids match.

After push completes, run:

```
python scripts/publish_kaggle.py status-notebooks
```

Record the status of every kernel. If any kernel shows an error:

- Read the error message.
- If it says "403 Forbidden", auth is wrong. Go back to step 1.
- If it says "404 Not Found", the kernel id is new and Kaggle is
  creating it. Wait 60 seconds and check status again.
- If it says the notebook is too large, the notebook exceeds
  Kaggle's 20MB limit. Identify which notebook and trim it.
- Do not retry more than twice per kernel.

## Step 8. Update docs to reflect the new state

a. Regenerate `docs/current_kaggle_notebook_state.md`. List all 28
   kernels with their new directory name, Kaggle id, code file,
   local mirror, and title. Remove the "Legacy Directory Aliases"
   section (all aliases are now resolved). Remove the "Extra Local
   Notebooks" section (`forge_llm_core_demo.ipynb` was deleted).

b. Update `docs/notebook_guide.md` with a table of all notebooks
   in numbered order. Columns: ID, Title, Section, Kaggle Link
   (format: `https://www.kaggle.com/code/taylorsamarel/<slug>`),
   Purpose (one sentence).

c. Update `README.md`: find any references to old notebook slugs
   (like `duecare-gemma-exploration`, `duecare-adversarial-resistance`,
   `duecare-index`) and replace with the new slugs.

d. Update `docs/copilot_review_prompt.md`: change the kernel count
   and inventory section to match the new state.

## Step 9. Commit

Stage all changed files and commit with a message like:

```
Renumber 28 Kaggle notebooks to three-digit curriculum scheme

- 16 legacy directory aliases resolved
- 14 builder scripts renamed and updated
- All kernel-metadata.json normalized (NNN prefix on id and title)
- All notebooks set to public
- Competition source verified on all 28
- Published to Kaggle
- Docs updated
```

## What to verify at the end

Run these four checks. All must pass:

```
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py --dry-run push-notebooks
python scripts/publish_kaggle.py status-notebooks
grep -r '"is_private": true' kaggle/kernels/
```

The last grep should return nothing. The first three should exit 0.

## Current state summary for reference

28 kernel directories, all renamed to `duecare_NNN_<snake>` scheme.
28 local mirrors in `notebooks/`, all renamed to `NNN_<snake>.ipynb`.
14 builder scripts renamed to `build_notebook_NNN_*.py`.
14 kernels have correct new-scheme metadata.
14 kernels have stale old-scheme metadata (listed in step 2).
192 uncommitted changes in git.
Dry-run publish discovers all 28 and exits 0.
`forge_llm_core_demo.ipynb` already deleted.
