# Build, fix, and publish the Kaggle notebooks now

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

## Context

This is a Kaggle Gemma 4 Good Hackathon submission (due 2026-05-18).
There are 28 Kaggle notebooks under `kaggle/kernels/`, each with a
`kernel-metadata.json`. There are 14 build scripts under
`scripts/build_notebook_*.py` that generate notebooks programmatically.
The publish tool is `scripts/publish_kaggle.py`. The authoritative
inventory is `docs/current_kaggle_notebook_state.md`.

The notebooks currently have historical numbering (00, 00a, 00b, 01,
02, ..., 22, plus `index`, `phase2`, `phase3`). 16 kernel directories
have folder names that do not match their notebook filename. One local
notebook (`notebooks/forge_llm_core_demo.ipynb`) has no Kaggle kernel.

## What to do

Work through these steps in order. After each step, run the stated
check. Fix any failure before moving on.

### Step 1. Fix the 16 legacy alias mismatches

For each entry in `docs/current_kaggle_notebook_state.md` under
"Legacy Directory Aliases", rename the directory under
`kaggle/kernels/` so the folder name matches the notebook filename
(minus `.ipynb`), prefixed with `duecare_`. Update the
`kernel-metadata.json` inside each renamed folder so `id`, `title`,
and `code_file` are consistent.

Update the matching `notebooks/` mirror file if its name changed.
Update any `scripts/build_notebook_*.py` that references the old path.

Check: `python scripts/publish_kaggle.py --dry-run push-notebooks`
discovers all 28 kernels and exits 0.

### Step 2. Renumber notebooks into a clean scheme

Apply three-digit IDs with step-of-10 gaps, grouped by purpose.
Use this layout as a starting point, but adjust if a better grouping
makes sense for the content:

```
000  index (navigation hub)
010  quickstart

100  gemma exploration (baseline, free-form)
110  prompt prioritizer
120  prompt remixer

200  cross-domain proof
210  oss model comparison
220  ollama cloud comparison
230  mistral family comparison
240  openrouter frontier comparison
250  comparative grading
260  rag comparison
270  gemma generations (Gemma 2 vs 3 vs 4)
290  exploration and comparison summary (NEW if time allows)

300  adversarial resistance
310  adversarial prompt factory
320  supergemma safety gap / uncensored redteam
390  adversarial summary (NEW if time allows)

400  function calling and multimodal
410  llm judge grading
420  conversation testing
430  rubric evaluation
440  per-prompt rubric generator
450  contextual worst-response judge
490  evaluation methods summary (NEW if time allows)

500  agent swarm deep dive
510  phase 2 model comparison
520  phase 3 curriculum builder
530  phase 3 unsloth finetune
590  pipeline summary (NEW if time allows)

600  results dashboard
610  submission walkthrough
```

For each notebook:

a. Rename the `kaggle/kernels/` directory to
   `duecare_NNN_<snake_case>/`.
b. Rename the `.ipynb` inside to `NNN_<snake_case>.ipynb`.
c. Update `kernel-metadata.json`: set `id` to
   `taylorsamarel/duecare-NNN-<kebab-case>`, `code_file` to the
   new filename, `title` to `NNN: <Human Title>`.
d. Rename the `notebooks/` mirror to match.
e. Rename and update any `scripts/build_notebook_*.py` that writes
   to the old path.

Delete `notebooks/forge_llm_core_demo.ipynb` (its content is covered
by the quickstart notebook).

Check: `python scripts/publish_kaggle.py --dry-run push-notebooks`
discovers all renamed kernels and exits 0.

### Step 3. Rebuild all notebooks from build scripts

Run every `scripts/build_notebook_*.py` (after renaming). Confirm
each produces a valid `.ipynb` in both `notebooks/` and
`kaggle/kernels/`. Fix any build script that fails.

For the 14 notebooks that do not have build scripts, leave them as
raw `.ipynb` files for now. Do not create new build scripts in this
pass unless a notebook is clearly broken.

Check: every `.ipynb` under `kaggle/kernels/` is valid JSON and has
at least one code cell and one markdown cell.

### Step 4. Pin package versions in install cells

In every notebook (build script source or raw `.ipynb`), find the
`pip install` cell. Pin every duecare package to `==0.1.0`:

```python
!pip install duecare-llm-core==0.1.0 duecare-llm-domains==0.1.0
```

Check the version in `packages/duecare-llm-core/pyproject.toml` and
use whatever version is there.

Check: grep across all notebooks confirms no unpinned
`pip install duecare-llm` lines (without `==`).

### Step 5. Publish to Kaggle

Run:

```bash
python scripts/publish_kaggle.py push-notebooks
```

Then:

```bash
python scripts/publish_kaggle.py status-notebooks
```

Report the result for each kernel. If any kernel fails, note it and
move on. Do not retry more than twice.

### Step 6. Update the inventory

Rewrite `docs/current_kaggle_notebook_state.md` to reflect the new
state: new directory names, new Kaggle ids, new filenames, resolved
aliases, deleted orphan.

Update `docs/notebook_guide.md` with a table of all notebooks in
their new numbered order (columns: ID, title, Kaggle link, purpose
in one sentence).

Update `README.md` if it references old notebook slugs.

## Output

After all steps, write a short summary to
`docs/review/notebook_publish_report.md` with:

- Total notebooks published, total failed, total skipped.
- A table: new slug, new Kaggle id, status (published / failed),
  one-line note.
- List of any remaining issues for Taylor.

## Notes

- Build scripts are the source of truth for notebook content. Edit
  the build script, not the `.ipynb` JSON, when a build script
  exists.
- Kaggle ids use hyphens. Directory slugs use underscores.
- The renumbering scheme above is a suggestion. Adjust groupings if
  the actual notebook content fits better elsewhere. The goal is a
  clean, logical order that a judge can follow top to bottom.
- Focus on getting notebooks renamed, valid, and published. Do not
  refactor notebook content or add new evaluation logic. Ship what
  exists with clean names.
