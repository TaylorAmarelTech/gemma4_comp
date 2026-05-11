# Kaggle notebook index — submission roster

> **Generated:** 2026-05-09. Machine-readable companion to
> [`kaggle/README.md`](./README.md) and [`docs/FOR_KAGGLE_JUDGES.md`](../docs/FOR_KAGGLE_JUDGES.md).
> Every row reflects what's in this directory tree right now.

## How to run a kernel without publishing to Kaggle

These notebooks are **not auto-published** right now. To run any of
the 13 locally on Kaggle yourself:

1. Open <https://kaggle.com> → New Notebook (Python).
2. Notebook settings → enable GPU (T4 is fine for E2B/E4B; 2×T4 or
   P100 for 31B / 26B-A4B).
3. **Add data** → search the `Wheels (dataset slug)` value from the
   table below (e.g. `taylorsamarel/duecare-harness-chat-wheels`)
   and attach it.
4. **Add model** (only if the row needs Gemma 4 weights) → search
   `google/gemma-4` and pick the variant the kernel expects.
5. Open the matching `kernel.py` from this folder, copy its full
   contents, paste into a single Kaggle code cell.
6. Run All. The kernel auto-detects the attached wheels dataset
   and installs from there.

Some folders also ship a `notebook.ipynb` carrying the same source
inside a JSON wrapper — that's a browser convenience for reading the
kernel inline. The kernel.py file is the source of truth.

## Build status — 2 core + 11 appendix = 13 submission notebooks

**Submission shape (2026-05-05):** judges land on the unified
`01-duecare-exploration-workbench` notebook to see every capability surface,
then proceed to `02-live-demo` for the focused thesis demonstration.
The 11 specialised notebooks (A1–A11) remain as appendix for depth
signal. Folder names use the `01-` / `02-` / `A-01-` ... `A-11-`
numbered prefix convention so the `ls kaggle/` listing reads in the
canonical presentation order.

| # | Folder | Files | Wheels (dataset slug) | Kernel slug | Publish |
|---|---|:-:|---|---|:-:|
| **1** | [`01-duecare-exploration-workbench/`](./01-duecare-exploration-workbench/) ★ omni playground | ✓ 3 (script) | `taylorsamarel/duecare-harness-chat-wheels` ✓ live | `taylorsamarel/duecare-harness-chat` | pending |
| **2** | [`02-live-demo/`](./02-live-demo/) ★ focused live demo | ✓ all 4 | `taylorsamarel/duecare-live-demo-wheels` ✓ live | `taylorsamarel/duecare-live-demo` | live |
| A1 | [`A-01-chat-playground/`](./A-01-chat-playground/) (baseline, harness OFF) | ✓ all 4 | `taylorsamarel/duecare-chat-playground-wheels` ✓ live | `taylorsamarel/duecare-chat-playground` | live |
| A2 | [`A-02-chat-playground-with-grep-rag-tools/`](./A-02-chat-playground-with-grep-rag-tools/) (4-toggle harness) | ✓ all 4 | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools` | live |
| A3 | [`A-03-content-classification-playground/`](./A-03-content-classification-playground/) | ✓ all 4 | `taylorsamarel/duecare-content-classification-playground-wheels` ✓ live | `taylorsamarel/duecare-content-classification-playground` | pending |
| A4 | [`A-04-content-knowledge-builder-playground/`](./A-04-content-knowledge-builder-playground/) | ✓ all 4 | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` ✓ live | `taylorsamarel/duecare-content-knowledge-builder-playground` | pending |
| A5 | [`A-05-gemma-content-classification-evaluation/`](./A-05-gemma-content-classification-evaluation/) | ✓ all 4 | `taylorsamarel/duecare-gemma-content-classification-evaluation-wheels` ✓ live | `taylorsamarel/duecare-gemma-content-classification-evaluation` | live |
| A6 | [`A-06-prompt-generation/`](./A-06-prompt-generation/) | ✓ all 4 | `taylorsamarel/duecare-prompt-generation-wheels` ✓ live | `taylorsamarel/duecare-prompt-generation` | pending |
| A7 | [`A-07-bench-and-tune/`](./A-07-bench-and-tune/) (Unsloth fine-tune) | ✓ all 4 | `taylorsamarel/duecare-bench-and-tune-wheels` ✓ live | `taylorsamarel/duecare-bench-and-tune` | pending |
| A8 | [`A-08-research-graphs/`](./A-08-research-graphs/) (Plotly graphs) | ✓ all 4 | `taylorsamarel/duecare-research-graphs-wheels` ✓ live | `taylorsamarel/duecare-research-graphs` | pending |
| A9 | [`A-09-chat-playground-with-agentic-research/`](./A-09-chat-playground-with-agentic-research/) (Playwright web search) | ✓ all 4 | `taylorsamarel/duecare-chat-playground-with-agentic-research-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-with-agentic-research` | pending |
| A10 | [`A-10-chat-playground-jailbroken-models/`](./A-10-chat-playground-jailbroken-models/) (abliterated baselines) | ✓ all 4 | `taylorsamarel/duecare-chat-playground-jailbroken-models-wheels` ✓ live | `taylorsamarel/duecare-chat-playground-jailbroken-models` | pending |
| A11 | [`A-11-grading-evaluation/`](./A-11-grading-evaluation/) (lift regenerator) | ✓ all 4 | `taylorsamarel/duecare-grading-evaluation-wheels` ✓ live | `taylorsamarel/duecare-grading-evaluation` | pending |

> **Note on slugs vs folders.** The folder name (`01-duecare-exploration-workbench/`)
> is local-organization only — Kaggle never sees it. The Kaggle
> kernel slug (`taylorsamarel/duecare-harness-chat`) is set by the
> `id` field inside `kernel-metadata.json` and is what appears in
> the public URL. Same for the dataset slug
> (`taylorsamarel/duecare-harness-chat-wheels`). Don't change either
> slug — they're already pushed and judges link to them.

**Files** column legend. Notebook kernels carry 4 source files
(`kernel.py + kernel-metadata.json + notebook.ipynb + README.md`).
Script kernels can ship as 3 (without `notebook.ipynb`) or 4 (with
the optional browsing wrapper); both are valid.

| Symbol | Meaning |
|:-:|---|
| ✓ all 4 | All 4 canonical files present (notebook kernel, or script kernel + browsing wrapper) |
| ✓ 3 (script) | Script kernel ships kernel.py + metadata + README only; no notebook.ipynb |
| partial | One or more required files missing |
| — | Folder doesn't exist locally |

**Wheels**: each notebook ships a per-purpose `wheels/` subdirectory
with the wheel files it `pip install`s at kernel start. All are
present locally as of 2026-05-01.

**Publish**: `live` = the slug returned 200 on the last
`scripts/verify_kaggle_urls.py` run. `pending` = built locally,
ready to push, gated by Kaggle's daily push rate-limit.

## Per-notebook canonical files

Each submission notebook directory holds these files:

| File | Required? | Purpose |
|---|---|---|
| `kernel.py` | always | Source-of-truth Python — what runs on Kaggle |
| `kernel-metadata.json` | always | Kaggle CLI metadata (slug, title, attached datasets, GPU/CPU) |
| `README.md` | always | Per-notebook overview (purpose, runtime, what to look for) |
| `notebook.ipynb` | required when `kernel_type: notebook`, optional otherwise | Jupyter wrapper carrying the same source kernel.py has, with a markdown intro cell. Useful for in-repo browsing of script kernels (e.g. A-11). |

Folders with `kernel-metadata.json` set to `kernel_type: script`
ship `kernel.py` directly to Kaggle. They MAY also include a
`notebook.ipynb` for in-repo browsing — judges who open the folder
in Jupyter/Colab see the same source as kernel.py with a markdown
intro on top. Currently `01-duecare-exploration-workbench/` ships
kernel.py only; `A-11-grading-evaluation/` ships both. Folders with
`kernel_type: notebook` always ship both.

The `wheels/` subdirectory holds the wheels uploaded as a Kaggle
dataset attached to the notebook. The notebook installs from the
attached dataset path at startup.

## Other directories under kaggle/

| Path | Status | Notes |
|---|---|---|
| `kaggle/_archive/` | archived | Pre-canonical-layout legacy; superseded |
| `kaggle/kernels/` | research | The 77-notebook research pipeline; NOT part of the submission. Inventory: `docs/current_kaggle_notebook_state.md` |
| `kaggle/models/` | reference | Model card YAML + HF Hub push helpers |
| `kaggle/shared-datasets/` | reference | Shared assets pulled by multiple notebooks |
| `kaggle/README.md` | live | Human-readable overview of the 2 core + 11 appendix submission shape |

## How to update this file

Re-run the audit when notebooks are added, deleted, or pushed:

```bash
# Quick audit of file completeness across all 13 numbered folders
for d in kaggle/01-* kaggle/02-* kaggle/A-*; do
  count=$(ls -1 "$d" | grep -E "kernel.py|kernel-metadata.json|notebook.ipynb|README.md|^wheels$" | wc -l)
  ktype=$(grep -o '"kernel_type"[[:space:]]*:[[:space:]]*"[^"]*"' "$d/kernel-metadata.json" 2>/dev/null | head -1)
  echo "$d: $count files ($ktype)"
done
# Notebook kernels should report 5 (4 files + wheels dir).
# Script kernels report 4 or 5 depending on whether they ship
# the optional notebook.ipynb wrapper. Both are valid.

# Verify Kaggle live URLs (manual, not part of CI)
python scripts/verify_kaggle_urls.py

# Push v3.16 wheels to Kaggle datasets (rate-limited; safe to re-run)
python scripts/push_v316_wheels.py --dry-run
python scripts/push_v316_wheels.py
```

Update the **Publish** column whenever a `kaggle kernels push`
returns 200 + the corresponding `kaggle datasets create / version`
returns 200.
