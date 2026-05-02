# Duecare Research Graphs (Appendix Notebook)

Appendix-style notebook (third). **Not** part of the core deployment
flow — this is a visualization + research playground for judges, NGO
partners, and researchers who want to inspect the harness data and
benchmark results visually.

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs *(TBD — kernel created 2026-04-29; not yet pushed)* |
| **Title on Kaggle** | "Duecare Research Graphs" |
| **Slug** | `taylorsamarel/duecare-research-graphs` |
| **Wheels dataset** | `taylorsamarel/duecare-research-graphs-wheels` *(TBD — needs upload)* |
| **Optional dataset** | `taylorsamarel/duecare-eval-results` (for chart 3) |
| **Models attached** | NONE (pure visualization) |
| **GPU** | NOT required |
| **Internet** | required only for plotly CDN bundle |
| **Secrets** | none |
| **Expected runtime** | ~30 sec end-to-end on CPU |

Built with Google's Gemma 4 ecosystem. The visualizations operate on
data Gemma 4 produces (the harness layer outputs, the benchmark
results) — Gemma itself doesn't need to be loaded for this kernel.
Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

## Why "appendix"

The four core notebooks deliver everything an end user needs for
deployment. The two earlier appendix notebooks
(`prompt-generation`, `bench-and-tune`) extend the system with new
prompts and a fine-tuned model. This third appendix notebook
visualizes what Duecare *already knows* — the 22 GREP rules, the
18-doc RAG corpus, the 7 corridor fee caps, the 16 fee-camouflage
labels, the 11 ILO indicators, the 4 NGO intake hotlines, and the
204 example prompts — so a researcher can spot patterns,
gaps, and biases in the rule base before deploying or extending it.

## What it renders (6 interactive Plotly charts)

1. **Entity graph** — force-directed network of recruiters,
   employers, money flows, passport-retention incidents, victim
   cases (composite), and the ILO/national statutes each violated.
   Built with NetworkX + Plotly. Drag nodes to reorganize.
2. **Corridor flow Sankey** — worker movement corridors (PH→HK,
   PH→SA, ID→HK, NP→Gulf, BD→Gulf, LK→Kuwait) with controlling
   fee-cap statutes (POEA MC 14-2017, BP2MI Reg 9/2020, Nepal FEA
   2007 §11(2), etc.) shown on each edge.
3. **Per-category benchmark bars** — stock vs fine-tuned pass rates
   across the 11 prompt categories. Reads from the optional
   `duecare-eval-results` dataset; gracefully skips if no benchmark
   runs are present yet.
4. **Fee-camouflage co-occurrence heatmap** — which of the 16 known
   fee-camouflage labels appear together across the 204 example
   prompts.
5. **ILO indicator hit counts per category** — which of the 11 ILO
   indicators of forced labour fire most often in each prompt
   category. Stacked bars.
6. **RAG corpus sunburst** — the 18-doc BM25 corpus organized by
   source family (ILO conventions, POEA MCs, BP2MI Reg, HK statutes,
   NGO briefs).

Output goes to `/kaggle/working/research_graphs/` as 6 standalone
HTML files plus an `index.html` that links to them. The kernel also
inlines each chart in the Kaggle notebook output via `IPython.display`.

## Files in this folder

```
research-graphs/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── notebook.ipynb       ← built artifact
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← dataset-metadata.json (3 wheels TBD)
```

## Status

**Built 2026-04-29.** All 6 chart functions are real (no
placeholders). Charts 1, 2, 4, 5, 6 render from the bundled harness
data; chart 3 is conditional on the `duecare-eval-results` dataset
being attached. The wheels dataset
(`duecare-research-graphs-wheels`) needs 3 wheels:
`duecare-llm-core`, `duecare-llm-chat`, `duecare-llm-benchmark` —
same minimal subset as the prompt-generation kernel.
