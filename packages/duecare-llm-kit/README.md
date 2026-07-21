# duecare-llm-kit

The reusable, downloadable **DueCare toolkit**: the ILO forced-labour indicator engine, the
DueCare-styled chart helpers, a self-contained **HTML harness-lift report generator**, and a
**data-corpus exporter** -- the same code embedded in the DueCare Kaggle notebooks, now packaged as
importable Python so you can `pip install` it, reuse it, generate HTML reports, and bundle data
corpuses without opening a notebook.

Part of the [DueCare](https://github.com/TaylorAmarelTech/gemma4_comp) migrant-worker safety harness
for Gemma 4. Import root is `duecare.kit` (PEP 420 namespace under `duecare`).

## Install

```bash
# from PyPI (namespace package under duecare.kit)
pip install duecare-llm-kit

# richer charts (seaborn + Plotly + scipy) and NLP add-ons are optional extras
pip install "duecare-llm-kit[viz]"     # seaborn, plotly, scipy
pip install "duecare-llm-kit[nlp]"     # scikit-learn, vaderSentiment, textstat
pip install "duecare-llm-kit[all]"

# or from a checkout of the repo
pip install -e packages/duecare-llm-kit
```

Core dependencies are just `numpy`, `pandas`, and `matplotlib`; everything runs offline and CPU-only
(no GPU, no model, no API key). seaborn/plotly/scipy are optional -- the helpers fall back to
matplotlib when they are absent.

## Usage

### 1. Scan text for ILO forced-labour indicators

The engine is a representative subset of the DueCare GREP layer (production has 451 rules across 11
languages) plus the ILO knowledge packs -- deterministic and grounded, each hit cites its ILO
instrument.

```python
from duecare.kit.engine import scan, generate_chain, risk_level

text = ("The recruitment agency took my passport when I arrived. I still have not been paid, "
        "and I must work off the placement fee debt before I can leave.")

hits = scan(text)
for h in hits:
    print(h["indicator"], "--", h["label"], "--", h["ilo_ref"])

print(risk_level(hits))            # ('HIGH', 'Multiple forced-labour indicators present')

for step_no, reasoning in generate_chain(text):
    print(step_no, reasoning)      # structured ILO-indicator chain of thought
```

### 2. Chart with the shared DueCare theme

Publication-grade helpers with one warm-paper / ink / civic-teal theme. Each returns a matplotlib
`Figure`; pass `show=False` to render without displaying.

```python
from duecare.kit.viz import radar, dumbbell, stat_cards, pretty_table

dumbbell(["gemma4:31b", "glm-5.2"], [48.4, 60.0], [89.1, 70.0],
         title="Baseline -> harness core")

radar(["A indicator", "B law", "C refuses", "D resources", "E privacy"],
      [("baseline", [8, 4, 20, 6, 3], None), ("core", [16, 9, 24, 12, 8], None)])
```

Also available: `slope`, `kde_hist`, `heatmap`, `ibar` (interactive Plotly with a matplotlib
fallback), and `stat_cards` KPI tiles.

### 3. Generate a shareable, offline HTML report

`generate_report` reads a graded panel (a DataFrame, a `panel.jsonl`, or a `panel_grades.csv`) and
writes one **self-contained** HTML file: a hero with the headline lift / win rate / n, a cross-model
board, a per-dimension (A-E) section, and charts embedded as base64 PNG data-URIs so the page opens
offline with no external assets. Numbers reproduce `scripts/analyze_full_results.py`.

```python
from duecare.kit.report import generate_report, report_from_jsonl

generate_report("reports/rich_lift/panel.jsonl", "duecare_report.html", model="gemma4:31b")
report_from_jsonl("reports/rich_lift/panel.jsonl", "duecare_report.html")   # convenience
```

The panel rows carry `model, arm, prompt_id, judge, score_0_100, components` (components is a per-row
A-E dict). Arms are `baseline`, `harness_core`, `harness_full`.

### 4. Package a downloadable data corpus

`export_corpus` copies dataset files into a folder and writes a machine-readable `MANIFEST.json`
(per file: name, rows, columns, sha256, byte size, license, one-line description) plus a human
`README.md` -- a self-describing, versionable corpus bundle.

```python
from duecare.kit.corpus import export_corpus, describe

export_corpus("corpus_out", ["reports/rich_lift/panel.jsonl", "data/grades.csv"])

import pandas as pd
describe(pd.read_json("reports/rich_lift/panel.jsonl", lines=True))   # schema + rows + null rates
```

## Command line

Both generators ship console entry points (and are runnable as modules):

```bash
# HTML report
python -m duecare.kit.report --panel reports/rich_lift/panel.jsonl --out duecare_report.html
duecare-kit-report --panel reports/rich_lift/panel.jsonl --out duecare_report.html

# corpus bundle
python -m duecare.kit.corpus --out corpus_out --sources reports/rich_lift/panel.jsonl data/grades.csv
duecare-kit-corpus --out corpus_out --sources reports/rich_lift/panel.jsonl
```

## Public API

| Module | Exports |
|---|---|
| `duecare.kit.engine` | `scan`, `risk_level`, `generate_chain`, `ILO_INDICATORS`, `ILO_REFS`, `PATTERNS`, `FEE_CAMOUFLAGE`, `HOTLINES`, `INDICATOR_QUESTIONS`, `LIFECYCLE`, `EVIDENCE_STATES`, `COUNTERFACTUALS` |
| `duecare.kit.viz` | `stat_cards`, `pretty_table`, `radar`, `dumbbell`, `slope`, `kde_hist`, `heatmap`, `ibar`, `apply_theme`, palette constants |
| `duecare.kit.report` | `generate_report`, `report_from_jsonl`, `aggregate` |
| `duecare.kit.corpus` | `export_corpus`, `describe` |

All names are also re-exported at the root, e.g. `from duecare.kit import scan, generate_report`.

## Provenance and honesty

This is the **same engine and viz code** embedded in the DueCare Kaggle notebooks (source of truth:
`scripts/_usecase_engine.py` and `scripts/_notebook_viz.py`), lifted into importable modules. The
report's lift numbers are rubric-scored proxy results under an LLM judge panel -- not real-world
detection rates -- and every generated report carries that honest-boundary footer. MIT licensed.
