# `kaggle/` — what gets published to kaggle.com

Everything in this folder is **delivered to Kaggle** as either a
script kernel, a dataset, or a model. The actual *source code* of
the duecare framework lives in [`../packages/`](../packages/) — the
files here are bundles built from those packages, plus the kernel
sources judges open in Kaggle.

> **Quick reference:** [`kaggle/_INDEX.md`](./_INDEX.md) is the
> machine-readable roster of all 13 submission kernels (2 core + 11
> appendix) with file + wheel + publish status per row. Refresh
> whenever a kernel is added, removed, or pushed to Kaggle.

## Submission shape: 2 core + 11 appendix

The 2026 Gemma 4 Good Hackathon submission is structured as **2 core
kernels** (the omni playground + the focused live demo) plus
**11 appendix kernels** (specialised playgrounds, research
visualization, agentic-research proof-of-concept, jailbroken-models
comparison, lift regenerator, and the Unsloth fine-tune pipeline).
Judges land on the omni playground (#1) to see every capability,
then proceed to the live demo (#2) for the focused thesis demonstration.

### Core kernels (walk in this order)

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| **1** | [`duecare-exploration-workbench/`](./01-duecare-exploration-workbench/) ★ | https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench _(publish pending)_ | **The omni playground.** All 6 harness toggles (Persona / GREP 161 rules / RAG 46 docs / Imports / Tools 5 lookups / Online + deep-fetch) + 4 grading modes (Rule-Based / LLM-Based / Combined / Expert) + **9-variant Gemma 4 model selector** (E2B / E4B / 26B-A4B / 31B / 2 jailbroken / 3 cloud BYOK) + A/B Compare + retrieval-config + path-trace. |
| **2** | [`live-demo/`](./02-live-demo/) ★ | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo | **The user-facing live URL.** Full safety-harness pipeline + audit Workbench + the polished classification + knowledge-building product with the +56.5pp lift demonstration. |

### Appendix kernels (specialised + research)

The appendices are **not required for deployment** — the 2 core
kernels above cover the whole submission claim. They add
depth-of-engineering signal across model variants, sectors, fine-tune
pipelines, and research visualization.

### Appendix training path: two adapters, one Gemma 4 backbone

The training appendices now read as two related tracks rather than one
blended task:

1. **SafetyJudge / anti-exploitation track:** A6 generates synthetic
  exploitation prompts plus 0-4 graded response ladders. A7 can consume
  those JSONLs, train SFT/DPO LoRA adapters, and benchmark stock Gemma 4
  against the fine-tuned adapter in `eval_results.json`.
2. **PrivacyRedactor / anonymization track:** A6 also emits composite
  anonymization cases and gold redaction plans. These train or evaluate a
  separate privacy adapter that can run behind deterministic PII gates on
  a server-side or local intake path.

This is deliberately **not** one blended adapter. Anonymization has a
"leak nothing" failure mode, while anti-exploitation response quality is
reasoning, citation, and actionability. The story is one Gemma 4 backbone
with two DueCare skills routed by task. A11 is separate: it regenerates the
runtime harness OFF/ON lift, not stock-vs-fine-tuned model lift.

Kaggle memory is treated as a hard constraint: **one loaded model per
kernel run**. A6 writes a `duecare_a06_to_a07_manifest.json` plus a
`duecare_a06_to_a07_bundle.zip`; Taylor can publish that `/kaggle/working`
output as a Kaggle Dataset or download/re-upload it, then attach it to A7
with Add Data. The A6 served UI also tells the reader to open the printed
Cloudflare URL and download the ZIP; the A7 served UI accepts multiple ZIP,
JSONL, or JSON uploads into `/kaggle/working/a06_uploaded_bundles` for the
next rerun. To diversify the corpus, run A6 multiple times with separate
profiles such as `stock_harness_teacher`, `abliterated_adversary`, and
`human_curated_review`. A7 merges all attached/staged bundles by manifest.
The abliterated-Gemma profile is useful for adversarial prompts, harmful
negatives, and evaluator stress tests, but not as the source of **Best**
labels without harness or human review. A6's prompt-test rows carry both the
compatibility labels (`HARMFUL` → `BEST`) and the screen-facing review labels
(`WORST`, `BAD`, `NEUTRAL`, `GOOD`, `BEST`).

| # | Folder | Kaggle URL | Purpose |
|---|---|---|---|
| A1 | [`chat-playground/`](./A-01-chat-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground | Raw Gemma 4 chat — NO harness. The baseline that demonstrates the failure mode. |
| A2 | [`chat-playground-with-grep-rag-tools/`](./A-02-chat-playground-with-grep-rag-tools/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools | Harness ablation runner: same chat UI with GREP, RAG, Tools, and Imports toggles plus trace evidence for each layer. |
| A3 | [`content-classification-playground/`](./A-03-content-classification-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground _(publish pending)_ | Hands-on classification sandbox. Paste content, pick a schema, see the merged prompt + raw response + parsed JSON. |
| A4 | [`content-knowledge-builder-playground/`](./A-04-content-knowledge-builder-playground/) | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground _(publish pending)_ | Hands-on knowledge-base sandbox. Add GREP rules, RAG docs, lookup-table entries; test what fires; export the full knowledge JSON. |
| A5 | [`gemma-content-classification-evaluation/`](./A-05-gemma-content-classification-evaluation/) | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation | The polished Agency / NGO classifier dashboard. Form-based submission → structured JSON with risk vectors + threshold-filterable history queue. |
| A6 | [`prompt-generation/`](./A-06-prompt-generation/) | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation _(publish pending)_ | Two-track synthetic data generator: SafetyJudge prompts + 5-grade response ladders, plus PrivacyRedactor composite anonymization cases + gold redaction plans. Outputs feed A7. |
| A7 | [`bench-and-tune/`](./A-07-bench-and-tune/) | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune _(publish pending)_ | Adapter trainer + new-model benchmark: stock benchmark + **Unsloth SFT + DPO** from harness/A6 data + re-benchmark + GGUF + HF Hub push. Special Tech Track ($10k Unsloth + $10k llama.cpp) angle. Walkthrough at [`docs/bench_and_tune_walkthrough.md`](../docs/bench_and_tune_walkthrough.md). |
| A8 | [`research-graphs/`](./A-08-research-graphs/) | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs _(publish pending)_ | 6 interactive Plotly charts: entity graph, corridor Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO indicator hits, RAG corpus sunburst. CPU-only, ~30 sec runtime. |
| A9 | [`chat-playground-with-agentic-research/`](./A-09-chat-playground-with-agentic-research/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research _(publish pending)_ | Same chat UI as A2 + a 5th toggle for **agentic web research**. Gemma 4 multi-step loop: web_search → web_fetch → wikipedia → done. All open-source, no API keys. **Proof-of-concept.** |
| A10 | [`chat-playground-jailbroken-models/`](./A-10-chat-playground-jailbroken-models/) | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models _(publish pending)_ | Same chat UI as A2 + 4-toggle harness, but loads an **abliterated / cracked / uncensored Gemma 4 variant** (default: `dealignai/Gemma-4-31B-JANG_4M-CRACK` or `mlabonne/Gemma-4-E4B-it-abliterated`). Proves the harness still produces safe outputs even when the base model has had its refusals ablated. **The strongest "real, not faked" proof.** |
| A11 | [`grading-evaluation/`](./A-11-grading-evaluation/) | https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation _(publish pending)_ | **The runtime lift regenerator.** Runs N curated prompts through the same Gemma 4 weights twice (harness OFF vs ON) and grades both with the Rule-Based v3.10 grader. Emits JSON + markdown with provenance tuple `(model, git_sha, dataset_version)`. **The falsifiable +56.5pp number, regenerated from a git SHA.** |

Each folder has its own `README.md` with paste-into-Kaggle
instructions, dataset attachments needed, GPU/Secrets requirements,
and expected runtime.

## Shared datasets

Cross-kernel datasets that aren't bundled into one folder:

| Folder | Slug | Used by |
|---|---|---|
| [`shared-datasets/trafficking-prompts/`](./shared-datasets/trafficking-prompts/) | `taylorsamarel/duecare-trafficking-prompts` | `bench-and-tune` (SFT/DPO target data) |
| [`shared-datasets/eval-results/`](./shared-datasets/eval-results/) | `taylorsamarel/duecare-eval-results` | `bench-and-tune` (write target — JSON exports of stock/SFT/DPO deltas) |

## Other folders

- [`kernels/`](./kernels/) — archived generated/research notebook mirrors.
  The current judge-facing path is the 13 root script-kernel folders; use
  `_archive/kaggle-notebook-previews-2026-05-11/` for historical recovery.
  Older root-level `legacy_notebooks/` and `skunkworks/` mirrors are archived
  under `../_archive/legacy-research-2026-05-09/` and should only be restored
  for historical or migration work.
- [`models/`](./models/) — Kaggle Models artifacts (model cards +
  metadata for the fine-tuned weights).
- [`_archive/`](./_archive/) — legacy kernel sources we no longer
  push (e.g., `duecare_validation.py`, kept for reference).

## Source-of-truth vs build artifacts

Within each kernel folder:

- `kernel.py` — **source-of-truth, human-edited.** This is what
  judges paste into Kaggle. Track in git.
- `notebook.ipynb` — **archived preview artifact**, not active source.
  Notebook wrappers have been moved to
  [`../_archive/kaggle-notebook-previews-2026-05-11/`](../_archive/kaggle-notebook-previews-2026-05-11/).
  Do not recreate them in active `kaggle/*/` folders unless Taylor explicitly asks.
- `kernel-metadata.json` — **built artifact**, rewritten on every
  push. Track in git so the published kernel state is reproducible.
- `wheels/*.whl` — **built artifact**, copied from `dist/` after
  `python scripts/build_all_wheels.py`. Track in git so the dataset
  bundle is reproducible.

## Bootstrap rule for any included kernel

Every judge-facing Kaggle script kernel must explain and validate its own
runtime setup. The first executable block in every judge-facing Kaggle bundle
should:

1. Print required Kaggle settings: accelerator, internet, attached datasets /
  model sources, and required secrets such as `HF_TOKEN`.
2. Fail fast with a clear message if a required GPU, secret, wheel dataset, or
  model source is missing; a sample/offline fallback must be explicitly
  labeled as such.
3. Install DueCare from reproducible sources in order: attached Kaggle wheel
  dataset first, pinned PyPI releases when available, then immutable GitHub
  release wheel URLs or commit-pinned source archives as a fallback.
4. Validate imports and print the resolved DueCare version and install source
  before loading Gemma 4 or rendering demo output.
5. Never rely on `_reference/`, a local `.venv`, root-level legacy mirrors, or
  untracked repo files.

Installing from GitHub is acceptable only when the URL is immutable, for
example a versioned release asset or commit-pinned source archive. Do not use a
moving branch such as `main` for judge-facing Kaggle kernels.

## Naming convention

Standardized in `reference_kaggle_naming_convention.md` (memory
file). Don't drift from these slugs/titles — judges scan the
attachments panel and parallel naming matters:

- Kaggle kernels: `taylorsamarel/duecare-<purpose>` (e.g., `duecare-live-demo`)
- Wheel datasets: `taylorsamarel/duecare-<purpose>-wheels`
- Cross-kernel datasets: `taylorsamarel/duecare-<role>` (e.g.,
  `duecare-trafficking-prompts`, `duecare-eval-results`)
- HF Hub fine-tunes: `taylorscottamarel/Duecare-Gemma-4-<size>-<purpose>-v<version>[-suffix]`
