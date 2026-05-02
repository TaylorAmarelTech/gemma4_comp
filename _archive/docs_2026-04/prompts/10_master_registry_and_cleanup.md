# Create a master notebook registry and fix all stale references

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

## Problem

The repo has notebook names, Kaggle ids, titles, and directory paths
hardcoded in at least 10 different files. Every rename pass breaks
something because there is no single source of truth that all scripts
and tests read from. This prompt fixes that permanently.

## Step 1. Create the master notebook registry

Create a new file at `scripts/notebook_registry.py`. This is the
single source of truth for every notebook's identity. It is a Python
file (not YAML, not JSON) so builders, tests, publishers, and doc
generators can import it directly.

The file exports one list: `NOTEBOOKS`. Each entry is a dict with
these exact keys:

```python
NOTEBOOKS = [
    {
        "num": "000",                    # three-digit local ID
        "local_dir": "duecare_000_index",  # directory under kaggle/kernels/
        "code_file": "000_index.ipynb",    # notebook filename
        "kaggle_id": "taylorsamarel/duecare-index",  # ORIGINAL Kaggle slug
        "title": "000: DueCare Index",     # display title
        "section": "orientation",          # curriculum section name
        "gpu": False,                      # needs GPU
        "private": False,                  # is_private
        "competition": "gemma-4-good-hackathon",
        "datasets": [],                    # dataset_sources list
        "models": [],                      # model_sources list
        "builder": None,                   # path to build script, or None
    },
    ...
]
```

Populate it with all 28 current notebooks using the data below.
The Kaggle ids come from the ORIGINAL pre-rename state (these are
the slugs Kaggle actually knows about):

```
num  | local_dir                              | code_file                              | kaggle_id                                                    | title                                                              | section       | gpu   | builder
000  | duecare_000_index                      | 000_index.ipynb                        | taylorsamarel/duecare-index                                  | 000: DueCare Index                                                 | orientation   | false | scripts/build_index_notebook.py
010  | duecare_010_quickstart                 | 010_quickstart.ipynb                   | taylorsamarel/01-duecare-quickstart-generalized-framework    | 010: DueCare Quickstart                                            | orientation   | false | scripts/build_kaggle_notebooks.py
100  | duecare_100_gemma_exploration          | 100_gemma_exploration.ipynb             | taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts | 100: Gemma 4 Exploration (Phase 1 Baseline)                        | exploration   | true  | scripts/build_notebook_100.py
110  | duecare_110_prompt_prioritizer         | 110_prompt_prioritizer.ipynb            | taylorsamarel/duecare-curating-2k-trafficking-prompts-from-74k | 110: Prompt Prioritizer                                          | exploration   | false | scripts/build_notebook_110.py
120  | duecare_120_prompt_remixer             | 120_prompt_remixer.ipynb                | taylorsamarel/00b-duecare-prompt-remixer-data-pipeline       | 120: Prompt Remixer                                                | exploration   | false | scripts/build_notebook_120.py
200  | duecare_200_cross_domain_proof         | 200_cross_domain_proof.ipynb            | taylorsamarel/duecare-cross-domain-proof                     | 200: Cross-Domain Proof                                            | comparison    | false | scripts/build_kaggle_notebooks.py
210  | duecare_210_oss_model_comparison       | 210_oss_model_comparison.ipynb          | taylorsamarel/gemma-4-vs-llama-vs-mistral-on-trafficking-safety | 210: Gemma 4 vs OSS Models                                      | comparison    | false | scripts/build_notebook_210_oss_model_comparison.py
220  | duecare_220_ollama_cloud_comparison    | 220_ollama_cloud_comparison.ipynb       | taylorsamarel/duecare-gemma-4-vs-6-oss-models-via-ollama-cloud | 220: Ollama Cloud Comparison                                     | comparison    | false | scripts/build_notebook_220_ollama_cloud_comparison.py
230  | duecare_230_mistral_family_comparison  | 230_mistral_family_comparison.ipynb     | taylorsamarel/duecare-gemma-4-vs-mistral-family              | 230: Mistral Family Comparison                                     | comparison    | false | scripts/build_notebook_230_mistral_family_comparison.py
240  | duecare_240_openrouter_frontier_comparison | 240_openrouter_frontier_comparison.ipynb | taylorsamarel/duecare-vs-large-cloud-models               | 240: OpenRouter Frontier Comparison                                | comparison    | false | scripts/build_notebook_240_openrouter_frontier_comparison.py
250  | duecare_250_comparative_grading        | 250_comparative_grading.ipynb           | taylorsamarel/duecare-comparative-grading                    | 250: Comparative Grading                                           | comparison    | false | scripts/build_grading_notebooks.py
260  | duecare_260_rag_comparison             | 260_rag_comparison.ipynb                | taylorsamarel/duecare-rag-comparison                         | 260: RAG Comparison                                                | comparison    | true  | scripts/build_showcase_notebooks.py
270  | duecare_270_gemma_generations          | 270_gemma_generations.ipynb             | taylorsamarel/duecare-22-gemma-generations                   | 270: Gemma 2 vs 3 vs 4 Generations                                 | comparison    | false | scripts/build_notebook_270_gemma_generations.py
300  | duecare_300_adversarial_resistance     | 300_adversarial_resistance.ipynb        | taylorsamarel/duecare-adversarial-resistance                 | 300: Adversarial Resistance                                        | adversarial   | false | scripts/build_showcase_notebooks.py
310  | duecare_310_prompt_factory             | 310_prompt_factory.ipynb                | taylorsamarel/duecare-adversarial-prompt-factory             | 310: Prompt Factory                                                | adversarial   | false | scripts/build_grading_notebooks.py
320  | duecare_320_supergemma_safety_gap      | 320_supergemma_safety_gap.ipynb         | taylorsamarel/duecare-uncensored-redteam                     | 320: Red-Team Safety Gap                                           | adversarial   | true  | scripts/build_notebook_320_supergemma_safety_gap.py
400  | duecare_400_function_calling_multimodal| 400_function_calling_multimodal.ipynb   | taylorsamarel/duecare-function-calling-multimodal            | 400: Function Calling and Multimodal                               | tools         | true  | scripts/build_showcase_notebooks.py
410  | duecare_410_llm_judge_grading          | 410_llm_judge_grading.ipynb             | taylorsamarel/duecare-llm-judge-grading                      | 410: LLM Judge Grading                                             | evaluation    | false | scripts/build_grading_notebooks.py
420  | duecare_420_conversation_testing       | 420_conversation_testing.ipynb          | taylorsamarel/duecare-conversation-testing                   | 420: Conversation Testing                                          | evaluation    | false | scripts/build_grading_notebooks.py
430  | duecare_430_rubric_evaluation          | 430_rubric_evaluation.ipynb             | taylorsamarel/duecare-rubric-anchored-evaluation             | 430: Rubric Evaluation                                             | evaluation    | false | scripts/build_grading_notebooks.py
440  | duecare_440_per_prompt_rubric_generator| 440_per_prompt_rubric_generator.ipynb   | taylorsamarel/duecare-rubric-pipeline                        | 440: Per-Prompt Rubric Generator                                   | evaluation    | false | scripts/build_notebook_440_per_prompt_rubric_generator.py
450  | duecare_450_contextual_worst_response_judge | 450_contextual_worst_response_judge.ipynb | taylorsamarel/duecare-context-judge                   | 450: Contextual Worst-Response Judge                               | evaluation    | false | scripts/build_notebook_450_contextual_worst_response_judge.py
500  | duecare_500_agent_swarm_deep_dive      | 500_agent_swarm_deep_dive.ipynb         | taylorsamarel/duecare-12-agent-gemma-4-safety-pipeline       | 500: Agent Swarm Deep Dive                                         | pipeline      | false | scripts/build_kaggle_notebooks.py
510  | duecare_510_phase2_model_comparison    | 510_phase2_model_comparison.ipynb       | taylorsamarel/duecare-phase-2-model-comparison               | 510: Phase 2 Model Comparison                                      | pipeline      | true  | scripts/build_notebook_510_phase2_model_comparison.py
520  | duecare_520_phase3_curriculum_builder  | 520_phase3_curriculum_builder.ipynb     | taylorsamarel/duecare-curriculum-builder                     | 520: Phase 3 Curriculum Builder                                    | pipeline      | false | scripts/build_notebook_520_phase3_curriculum_builder.py
530  | duecare_530_phase3_unsloth_finetune    | 530_phase3_unsloth_finetune.ipynb       | taylorsamarel/duecare-phase3-finetune                        | 530: Phase 3 Unsloth Fine-Tune                                     | pipeline      | true  | scripts/build_notebook_530_phase3_unsloth_finetune.py
600  | duecare_600_results_dashboard          | 600_results_dashboard.ipynb             | taylorsamarel/duecare-results-dashboard                      | 600: Results Dashboard                                             | results       | false | scripts/build_grading_notebooks.py
610  | duecare_610_submission_walkthrough     | 610_submission_walkthrough.ipynb        | taylorsamarel/duecare-submission-walkthrough                 | 610: Submission Walkthrough                                        | results       | false | scripts/build_kaggle_notebooks.py
```

The file must also export helper functions:

```python
def get_by_num(num: str) -> dict: ...
def get_by_kaggle_id(kaggle_id: str) -> dict: ...
def get_all() -> list[dict]: ...
```

## Step 2. Create a metadata generator

Create `scripts/generate_kernel_metadata.py` that:

a. Imports `NOTEBOOKS` from `scripts/notebook_registry.py`.
b. For each entry, writes `kaggle/kernels/<local_dir>/kernel-metadata.json`
   with the correct `id`, `title`, `code_file`, `language`, `kernel_type`,
   `is_private`, `enable_gpu`, `enable_tpu`, `enable_internet`,
   `dataset_sources`, `competition_sources`, `kernel_sources`, and
   `model_sources`.
c. Prints what it wrote.

This script replaces hand-editing metadata. Run it once, and every
`kernel-metadata.json` is consistent. Run it after any registry
change and metadata stays in sync.

Run it now. Check that all 28 metadata files are written and
`python scripts/publish_kaggle.py --dry-run push-notebooks` exits 0.

## Step 3. Update the publish script to read the registry

In `scripts/publish_kaggle.py`, replace the filesystem glob
discovery (`_notebook_dirs()`) with an import from
`notebook_registry.py`. The publisher should iterate
`NOTEBOOKS` and push each `kaggle/kernels/<local_dir>`. This
ensures the publisher and the metadata generator agree on
the set of notebooks.

If changing the publisher is too risky right now, at least add a
validation step at the top of `push-notebooks` that asserts every
directory the glob finds has a matching entry in `NOTEBOOKS`, and
vice versa.

## Step 4. Update all builder scripts to read the registry

Each builder script that writes metadata or references a Kaggle id
or title must import from `notebook_registry.py` instead of
hardcoding. At minimum, fix these files which contain stale
references:

- `scripts/build_index_notebook.py` (line 14: hardcodes
  `duecare_index`)
- `scripts/build_kaggle_notebooks.py` (lines 866-887: hardcodes
  `duecare_01_quickstart`, `duecare_02_cross_domain_proof`,
  `duecare_03_agent_swarm_deep_dive`,
  `duecare_04_submission_walkthrough`)
- `scripts/build_grading_notebooks.py` (lines 1712-1716: hardcodes
  `duecare_09_llm_judge`, `duecare_10_conversations`,
  `duecare_11_comparative`, `duecare_12_prompt_factory`,
  `duecare_13_rubric_eval`)
- `scripts/build_showcase_notebooks.py` (lines 863-865: hardcodes
  `duecare_05_rag_comparison`, `duecare_06_adversarial`,
  `duecare_08_fc_multimodal`)

For each, replace the hardcoded strings with lookups like:

```python
from notebook_registry import get_by_num
nb = get_by_num("410")
write_nb(nb["code_file"], cells, nb["local_dir"], nb["kaggle_id"], nb["title"])
```

After updating, rebuild all notebooks and rerun the metadata
generator to confirm consistency.

## Step 5. Update tests to read the registry

Fix `tests/test_kaggle_notebook_utils.py`:

- Line 22: `assert any(entry.dir_name == "duecare_index" ...)` must
  become `assert any(entry.dir_name == "duecare_000_index" ...)`.
- Line 23: `assert any(entry.code_file == "22_gemma_generations.ipynb" ...)`
  must become `assert any(entry.code_file == "270_gemma_generations.ipynb" ...)`.
- Line 29: `assert "forge_llm_core_demo.ipynb" in markdown` must be
  removed (the orphan was deleted).

Fix `tests/integration/test_publish_kaggle.py`:

- Lines 65-68: replace old directory names with new three-digit names.

After fixing, run `pytest tests/test_kaggle_notebook_utils.py tests/integration/test_publish_kaggle.py` and confirm both pass.

## Step 6. Generate docs from the registry

Create `scripts/generate_notebook_guide.py` that:

a. Imports `NOTEBOOKS` from `notebook_registry.py`.
b. Generates `docs/notebook_guide.md` with a table: Num, Title,
   Section, Kaggle Link, GPU, Purpose.
c. Generates `docs/current_kaggle_notebook_state.md` from the same
   data.

Run it. Both docs are now generated artifacts. They never drift
from the registry.

Update `docs/FOR_JUDGES.md` line 174 to use the new directory and
script names.

## Step 7. Publish to Kaggle

```
python scripts/publish_kaggle.py auth-check
python scripts/generate_kernel_metadata.py
python scripts/publish_kaggle.py push-notebooks
python scripts/publish_kaggle.py status-notebooks
```

If any kernel fails, note it. The original Kaggle ids should match
existing kernels, so most should succeed as version bumps.

For any UTF-8 errors on Windows, set `$env:PYTHONIOENCODING = "utf-8"`
before running.

## Step 8. Commit

```
git add scripts/notebook_registry.py scripts/generate_kernel_metadata.py scripts/generate_notebook_guide.py
git add kaggle/kernels/*/kernel-metadata.json
git add docs/current_kaggle_notebook_state.md docs/notebook_guide.md docs/FOR_JUDGES.md
git add tests/test_kaggle_notebook_utils.py tests/integration/test_publish_kaggle.py
git add scripts/build_*.py scripts/publish_kaggle.py
```

Message:

```
Add master notebook registry, generate all metadata from it

- scripts/notebook_registry.py: single source of truth for all 28
  notebook identities (local dir, Kaggle id, title, section, GPU)
- scripts/generate_kernel_metadata.py: writes kernel-metadata.json
  from the registry
- scripts/generate_notebook_guide.py: writes notebook_guide.md and
  current_kaggle_notebook_state.md from the registry
- Updated all builder scripts to import from registry
- Updated tests to use current directory and file names
- Restored original Kaggle ids so publishing updates existing kernels
```

## Why this fixes the root cause

Before: notebook identity was scattered across kernel-metadata.json,
builder scripts, tests, docs, and the publisher. Each rename pass
had to update 10+ files and missed some.

After: `scripts/notebook_registry.py` is the only place notebook
identity lives. Everything else is generated from it. A rename is
one line change in the registry, then run three generators.
