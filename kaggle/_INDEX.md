# Kaggle notebook index — submission roster

> **Generated:** 2026-05-01. Machine-readable companion to
> [`kaggle/README.md`](./README.md) and [`docs/FOR_JUDGES.md`](../docs/FOR_JUDGES.md).
> Every row reflects what's in this directory tree right now.

## Build status — 6 core + 5 appendix = 11 submission notebooks

| # | Slug | Files | Wheels | kernel-metadata target | Publish |
|---|---|:-:|:-:|---|:-:|
| 1 | `chat-playground` | ✓ all 4 | ✓ | `taylorsamarel/duecare-chat-playground` | live |
| 2 | `chat-playground-with-grep-rag-tools` | ✓ all 4 | ✓ | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools` | live |
| 3 | `content-classification-playground` | ✓ all 4 | ✓ | `taylorsamarel/duecare-content-classification-playground` | pending |
| 4 | `content-knowledge-builder-playground` | ✓ all 4 | ✓ | `taylorsamarel/duecare-content-knowledge-builder-playground` | pending |
| 5 | `gemma-content-classification-evaluation` | ✓ all 4 | ✓ | `taylorsamarel/duecare-gemma-content-classification-evaluation` | live |
| 6 | `live-demo` | ✓ all 4 | ✓ | `taylorsamarel/duecare-live-demo` | live |
| A1 | `prompt-generation` | ✓ all 4 | ✓ | `taylorsamarel/duecare-prompt-generation` | pending |
| A2 | `bench-and-tune` | ✓ all 4 | ✓ | `taylorsamarel/duecare-bench-and-tune` | pending |
| A3 | `research-graphs` | ✓ all 4 | ✓ | `taylorsamarel/duecare-research-graphs` | pending |
| A4 | `chat-playground-with-agentic-research` | ✓ all 4 | ✓ | `taylorsamarel/duecare-chat-playground-with-agentic-research` | pending |
| A5 | `chat-playground-jailbroken-models` | ✓ all 4 | ✓ | `taylorsamarel/duecare-chat-playground-jailbroken-models` | pending |

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
| `kaggle/README.md` | live | Human-readable overview of the 6+5 submission shape |

## How to update this file

Re-run the audit when notebooks are added, deleted, or pushed:

```bash
# Quick audit of file completeness
for d in kaggle/{chat-playground,chat-playground-with-grep-rag-tools,content-classification-playground,content-knowledge-builder-playground,gemma-content-classification-evaluation,live-demo,prompt-generation,bench-and-tune,research-graphs,chat-playground-with-agentic-research,chat-playground-jailbroken-models}; do
  ls -1 "$d" | grep -E "kernel.py|kernel-metadata.json|notebook.ipynb|README.md|^wheels$" | wc -l
done
# Each line should be 5 (4 files + wheels dir)

# Verify Kaggle live URLs (manual, not part of CI)
python scripts/verify_kaggle_urls.py
```

Update the **Publish** column whenever a `kaggle kernels push`
returns 200 + the corresponding `kaggle datasets create / version`
returns 200.
