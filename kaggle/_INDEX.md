# Kaggle notebook index — submission roster

> **Generated:** 2026-05-01. Machine-readable companion to
> [`kaggle/README.md`](./README.md) and [`docs/FOR_KAGGLE_JUDGES.md`](../docs/FOR_KAGGLE_JUDGES.md).
> Every row reflects what's in this directory tree right now.

## Build status — 2 core + 11 appendix = 13 submission notebooks

**Submission shape (2026-05-05):** judges land on the unified
`01-duecare-harness-chat` notebook to see every capability surface,
then proceed to `02-live-demo` for the focused thesis demonstration.
The 11 specialised notebooks (A1–A11) remain as appendix for depth
signal. Folder names use the `01-` / `02-` / `A-01-` ... `A-11-`
numbered prefix convention so the `ls kaggle/` listing reads in the
canonical presentation order.

| # | Folder | Files | Wheels (dataset slug) | Kernel slug | Publish |
|---|---|:-:|---|---|:-:|
| **1** | [`01-duecare-harness-chat/`](./01-duecare-harness-chat/) ★ omni playground | ✓ all 4 | `taylorsamarel/duecare-harness-chat-wheels` ✓ live | `taylorsamarel/duecare-harness-chat` | pending |
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

> **Note on slugs vs folders.** The folder name (`01-duecare-harness-chat/`)
> is local-organization only — Kaggle never sees it. The Kaggle
> kernel slug (`taylorsamarel/duecare-harness-chat`) is set by the
> `id` field inside `kernel-metadata.json` and is what appears in
> the public URL. Same for the dataset slug
> (`taylorsamarel/duecare-harness-chat-wheels`). Don't change either
> slug — they're already pushed and judges link to them.

**Files** column legend (each row reads `kernel.py + kernel-metadata.json + notebook.ipynb + README.md`):

| Symbol | Meaning |
|:-:|---|
| ✓ all 4 | All 4 canonical files present |
| partial | One or more files missing |
| — | Folder doesn't exist locally |

**Wheels**: each notebook ships a per-purpose `wheels/` subdirectory
with the wheel files it `pip install`s at kernel start. All are
present locally as of 2026-05-01.

**Publish**: `live` = the slug returned 200 on the last
`scripts/verify_kaggle_urls.py` run. `pending` = built locally,
ready to push, gated by Kaggle's daily push rate-limit.

## Per-notebook canonical files

Each submission notebook directory holds exactly four files:

| File | Purpose |
|---|---|
| `kernel.py` | Source-of-truth Python — what runs on Kaggle |
| `kernel-metadata.json` | Kaggle CLI metadata (slug, title, attached datasets, GPU/CPU) |
| `notebook.ipynb` | Jupyter export jupytext-synced from `kernel.py` |
| `README.md` | Per-notebook overview (purpose, runtime, what to look for) |

The `wheels/` subdirectory holds the wheels uploaded as a Kaggle
dataset attached to the notebook. The notebook installs from the
attached dataset path at startup.

## Other directories under kaggle/

| Path | Status | Notes |
|---|---|---|
| `kaggle/_archive/` | archived | Pre-canonical-layout legacy; superseded |
| `kaggle/kernels/` | research | The 76-notebook research pipeline; NOT part of the submission. Inventory: `docs/current_kaggle_notebook_state.md` |
| `kaggle/models/` | reference | Model card YAML + HF Hub push helpers |
| `kaggle/shared-datasets/` | reference | Shared assets pulled by multiple notebooks |
| `kaggle/README.md` | live | Human-readable overview of the 2 core + 11 appendix submission shape |

## How to update this file

Re-run the audit when notebooks are added, deleted, or pushed:

```bash
# Quick audit of file completeness across all 13 numbered folders
for d in kaggle/01-* kaggle/02-* kaggle/A-*; do
  count=$(ls -1 "$d" | grep -E "kernel.py|kernel-metadata.json|notebook.ipynb|README.md|^wheels$" | wc -l)
  echo "$d: $count files"
done
# Each line should be 5 (4 files + wheels dir)

# Verify Kaggle live URLs (manual, not part of CI)
python scripts/verify_kaggle_urls.py

# Push v3.16 wheels to Kaggle datasets (rate-limited; safe to re-run)
python scripts/push_v316_wheels.py --dry-run
python scripts/push_v316_wheels.py
```

Update the **Publish** column whenever a `kaggle kernels push`
returns 200 + the corresponding `kaggle datasets create / version`
returns 200.
