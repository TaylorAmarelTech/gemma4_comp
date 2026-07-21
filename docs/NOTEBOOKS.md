# DueCare notebooks, datasets, and the reusable kit

A single catalog of the public DueCare surfaces on Kaggle: the analysis and
applied notebooks, the open datasets they read, and the importable
`duecare-llm-kit` package. Every analysis notebook is CPU-safe and recomputes
its figures live from a public dataset -- no hidden state, attach the dataset
and re-run any cell.

## How to read the status column

- **live** -- published and reachable. It is linked below and from the public
  hub at [duecare-ai.com/data](https://duecare-ai.com/data) and
  [duecare-ai.com/kernels](https://duecare-ai.com/kernels).
- **queued** -- built in this repository (see `scripts/build_*_notebook.py`)
  and publishing on the next Kaggle window. Listed by name **without a link**
  so nothing here 404s. Some queued notebooks may already be live on Kaggle;
  they gain a link here once a public URL is verified.

Slugs follow `https://www.kaggle.com/code/taylorsamarel/<slug>` for notebooks
and `https://www.kaggle.com/datasets/taylorsamarel/<slug>` for datasets.

---

## Analysis

The harness-lift result, opened up. These read the public grade and text
datasets and recompute every figure.

| Status | Notebook | What it is |
|---|---|---|
| live | [Start Here: Harness-Lift Benchmark](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) | The benchmark front door: the headline lift and the cross-model board, recomputed live, with a guided tour of the whole collection. |
| live | [Does A Safety Harness Help? (flagship)](https://www.kaggle.com/code/taylorsamarel/duecare-does-a-safety-harness-help) | The publication-grade walk-through: thirteen sections, dozens of live charts, the +40.7 headline, and the honest counter-evidence. |
| live | [Per-Dimension Grades Explorer](https://www.kaggle.com/code/taylorsamarel/duecare-perdim-grades-explorer) | The exhaustive one-judge-call-per-dimension sweep: per-dimension A-E lift, sliceable by model and judge. |
| live | [Cross-Model Leaderboard Deep-Dive](https://www.kaggle.com/code/taylorsamarel/duecare-cross-model-leaderboard-deep-dive) | Every model ranked by raw lift and by ceiling-adjusted normalized gain, so a strong baseline is compared fairly with a weak one. |
| live | [Prompt And Response NLP Explorer](https://www.kaggle.com/code/taylorsamarel/duecare-prompt-and-response-nlp-explorer) | Text analytics over the prompt/response showcase: length, distinctive vocabulary (baseline vs harnessed), refusal and citation markers, readability. |
| live | [CoT Reasoning Explorer](https://www.kaggle.com/code/taylorsamarel/duecare-cot-reasoning-explorer) | Browse the chain-of-thought reasoning traces the harness produces, prompt by prompt. |
| live | [CoT Reasoning Analysis](https://www.kaggle.com/code/taylorsamarel/duecare-cot-reasoning-analysis) | Quantitative analysis of the reasoning chains: structure, length, and indicator / citation density. |
| live | [Harness Grades Data Card](https://www.kaggle.com/code/taylorsamarel/duecare-harness-grades-data-card) | Schema, provenance, and coverage of the grades panel, and how to load it. Read this before trusting the charts. |
| live | [CoT Reasoning Data Card](https://www.kaggle.com/code/taylorsamarel/duecare-cot-reasoning-data-card) | Schema and provenance of the chain-of-thought dataset. |
| queued | Prompt Intent And Attack Explorer (`duecare-prompt-intent-and-attack-explorer`) | The attack taxonomy: intent, framing, and category coverage of the adversarial prompt set. |
| queued | CoT Direction And Intent Explorer (`duecare-cot-direction-and-intent-explorer`) | Where each reasoning chain points: direction, intent, and refusal geometry. |
| queued | Corridor And Sector Atlas (`duecare-corridor-and-sector-atlas`) | Lift mapped across migration corridors and labor sectors, so you can see it holds beyond one geography. |

**Benchmark deep-dives** reached from the Start Here index (per-claim analyses
over the same grades panel): [reproduce the harness lift](https://www.kaggle.com/code/taylorsamarel/duecare-reproduce-harness-lift),
[where the harness helps most](https://www.kaggle.com/code/taylorsamarel/duecare-where-the-harness-helps-most),
[statistical robustness](https://www.kaggle.com/code/taylorsamarel/duecare-harness-statistical-robustness),
plus judge-agreement, methodology-and-controls, benchmark-convergence,
impact-and-coverage, and benchmark-as-training-signal (all reachable from the
Start Here index above).

## Applied use cases

Offline, paste-in workflows. No dataset required; they run as pure local
Python around the harness primitives.

| Status | Notebook | What it is |
|---|---|---|
| queued | NGO Case Triage (`duecare-ngo-case-triage`) | Paste a worker account, get an ILO-grounded triage: indicators, risk level, evidence gaps, next steps, referrals, and a draft note. |
| queued | Worker Self-Check (`duecare-worker-self-check`) | A worker pastes a suspicious message and gets a plain-language warning and next steps. |
| queued | Platform Moderation At Scale (`duecare-platform-moderation-at-scale`) | Screen risky recruitment posts and ads into a review queue with a reason for every decision. |
| queued | Chain Of Thought Generator (`duecare-chain-of-thought-generator`) | Turn a prompt into a structured, ILO-grounded reasoning chain. |
| queued | Regulator Compliance (`duecare-regulator-compliance`) | Compliance-monitoring view for labor ministries and regulators: corridor rules, fee caps, and an evidence trail. |
| queued | Developer Integration (`duecare-developer-integration`) | The software-to-software path: call the harness from your own code, structured request in and structured analysis out. |

## Advanced

| Status | Notebook | What it is |
|---|---|---|
| queued | The Entire System (`duecare-the-entire-system`) | End-to-end tour of the whole DueCare substrate: runtime, harness layers, knowledge, training, and judging. |
| queued | Semantic Landscape (`duecare-semantic-landscape`) | An embedding-space map of the prompt and knowledge corpus: clusters, gaps, and coverage. |
| queued | Cross-Industry Capabilities (`duecare-cross-industry-capabilities`) | The same harness across domains beyond trafficking (tax evasion, financial crime, and more). |

## Knowledge

| Status | Notebook | What it is |
|---|---|---|
| queued | Knowledge Base Explorer (`duecare-knowledge-base-explorer`) | Browse the GREP rules, the RAG corpus, the ILO instruments, and the corridor fee-caps behind the harness. |
| queued | Getting Started (`duecare-getting-started`) | A one-page hub: set DueCare up in minutes, plus a catalog of every published surface. |
| queued | Fact Check And Reproducibility (`duecare-fact-check-and-reproducibility`) | Verify the headline numbers and reproduce them from the public data. |

## Datasets

Open-licensed. Grades and scores carry no response text and no personal data;
the text datasets are synthetic composite scenarios with kernel metadata
scrubbed and a conservative PII scan applied.

| Status | Dataset | What it is |
|---|---|---|
| live | [Harness Benchmark Grades](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades) | The judged panel: one 0-100 score per (model, arm, prompt, judge) plus five A-E components. 85,417 grade rows across 7,973 prompts and 8 models. The primary evidence file. |
| live | [Harness Per-Dimension Grades](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-perdim-grades) | Higher resolution: one reasoned judge call per rubric dimension. Re-versioned as the exhaustive sweep grows. |
| live | [Cross-Model Harness Leaderboard](https://www.kaggle.com/datasets/taylorsamarel/duecare-cross-model-harness-leaderboard) | A citable flat CSV of the cross-model board: baseline, harnessed mean, raw lift, normalized gain, and win rate per model. |
| live | [Harness Lift Controls](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-lift-controls) | The placebo, negative-control, and applicability-audit results -- including the honest, inconclusive parts. |
| live | [Prompt Response Showcase](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) | The raw adversarial prompt plus the model's baseline, harness-core, and harness-full answers side by side. 1,087 prompts x 3 responses. |
| live | [CoT Reasoning](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) | Multi-perspective chain-of-thought reasoning traces grounded in the ILO forced-labour indicators. 2,020 chains, 1,740 train / 280 held out. |

Training corpora (measured-response, multiperspective, the proof corpus, and
the adapter / byte-model learning studies) are catalogued on the hub's
[Data & downloads](https://duecare-ai.com/data) page.

## Reproduce the headline in a few lines

Attach the [grades dataset](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades)
to a Kaggle notebook (or download the CSV) and read it with pandas:

```python
import pandas as pd, glob
grades = pd.read_csv(glob.glob("/kaggle/input/**/panel_grades.csv", recursive=True)[0])
piv = grades.groupby(["prompt_id", "arm"])["score_0_100"].mean().unstack()   # mean the judge panel
lift = (piv["harness_core"] - piv["baseline"]).dropna()                       # pair harnessed vs baseline
print(f"mean lift +{lift.mean():.1f} over {len(lift):,} paired prompts, {100 * (lift > 0).mean():.1f}% improved")
```

These are benchmark response-quality results under an LLM judge panel, not
field-detection metrics. Source and build scripts:
[github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp).

## The reusable kit: `duecare-llm-kit`

The indicator engine, chart helpers, HTML-report generator, corpus exporter,
and deterministic verifier that ship embedded in these notebooks -- packaged as
importable Python so you can use them without opening a notebook.

```bash
pip install duecare-llm-kit
```

```python
from duecare.kit import scan, generate_report

for hit in scan("The agency took my passport and I have not been paid."):
    print(hit["indicator"], "--", hit["ilo_ref"])

generate_report("panel.jsonl", "duecare_report.html")   # self-contained HTML lift report
```

Full API, CLI, and usage snippets: [`packages/duecare-llm-kit/README.md`](../packages/duecare-llm-kit/README.md).
