# DueCare — Research graphs (CPU-only) (#A08 appendix)

> AI infrastructure to combat migrant-worker exploitation. This appendix: visual research over corridors, GREP rules, RAG evidence, and benchmark deltas.

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | CPU-only visual research notebook for inspecting DueCare's entity graph, corridors, benchmark patterns, and RAG evidence. |
| **What it does** | Renders six Plotly views with open/download actions while reusing the warm-paper DueCare visual system. |
| **Demo path** | Run the notebook, open the chart dashboard, skim the six cards, and open the graph or Sankey view full screen. |
| **Audience** | Researcher. |
| **Inputs** | Optional /kaggle/input/duecare-eval-results dataset for chart 3 (placeholder rendered otherwise). CPU-only; no GPU required. |
| **Gemma 4 features** | Cross-prompt analysis (CPU-only, no Gemma load); visualizes the harness lift + corridor distribution from earlier kernels. |
| **Outputs** | Six interactive HTML charts, chart metadata API, and downloadable visualization artifacts. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, grading-lift appendix, and public website. |

Appendix-style notebook . **Not** part of the core deployment
flow — this is a visualization + research playground for judges, NGO
partners, and researchers who want to inspect the harness data and
benchmark results visually.

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs *(manual Kaggle publication target)* |
| **Title on Kaggle** | "DueCare Research Graphs" |
| **Slug** | `taylorsamarel/duecare-research-graphs` |
| **Wheels dataset** | `taylorsamarel/duecare-research-graphs-wheels` *(local wheels present; create/update dataset during manual Kaggle publish)* |
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

The 3 core + 24 appendix kernels deliver everything an end user needs for
deployment. The two earlier appendix notebooks
(`prompt-generation`, `bench-and-tune`) extend the system with new
prompts and a fine-tuned model. This third appendix notebook
visualizes what DueCare *already knows* — the 161 GREP rules, the
46-doc RAG corpus + 46-edge citation graph, the 7 corridor fee caps,
the 16+ fee-camouflage labels, the 11 ILO indicators, the 4 NGO intake
hotlines, and the 587 example prompts across 8 audience buckets — so
a researcher can spot patterns,
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
6. **RAG corpus sunburst** — the 46-doc BM25 corpus organized by
   source family (ILO conventions, POEA MCs, BP2MI Reg, HK statutes,
   NGO briefs).

Output goes to `/kaggle/working/research_graphs/` as 6 standalone
HTML files plus an `index.html` that links to them. The kernel also
inlines each chart in the Kaggle notebook output via `IPython.display`.

## Files in this folder

```
research-graphs/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← dataset-metadata.json + local wheels for manual Kaggle upload
```

## Status

**Built 2026-04-29.** All 6 chart functions are implemented. Charts
1, 2, 4, 5, 6 render from the bundled harness
data; chart 3 is conditional on the `duecare-eval-results` dataset
being attached. The wheels dataset
(`duecare-research-graphs-wheels`) needs 3 wheels:
`duecare-llm-core`, `duecare-llm-chat`, `duecare-llm-benchmark` —
same minimal subset as the prompt-generation kernel.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A08 appendix — Research graphs (CPU-only)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- **[#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)**
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Runtime vs weights safety study](../A-10-runtime-vs-weights-safety-study/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> A-11 grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation)** -- see the per-dimension lift behind the corridor + RAG charts you just explored.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
