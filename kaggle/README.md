# `kaggle/` — what gets shipped to kaggle.com

Everything in this folder is **delivered to Kaggle** as either a
notebook (kernel), a dataset, or a model. The actual *source code* of
the duecare framework lives in [`../packages/`](../packages/) — the
files here are bundles built from those packages, plus the kernel
sources judges open in Kaggle.

> **Quick reference:** [`kaggle/_INDEX.md`](./_INDEX.md) is the
> machine-readable roster of all 11 submission notebooks with file
> + wheel + publish status per row. Refresh whenever a notebook is
> added, removed, or pushed to Kaggle.

## Submission shape: 6 core + 5 appendix

The 2026 Gemma 4 Good Hackathon submission is structured as **6 core
notebooks** (sufficient for end-user deployment) plus **5 appendix
notebooks** (advanced extension workflows, research visualization,
agentic-research proof-of-concept, and a jailbroken-models comparison).
Judges should walk through the core notebooks IN ORDER — each builds
context for the next.

### Core notebooks (in canonical presentation order)

The chat playgrounds (1, 2) introduce the chat surface. The classification
and knowledge-builder playgrounds (3, 4) introduce the two pieces the
live-demo combines. The classifier dashboard (5) shows the production NGO
shape. The live-demo (6) is the polished end product.

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| 1 | [`chat-playground/`](./chat-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground | Raw Gemma 4 chat — NO harness. The baseline for the comparison story. |
| 2 | [`chat-playground-with-grep-rag-tools/`](./chat-playground-with-grep-rag-tools/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools | Same chat UI + 4 toggle tiles + Persona library + Pipeline modal. **The headline demo.** |
| 3 | [`content-classification-playground/`](./content-classification-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground _(publish pending)_ | Hands-on classification sandbox. Paste content, pick a schema (single-label / multi-label / risk-vector / custom), see the merged prompt + raw response + parsed JSON. **Pre-live-demo intro to classification.** |
| 4 | [`content-knowledge-builder-playground/`](./content-knowledge-builder-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground _(publish pending)_ | Hands-on knowledge-base sandbox. Add GREP rules, RAG docs, lookup-table entries; test what fires; export the full knowledge JSON. **Pre-live-demo intro to knowledge building.** |
| 5 | [`gemma-content-classification-evaluation/`](./gemma-content-classification-evaluation/) | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation | The polished Agency / NGO dashboard. Form-based submission → structured JSON with risk vectors + threshold-filterable history queue. |
| 6 | [`live-demo/`](./live-demo/) | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo | The user-facing live URL. Full safety-harness pipeline + 22-slide deck + audit Workbench. **Combines classification + knowledge-building (notebooks 3 + 4) into one polished product.** |

### Appendix notebooks (advanced extension + research)

These notebooks are **not required for deployment**. The first two
extend Duecare to new domains. The third is a visualization
playground. The fourth is a proof-of-concept for agentic web research.

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| A1 | [`prompt-generation/`](./prompt-generation/) | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation _(publish pending)_ | Use Gemma 4 to generate new evaluation prompts + 5 graded response examples per prompt (worst → best). Output feeds A2. |
| A2 | [`bench-and-tune/`](./bench-and-tune/) | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune _(publish pending)_ | Smoke benchmark + Unsloth SFT + DPO + GGUF + HF Hub push. Consumes A1 output (or any custom labeled JSONL). |
| A3 | [`research-graphs/`](./research-graphs/) | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs _(publish pending)_ | 6 interactive Plotly charts: entity graph, corridor Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO indicator hits, RAG corpus sunburst. CPU-only, ~30 sec runtime. |
| A4 | [`chat-playground-with-agentic-research/`](./chat-playground-with-agentic-research/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research _(publish pending)_ | Same chat UI as the GREP/RAG/Tools playground + a 5th toggle for **agentic web research**. Gemma 4 multi-step loop: web_search → web_fetch → wikipedia → done. All open-source, no API keys. **Proof-of-concept.** |
| A5 | [`chat-playground-jailbroken-models/`](./chat-playground-jailbroken-models/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models _(publish pending)_ | Same chat UI as core #2 + 4-toggle harness, but loads an **abliterated / cracked / uncensored Gemma 4 variant** (default: `dealignai/Gemma-4-31B-JANG_4M-CRACK`). Proves the harness still produces safe outputs even when the base model has had its refusals ablated. |

Each folder has its own `README.md` with paste-into-Kaggle
instructions, dataset attachments needed, GPU/Secrets requirements,
and expected runtime.

## Shared datasets

Cross-notebook datasets that aren't bundled into one folder:

| Folder | Slug | Used by |
|---|---|---|
| [`shared-datasets/trafficking-prompts/`](./shared-datasets/trafficking-prompts/) | `taylorsamarel/duecare-trafficking-prompts` | `bench-and-tune` (SFT/DPO target data) |
| [`shared-datasets/eval-results/`](./shared-datasets/eval-results/) | `taylorsamarel/duecare-eval-results` | `bench-and-tune` (write target — JSON exports of stock/SFT/DPO deltas) |

## Other folders

- [`kernels/`](./kernels/) — the **76-notebook research pipeline**
  (separate from the 6 core + 5 appendix hackathon submissions above).
  Each subfolder is one Kaggle kernel with its own metadata + .ipynb.
  Built from `notebooks/*.ipynb` via `python scripts/build_notebook_*.py`.
- [`models/`](./models/) — Kaggle Models artifacts (model cards +
  metadata for the fine-tuned weights).
- [`_archive/`](./_archive/) — legacy kernel sources we no longer
  push (e.g., `duecare_validation.py`, kept for reference).

## Source-of-truth vs build artifacts

Within each notebook folder:

- `kernel.py` — **source-of-truth, human-edited.** This is what
  judges paste into Kaggle. Track in git.
- `notebook.ipynb` — **built artifact**, regenerated by
  `scripts/push_kaggle_demo.py`. Track in git for transparency
  (judges can preview without running anything).
- `kernel-metadata.json` — **built artifact**, rewritten on every
  push. Track in git so the published kernel state is reproducible.
- `wheels/*.whl` — **built artifact**, copied from `dist/` after
  `python scripts/build_all_wheels.py`. Track in git so the dataset
  bundle is reproducible.

## Naming convention

Standardized in `reference_kaggle_naming_convention.md` (memory
file). Don't drift from these slugs/titles — judges scan the
attachments panel and parallel naming matters:

- Notebooks: `taylorsamarel/duecare-<purpose>` (e.g., `duecare-live-demo`)
- Wheel datasets: `taylorsamarel/duecare-<purpose>-wheels`
- Cross-notebook datasets: `taylorsamarel/duecare-<role>` (e.g.,
  `duecare-trafficking-prompts`, `duecare-eval-results`)
- HF Hub fine-tunes: `taylorscottamarel/Duecare-Gemma-4-<size>-<purpose>-v<version>[-suffix]`
