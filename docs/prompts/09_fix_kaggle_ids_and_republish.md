# Fix Kaggle id mismatches and republish all 28 notebooks

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

## Root cause of the 21 publish failures

Kaggle uses the `id` field in `kernel-metadata.json` as the lookup
key when you push. If the id matches an existing kernel, Kaggle
creates a new version. If the id does not match anything, Kaggle
tries to create a brand new kernel.

The rename pass changed the `id` for many kernels from their
original Kaggle slug to a new three-digit slug. Kaggle cannot find
a kernel under the new id, so it tries to create a new one. But
the title often conflicts with the existing kernel, producing 400
Bad Request, 409 Conflict, or "Notebook not found" errors.

The fix: restore the original Kaggle id for every kernel that
already exists on Kaggle. The local three-digit directory naming
stays as is. Only the `id` field in `kernel-metadata.json` changes
back. Titles can be updated freely once the id matches.

## Step 1. Verify Kaggle authentication

Run:

```
python scripts/publish_kaggle.py auth-check
```

Must exit 0. If it fails, ensure `~/.kaggle/kaggle.json` exists
with valid username and key.

## Step 2. Restore original Kaggle ids

The original Kaggle ids were recorded before the rename pass. For
each of the 28 kernels, look up the original Kaggle slug that the
kernel was published under. Then decide: does this kernel already
exist on Kaggle, or is it brand new?

Run this command to check which kernels already exist on Kaggle:

```
kaggle kernels list --user taylorsamarel --page-size 100
```

This returns every kernel the user owns. Cross-reference against
the 28 local kernels.

For every kernel that ALREADY EXISTS on Kaggle, set the `id` field
in `kernel-metadata.json` to the original slug that Kaggle knows.
Here are the original slugs from the pre-rename state (from git
history or from the first `current_kaggle_notebook_state.md`):

```
Local directory                        | Original Kaggle id (use this)
duecare_000_index                      | taylorsamarel/duecare-index
duecare_010_quickstart                 | taylorsamarel/01-duecare-quickstart-generalized-framework
duecare_100_gemma_exploration          | taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts
duecare_110_prompt_prioritizer         | taylorsamarel/duecare-curating-2k-trafficking-prompts-from-74k
duecare_120_prompt_remixer             | taylorsamarel/00b-duecare-prompt-remixer-data-pipeline
duecare_200_cross_domain_proof         | taylorsamarel/duecare-cross-domain-proof
duecare_210_oss_model_comparison       | taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety
duecare_220_ollama_cloud_comparison    | taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud
duecare_230_mistral_family_comparison  | taylorsamarel/duecare-gemma-4-vs-mistral-family
duecare_240_openrouter_frontier_comparison | taylorsamarel/duecare-vs-large-cloud-models
duecare_250_comparative_grading        | taylorsamarel/duecare-comparative-grading
duecare_260_rag_comparison             | taylorsamarel/duecare-rag-comparison
duecare_270_gemma_generations          | taylorsamarel/duecare-22-gemma-generations
duecare_300_adversarial_resistance     | taylorsamarel/duecare-adversarial-resistance
duecare_310_prompt_factory             | taylorsamarel/duecare-adversarial-prompt-factory
duecare_320_supergemma_safety_gap      | taylorsamarel/duecare-uncensored-redteam
duecare_400_function_calling_multimodal| taylorsamarel/duecare-function-calling-multimodal
duecare_410_llm_judge_grading          | taylorsamarel/duecare-llm-judge-grading
duecare_420_conversation_testing       | taylorsamarel/duecare-conversation-testing
duecare_430_rubric_evaluation          | taylorsamarel/duecare-rubric-anchored-evaluation
duecare_440_per_prompt_rubric_generator| taylorsamarel/duecare-rubric-pipeline
duecare_450_contextual_worst_response_judge | taylorsamarel/duecare-context-judge
duecare_500_agent_swarm_deep_dive      | taylorsamarel/duecare-12-agent-gemma-4-safety-pipeline
duecare_510_phase2_model_comparison    | taylorsamarel/duecare-phase-2-model-comparison
duecare_520_phase3_curriculum_builder  | taylorsamarel/duecare-curriculum-builder
duecare_530_phase3_unsloth_finetune    | taylorsamarel/duecare-phase3-finetune
duecare_600_results_dashboard          | taylorsamarel/duecare-results-dashboard
duecare_610_submission_walkthrough     | taylorsamarel/duecare-submission-walkthrough
```

For each kernel:

a. Open `kaggle/kernels/<directory>/kernel-metadata.json`.
b. Set `id` to the value from the "Original Kaggle id" column.
c. Leave `code_file` as is (the new three-digit filename).
d. Set `title` to a clean version using the three-digit prefix:
   `NNN: <descriptive title>`. Kaggle allows title changes on
   existing kernels. Use titles that are descriptive but short
   (under 80 characters).
e. Ensure `is_private` is `false`.
f. Ensure `competition_sources` includes `gemma-4-good-hackathon`.
g. Save the file.

IMPORTANT: The `kaggle kernels list` output from Kaggle is the
ground truth for which ids exist. If a kernel does not appear in
that list (because it was never successfully published), use a new
clean id of the form `taylorsamarel/duecare-NNN-<kebab-slug>` and
set the title to match exactly so Kaggle derives the same slug.
For new kernels, the title-derived slug must equal the id slug.
To compute what Kaggle derives: lowercase the title, replace all
non-alphanumeric characters with hyphens, collapse consecutive
hyphens, strip leading and trailing hyphens, then prepend
`taylorsamarel/`.

Check: `python scripts/publish_kaggle.py --dry-run push-notebooks`
discovers all 28 and exits 0.

## Step 3. Rebuild builder-owned notebooks

If any of the 14 build scripts embed the Kaggle id or title in
their output cells (for example in the first markdown cell), update
the build script, then rebuild:

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

IMPORTANT: Build scripts must NOT overwrite `kernel-metadata.json`.
If a build script writes metadata, update it to use the original
Kaggle id, not a generated one.

Check: After rebuild, re-read every `kernel-metadata.json` and
confirm the `id` field still matches the original Kaggle slug from
step 2. If any build script overwrote it, fix the build script and
rebuild again.

## Step 4. Publish all notebooks

Run:

```
python scripts/publish_kaggle.py push-notebooks
```

Then immediately:

```
python scripts/publish_kaggle.py status-notebooks
```

Expected behavior:

- Kernels with existing Kaggle ids: push creates a new version.
  Status should show queued, running, or complete.
- Kernels with new ids (never published before): push creates a
  new kernel. Status should show queued or running.
- If any kernel returns 400, 409, or 404: note the kernel slug,
  the error, and move on. Do not retry more than once.

## Step 5. Handle remaining failures

After the publish pass, categorize failures:

a. 400 Bad Request: Usually means the id still does not match an
   existing kernel AND Kaggle cannot create a new one because the
   title conflicts. Fix: check `kaggle kernels list` output,
   find the actual slug Kaggle is using, set `id` to that exact
   slug, and retry.

b. 409 Conflict: The kernel exists but something else is wrong
   (usually a concurrent push or a slug collision). Wait 60
   seconds and retry once.

c. 404 Not Found: The kernel does not exist and Kaggle could not
   create it. This means the id is wrong. Check
   `kaggle kernels list` again, or create the kernel fresh by
   setting the id to match the title-derived slug.

d. UTF-8 decode errors from kaggle.exe on Windows: Set the
   environment variable `PYTHONIOENCODING=utf-8` before running
   the publish command:
   ```
   $env:PYTHONIOENCODING = "utf-8"
   python scripts/publish_kaggle.py push-notebooks
   ```

For each remaining failure, log the kernel slug, error, and
attempted fix in `docs/review/notebook_publish_report.md`.

## Step 6. Update all docs

a. Regenerate `docs/current_kaggle_notebook_state.md` with the
   final Kaggle ids (the original slugs, not the three-digit ones).

b. Update `docs/notebook_guide.md` Kaggle link column to use the
   correct slug in the URL:
   `https://www.kaggle.com/code/taylorsamarel/<original-slug>`

c. Update `README.md` if it links to any Kaggle notebooks.

d. Update `docs/review/notebook_publish_report.md` with final
   per-kernel status.

## Step 7. Commit

Stage all changes and commit. Message:

```
Restore original Kaggle ids + republish all 28 notebooks

The rename pass broke publishing because Kaggle uses the id field
as the kernel lookup key. Restored original slugs so push updates
existing kernels instead of creating conflicting new ones. Local
three-digit directory naming preserved.

Published: <count>
Failed: <count>
```

## Key insight for future work

Local directory names (three-digit scheme) and Kaggle kernel ids
(original slugs) are independent. They do not need to match. The
`kernel-metadata.json` `id` field is the bridge: it tells Kaggle
which kernel to update when you push. The local directory name is
for human navigation only. Never change the `id` field unless you
intend to create a brand new kernel on Kaggle.

## Quick reference: the four checks that must pass

```
python scripts/publish_kaggle.py auth-check
python scripts/publish_kaggle.py --dry-run push-notebooks
python scripts/publish_kaggle.py status-notebooks
grep -r '"is_private": true' kaggle/kernels/
```

Last grep should return nothing. First three exit 0.
