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

## Submission shape: 2 core + 11 appendix

The 2026 Gemma 4 Good Hackathon submission is structured as **2 core
notebooks** (the omni playground + the focused live demo) plus
**11 appendix notebooks** (specialised playgrounds, research
visualization, agentic-research proof-of-concept, jailbroken-models
comparison, lift regenerator, and the Unsloth fine-tune pipeline).
Judges land on the omni playground (#1) to see every capability,
then proceed to the live demo (#2) for the focused thesis demonstration.

### Core notebooks (walk in this order)

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| **1** | [`duecare-harness-chat/`](./01-duecare-harness-chat/) ★ | https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat _(publish pending)_ | **The omni playground.** All 6 harness toggles (Persona / GREP 161 rules / RAG 46 docs / Imports / Tools 5 lookups / Online + deep-fetch) + 4 grade modes (Universal / Expert / Deep / Combined) + **9-variant Gemma 4 model selector** (E2B / E4B / 26B-A4B / 31B / 2 jailbroken / 3 cloud BYOK) + A/B Compare + retrieval-config + path-trace. |
| **2** | [`live-demo/`](./02-live-demo/) ★ | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo | **The user-facing live URL.** Full safety-harness pipeline + audit Workbench + the polished classification + knowledge-building product with the +56.5pp lift demonstration. |

### Appendix notebooks (specialised + research)

The appendices are **not required for deployment** — the 2 core
notebooks above cover the whole submission claim. They add
depth-of-engineering signal across model variants, sectors, fine-tune
pipelines, and research visualization.

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| A1 | [`chat-playground/`](./A-01-chat-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground | Raw Gemma 4 chat — NO harness. The baseline that demonstrates the failure mode. |
| A2 | [`chat-playground-with-grep-rag-tools/`](./A-02-chat-playground-with-grep-rag-tools/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools | Same chat UI + 4 toggle tiles (no Online layer) + Persona library + Pipeline modal. **The original headline demo notebook.** |
| A3 | [`content-classification-playground/`](./A-03-content-classification-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground _(publish pending)_ | Hands-on classification sandbox. Paste content, pick a schema, see the merged prompt + raw response + parsed JSON. |
| A4 | [`content-knowledge-builder-playground/`](./A-04-content-knowledge-builder-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground _(publish pending)_ | Hands-on knowledge-base sandbox. Add GREP rules, RAG docs, lookup-table entries; test what fires; export the full knowledge JSON. |
| A5 | [`gemma-content-classification-evaluation/`](./A-05-gemma-content-classification-evaluation/) | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation | The polished Agency / NGO classifier dashboard. Form-based submission → structured JSON with risk vectors + threshold-filterable history queue. |
| A6 | [`prompt-generation/`](./A-06-prompt-generation/) | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation _(publish pending)_ | Use Gemma 4 to generate new evaluation prompts + 5 graded response examples per prompt (worst → best). Output feeds A7. |
| A7 | [`bench-and-tune/`](./A-07-bench-and-tune/) | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune _(publish pending)_ | Smoke benchmark + **Unsloth SFT + DPO** + GGUF + HF Hub push. Special Tech Track ($10k Unsloth + $10k llama.cpp) angle. Walkthrough at [`docs/bench_and_tune_walkthrough.md`](../docs/bench_and_tune_walkthrough.md). |
| A8 | [`research-graphs/`](./A-08-research-graphs/) | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs _(publish pending)_ | 6 interactive Plotly charts: entity graph, corridor Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO indicator hits, RAG corpus sunburst. CPU-only, ~30 sec runtime. |
| A9 | [`chat-playground-with-agentic-research/`](./A-09-chat-playground-with-agentic-research/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research _(publish pending)_ | Same chat UI as A2 + a 5th toggle for **agentic web research**. Gemma 4 multi-step loop: web_search → web_fetch → wikipedia → done. All open-source, no API keys. **Proof-of-concept.** |
| A10 | [`chat-playground-jailbroken-models/`](./A-10-chat-playground-jailbroken-models/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models _(publish pending)_ | Same chat UI as A2 + 4-toggle harness, but loads an **abliterated / cracked / uncensored Gemma 4 variant** (default: `dealignai/Gemma-4-31B-JANG_4M-CRACK` or `mlabonne/Gemma-4-E4B-it-abliterated`). Proves the harness still produces safe outputs even when the base model has had its refusals ablated. **The strongest "real, not faked" proof.** |
| A11 | [`grading-evaluation/`](./A-11-grading-evaluation/) | https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation _(publish pending)_ | **The lift regenerator.** Runs N curated prompts through Gemma 4 twice (harness OFF vs ON) and grades both with the universal v3.1 grader. Emits JSON + markdown with provenance tuple `(model, git_sha, dataset_version)`. **The falsifiable +56.5pp number, regenerated from a git SHA.** |

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
  (separate from the 2 core + 11 appendix hackathon submissions above).
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
