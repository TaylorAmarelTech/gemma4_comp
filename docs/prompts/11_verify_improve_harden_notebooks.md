# Verify, improve, and harden all 28 Kaggle notebooks

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

## Current state

28 notebooks under `kaggle/kernels/`, each mirrored in `notebooks/`.
14 are built by scripts under `scripts/build_notebook_*.py`. 14 are
raw `.ipynb` files with no builder. The registry prompt (prompt 10)
may or may not have been executed yet. Work with whatever state is on
disk. The authoritative inventory is
`docs/current_kaggle_notebook_state.md`.

## Quality audit results (already collected)

The table below shows every notebook's current metrics. Use this to
prioritize fixes. Do not re-run the audit; use these numbers.

```
Notebook                               | cells | code_cells | py_lines | max_cell_lines | has_pip | has_duecare_import
duecare_000_index                      |    11 |          1 |        1 |              1 |   no    |   no
duecare_010_quickstart                 |    14 |          6 |       97 |             35 |   no    |  yes
duecare_100_gemma_exploration          |    22 |         10 |      469 |             96 |   no    |  yes
duecare_110_prompt_prioritizer         |    14 |          7 |      226 |             66 |   no    |  yes
duecare_120_prompt_remixer             |    11 |          5 |      159 |             79 |   no    |  yes
duecare_200_cross_domain_proof         |    17 |          8 |      113 |             36 |   no    |  yes
duecare_210_oss_model_comparison       |    16 |          7 |      213 |             54 |   no    |   no
duecare_220_ollama_cloud_comparison    |    25 |         12 |      295 |             42 |   no    |  yes
duecare_230_mistral_family_comparison  |    25 |         12 |      323 |             39 |   no    |  yes
duecare_240_openrouter_frontier_comparison | 24 |        11 |      327 |             69 |   no    |  yes
duecare_250_comparative_grading        |    16 |          7 |     1308 |           1082 |   no    |  yes
duecare_260_rag_comparison             |    20 |         10 |     4940 |           2111 |   no    |  yes
duecare_270_gemma_generations          |    18 |          8 |      218 |             60 |   no    |   no
duecare_300_adversarial_resistance     |    17 |          8 |     3180 |           2121 |   no    |  yes
duecare_310_prompt_factory             |    18 |          8 |     7710 |           2752 |   no    |  yes
duecare_320_supergemma_safety_gap      |    25 |         12 |      388 |             71 |   no    |  yes
duecare_400_function_calling_multimodal|    11 |          4 |      122 |             53 |   no    |  yes
duecare_410_llm_judge_grading          |    21 |         10 |     6544 |           2428 |   no    |  yes
duecare_420_conversation_testing       |    17 |          8 |     4603 |           2355 |   no    |  yes
duecare_430_rubric_evaluation          |    18 |          8 |     4935 |           2891 |   no    |   no
duecare_440_per_prompt_rubric_generator|    21 |         10 |      461 |            134 |   no    |   no
duecare_450_contextual_worst_response_judge | 21 |      11 |      332 |             69 |   no    |   no
duecare_500_agent_swarm_deep_dive      |    20 |         11 |     2951 |           1414 |   no    |  yes
duecare_510_phase2_model_comparison    |    16 |          7 |      127 |             37 |   no    |   no
duecare_520_phase3_curriculum_builder  |    16 |          7 |      218 |            102 |   no    |   no
duecare_530_phase3_unsloth_finetune    |    17 |          8 |      170 |             36 |   no    |   no
duecare_600_results_dashboard          |    18 |          9 |     8230 |           1437 |   no    |   no
duecare_610_submission_walkthrough     |    14 |          6 |       95 |             40 |   no    |  yes
```

## Step 1. Fix critical issues (do these first for every notebook)

### 1a. Add pip install cell to every notebook

Zero of 28 notebooks have a pip install cell. Every notebook must
have one as its first code cell. The cell installs only the packages
that notebook actually imports:

```python
# For notebooks that import duecare packages:
!pip install -q duecare-llm-core==0.1.0 duecare-llm-domains==0.1.0

# For notebooks that also use models/tasks/agents:
!pip install -q duecare-llm-core==0.1.0 duecare-llm-models==0.1.0 duecare-llm-domains==0.1.0 duecare-llm-tasks==0.1.0

# For notebooks that need the full stack:
!pip install -q duecare-llm==0.1.0
```

Check `packages/duecare-llm-core/pyproject.toml` for the current
version and use that exact version.

For the 8 notebooks that do not import duecare at all (000, 210,
270, 430, 440, 450, 510, 520, 530, 600), add a pip install cell
anyway with the packages the notebook should be using, or add the
duecare import to replace inline logic where appropriate.

For builder-owned notebooks, edit the builder script and rebuild.
For raw `.ipynb` notebooks, edit the JSON directly.

### 1b. Break up mega code cells

These 9 notebooks have code cells over 1000 lines. Each of these
is a red flag for judges and a maintenance nightmare:

```
250_comparative_grading:        1082-line cell
260_rag_comparison:             2111-line cell
300_adversarial_resistance:     2121-line cell
310_prompt_factory:             2752-line cell
410_llm_judge_grading:          2428-line cell
420_conversation_testing:       2355-line cell
430_rubric_evaluation:          2891-line cell
500_agent_swarm_deep_dive:      1414-line cell
600_results_dashboard:          1437-line cell
```

For each, the fix is NOT to split the cell arbitrarily. The fix is:

a. Identify the reusable logic in the mega cell (scoring functions,
   model adapters, data loaders, chart builders).
b. Check if that logic already exists in `duecare.*` packages. If
   yes, replace the inline code with an import.
c. If the logic does not exist in `duecare.*`, extract it into the
   appropriate package (for example, a scoring helper goes to
   `duecare.tasks`, a chart builder goes to `duecare.publishing`).
d. After extraction, the notebook cell should be short: import, load
   data, call function, display result.
e. The target is no cell over 60 lines and no notebook over 300
   lines of Python. These 9 notebooks are far over both limits.

This is the biggest single improvement. Judges will skim these
notebooks. A 2891-line code cell looks like unstructured slop.

### 1c. Ensure every notebook has a clear header

Every notebook's first markdown cell should contain:

- A title with the three-digit number.
- One sentence stating what question the notebook answers.
- A small table with: Inputs, Outputs, Prerequisites, Pipeline
  position (which notebook comes before, which comes after).

Many notebooks already have something like this but with old
numbering. Update the references to use the current three-digit
numbers and current titles.

## Step 2. Verify structural correctness

For every notebook, confirm:

a. Valid JSON (already verified).
b. First cell is markdown with a title.
c. Second cell (or first code cell) is the pip install cell.
d. No cell references old directory names (duecare_00_, duecare_06_,
   duecare_phase2_, etc). Search and replace.
e. No cell references old notebook numbers (NB 00, NB 00a, NB 22,
   etc). Replace with new numbers.
f. Every `from duecare.* import X` resolves to a real symbol.
g. Every notebook that loads a Kaggle dataset references it by its
   full slug.
h. Every notebook that loads Gemma 4 uses the correct model slug.

## Step 3. Improve the index notebook (000)

The index notebook is the first thing a judge sees. It currently has
10 markdown cells and 1 trivial code cell. Improve it:

a. Replace the single code cell with a cell that installs duecare
   and prints the version:

```python
!pip install -q duecare-llm-core==0.1.0
import duecare.core
print(f"duecare.core version: {duecare.core.__version__}")
```

b. Ensure the markdown cells contain a complete table of all 28
   notebooks in numbered order with columns: Number, Title,
   Section, Kaggle Link, One-Sentence Purpose.

c. Add a "Quick Start" section pointing judges to notebook 010
   and the three most impressive notebooks (100 for Gemma baseline,
   300 for adversarial, 500 for agent swarm).

d. Add a "How to Read" section explaining the section numbering:
   000 orientation, 100 exploration, 200 comparison, 300 adversarial,
   400 tools, 500 pipeline, 600 results.

e. Link to the GitHub repo, the writeup, and the video script.

f. If `scripts/build_index_notebook.py` exists, edit that. If it
   still references `duecare_index` (the old directory), fix it.

## Step 4. Improve the quickstart notebook (010)

This is the second notebook judges open. It should work on a free
Kaggle CPU kernel in under 2 minutes. Verify:

a. The pip install cell works on a fresh kernel.
b. Every import resolves.
c. Every code cell produces visible output (not just side effects).
d. The narrative guides the reader through: install, import, inspect
   registries, run one evaluation, see results.
e. Total runtime under 2 minutes on CPU.

## Step 5. Verify every notebook runs in isolation

For the 19 notebooks that do NOT need a GPU (where `gpu` is false
in the audit table), create a simple test script at
`scripts/validate_notebooks.py` that:

a. For each non-GPU notebook, loads the `.ipynb` JSON.
b. Extracts all code cells.
c. Checks that every `import` statement references a package that
   is installed or installable.
d. Checks that no code cell references a file path that does not
   exist in the repo or on Kaggle datasets.
e. Reports pass/fail per notebook.

Do not actually execute the notebooks. Just validate imports and
file references. Execution happens on Kaggle.

## Step 6. Harden for judges

Judges will open a random notebook and click "Run All". Prepare:

a. Every notebook must handle missing GPU gracefully. If a notebook
   needs a GPU but runs on CPU, the first code cell after pip
   install should detect the hardware and print a clear message:
   "This notebook requires a T4 GPU. Enable it in Kaggle settings."
   Do not crash silently.

b. Every notebook must handle missing API keys gracefully. If a
   notebook uses Ollama, Mistral, or OpenRouter APIs, wrap the call
   in a try/except that prints "API key not set, skipping live
   evaluation. Cached results shown below." and falls back to
   displaying cached results.

c. Every notebook must produce at least one visible chart or table
   even if the live evaluation is skipped. Pre-compute and embed
   the cached output in the notebook's build script.

d. Every notebook's last cell must print a clear summary line:
   "Evaluation complete. N prompts scored. Mean: X. Pass rate: Y%."
   or equivalent for its purpose.

## Step 7. Update docs

After all fixes:

a. Regenerate `docs/current_kaggle_notebook_state.md`.
b. Regenerate `docs/notebook_guide.md`.
c. Update `README.md` notebook links if any changed.
d. Update `docs/review/notebook_publish_report.md` with the new
   quality status per notebook.

## Priority order

If time is limited, do these in order:

1. 1a (pip install cells) for all 28. Fastest, highest impact.
2. Step 3 (index notebook). Judges see it first.
3. Step 4 (quickstart). Judges try it second.
4. 1c (headers) for all 28. Fast, good signal.
5. 1b (mega cell breakup) for the worst offenders: 310 (7710 lines),
   600 (8230 lines), 410 (6544 lines). Most visible slop.
6. Step 6 (graceful failure handling). Prevents judge frustration.
7. Everything else.

## Output

After completing, write `docs/review/notebook_quality_report.md`
with:

- Per-notebook row: number, title, pip install added (yes/no),
  header updated (yes/no), max cell lines (before/after), total
  python lines (before/after), graceful failure (yes/no).
- Count of notebooks fully hardened vs partially fixed.
- List of remaining issues.
