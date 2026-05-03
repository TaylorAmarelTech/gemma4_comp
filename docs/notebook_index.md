# Duecare — Notebook Index

> Single-page reference for all 11 submission notebooks. For the full
> 30-second / 2-minute / 5-minute verification paths, see
> [`FOR_JUDGES.md`](./FOR_JUDGES.md). For the complete writeup, see
> [`writeup_draft.md`](./writeup_draft.md).

---

## Submission shape

```
6 CORE (judges evaluate first; sufficient for end-user deployment)
  1. duecare-chat-playground                            raw Gemma 4 baseline
  2. duecare-chat-playground-with-grep-rag-tools        ★ headline demo
  3. duecare-content-classification-playground          classification sandbox
  4. duecare-content-knowledge-builder-playground       knowledge-base builder
  5. duecare-gemma-content-classification-evaluation    NGO/agency dashboard
  6. duecare-live-demo                                  ★ user-facing live URL

5 APPENDIX (optional; advanced extension + research)
  A1. duecare-prompt-generation                         generate new prompts
  A2. duecare-bench-and-tune                            SFT/DPO/GGUF/HF Hub
  A3. duecare-research-graphs                           6 Plotly charts
  A4. duecare-chat-playground-with-agentic-research     BYOK + browser agent
  A5. duecare-chat-playground-jailbroken-models         abliterated model proof
```

---

## Core notebooks

### 1. `duecare-chat-playground` — *raw Gemma 4 baseline*

| | |
|---|---|
| Folder | [`kaggle/chat-playground/`](../kaggle/chat-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground |
| Wheels | `taylorsamarel/duecare-chat-playground-wheels` ✓ live |
| LOC | 611 |
| GPU | T4 ×2 (default 31B; E2B/E4B run on single T4) |
| Cold start | ~30 sec for E4B; ~3-4 min for 31B |

Pure Gemma 4 chat playground — **no harness wired**. Persona / GREP /
RAG / Tools tiles are hidden via CSS injection (the kernel doesn't pass
the harness callables AND forces `app.state.persona_default = ""`).
This is the baseline for the comparison story: see how raw Gemma 4
responds to exploitation prompts before the harness transforms them
in #2.

### 2. `duecare-chat-playground-with-grep-rag-tools` — *★ headline demo*

| | |
|---|---|
| Folder | [`kaggle/chat-playground-with-grep-rag-tools/`](../kaggle/chat-playground-with-grep-rag-tools/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools |
| Wheels | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels` ✓ live |
| LOC | 557 |
| GPU | T4 ×2 |

Same chat UI as #1 with **4 toggleable safety tiles**: Persona /
GREP / RAG / Tools. Per-message customization via the Persona library
+ custom rule additions. Click `▸ View pipeline` on any response to
see the byte-for-byte prompt transformation in a 7-card modal. This is
the "watch what happens when I turn on GREP" demo the video centers on.

### 3. `duecare-content-classification-playground` — *classification sandbox*

| | |
|---|---|
| Folder | [`kaggle/content-classification-playground/`](../kaggle/content-classification-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground *(TBD — kernel needs creation)* |
| Wheels | `taylorsamarel/duecare-content-classification-playground-wheels` ✓ live |
| LOC | 815 |
| GPU | T4 ×2 |

Hands-on classification sandbox. Paste content, pick a schema mode
(single-label / multi-label / risk-vector / custom JSON Schema), see
the merged prompt Gemma actually receives + the raw response + the
parsed JSON envelope side-by-side. Lighter than #5 — no history queue,
no threshold filter, just iterate on classification mechanics.

### 4. `duecare-content-knowledge-builder-playground` — *KB builder*

| | |
|---|---|
| Folder | [`kaggle/content-knowledge-builder-playground/`](../kaggle/content-knowledge-builder-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground *(TBD)* |
| Wheels | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` ✓ live |
| LOC | 1082 |
| GPU | optional (pure-Python rule firing + BM25; Gemma only for the Test tab) |

Hands-on knowledge-base builder with 5 tabs: GREP rules / RAG corpus /
Tools / Test / Export-Import. Add new regex rules with live regex
preview, add new RAG documents (BM25 re-indexes automatically),
inspect lookup tables, test what fires on a sample text, export the
full knowledge JSON. Works WITHOUT a GPU — perfect for downstream NGO
partners extending Duecare to their corridor / domain on a laptop.

### 5. `duecare-gemma-content-classification-evaluation` — *NGO/agency dashboard*

| | |
|---|---|
| Folder | [`kaggle/gemma-content-classification-evaluation/`](../kaggle/gemma-content-classification-evaluation/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation |
| Wheels | `taylorsamarel/duecare-gemma-content-classification-evaluation-wheels` ✓ live |
| LOC | 526 |
| GPU | T4 ×2 |

The polished Agency / NGO dashboard. Form-based content submission
(text + optional document image — passport scan, fee receipt, complaint
form) → structured JSON classification with risk vectors +
threshold-filterable history queue + per-response Pipeline modal.
Ships with 16 example items (6 with embedded SVG document mockups
exercising Gemma 4's multimodal path).

### 6. `duecare-live-demo` — *★ user-facing live URL*

| | |
|---|---|
| Folder | [`kaggle/live-demo/`](../kaggle/live-demo/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| Wheels | `taylorsamarel/duecare-live-demo-wheels` ✓ live (16 wheels) |
| LOC | 1951 |
| GPU | T4 ×2 |

The polished deployed product. Full safety-harness pipeline (heuristic
prescan → GREP → RAG → tools → Gemma 4 verdict → audit trail) +
**22-slide deck** at `/overview` (with 7 appendices: Knowledge base,
Retrieval mechanism, Tool catalog, Tool call orchestration, Heuristic
taxonomy, Extensibility, Credits) + **Workbench** for paste-your-own-data
+ **Benchmark tab** with the bundled smoke_25 set + GGUF export option
for the llama.cpp track. Combines #3 + #4 in one polished surface.

---

## Appendix notebooks

### A1. `duecare-prompt-generation` — *generate new evaluation prompts*

| | |
|---|---|
| Folder | [`kaggle/prompt-generation/`](../kaggle/prompt-generation/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation *(TBD)* |
| Wheels | `taylorsamarel/duecare-prompt-generation-wheels` ✓ live |
| LOC | 646 |
| GPU | T4 ×1 |
| Runtime | ~50-75 min for 50 prompts × 5 grades = 250 graded responses |

Loads the 5 trafficking-prompts YAML rubrics (jurisdictional, financial,
victim-revictimization, etc.). For each scenario, asks Gemma 4 to
generate a new realistic adversarial test prompt in the same shape
as `smoke_25.jsonl`. Then for each generated prompt, generates 5
graded response examples on a worst→best scale (HARMFUL / INCOMPLETE
/ ADEQUATE / GOOD / BEST). Output JSONL feeds A2's SFT/DPO pipelines.

### A2. `duecare-bench-and-tune` — *SFT → DPO → GGUF → HF Hub*

| | |
|---|---|
| Folder | [`kaggle/bench-and-tune/`](../kaggle/bench-and-tune/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune *(TBD)* |
| Wheels | `taylorsamarel/duecare-bench-and-tune-wheels` ✓ live (6 wheels) |
| LOC | 1247 |
| GPU | T4 ×2 |
| Runtime | ~30-50 min end-to-end |

The science / methodology piece. Stock smoke benchmark → Unsloth SFT
(LoRA on harness-distilled prompt/response pairs) → DPO (chosen =
harness-on, rejected = harness-off) → re-benchmark to compute deltas →
GGUF Q8_0 export → HF Hub push of all three artifacts under
`taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0[-DPO|-GGUF]`.

### A3. `duecare-research-graphs` — *6 Plotly visualizations, CPU-only*

| | |
|---|---|
| Folder | [`kaggle/research-graphs/`](../kaggle/research-graphs/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs *(TBD)* |
| Wheels | `taylorsamarel/duecare-research-graphs-wheels` ✓ live |
| LOC | 667 |
| GPU | NOT required |
| Runtime | ~30 sec |

6 interactive Plotly charts rendered from the bundled harness data:
entity graph (NetworkX force-directed), corridor flow Sankey,
per-category benchmark pass-rate bars (stock vs fine-tuned),
fee-camouflage co-occurrence heatmap, ILO indicator hits per category,
RAG corpus sunburst by source family. CPU-only, no model load.

### A4. `duecare-chat-playground-with-agentic-research` — *BYOK + browser agent*

| | |
|---|---|
| Folder | [`kaggle/chat-playground-with-agentic-research/`](../kaggle/chat-playground-with-agentic-research/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research *(TBD)* |
| Wheels | `taylorsamarel/duecare-chat-playground-with-agentic-research-wheels` ✓ live |
| LOC | 1378 |
| GPU | T4 ×2 |
| Runtime | ~30 sec startup + ~10-15 sec per agentic turn |

Same chat UI as Core #2 + a **5th toggle for agentic web research**.
When ON, Gemma 4 multi-step loop (max 5 steps): decide → tool call
→ summarize → repeat. Tools: `web_search` (BYOK or no-key Playwright
browser via brave.com / duckduckgo.com / ecosia.org), `web_fetch`
(httpx + trafilatura), `wikipedia` (REST API). **BYOK panel** in the
sidebar lets users paste optional Tavily / Brave / Serper API keys
(stored in browser localStorage, never on server). PII filter on
every outbound query; audit log records sha256(query) only.

### A5. `duecare-chat-playground-jailbroken-models` — *abliterated model proof*

| | |
|---|---|
| Folder | [`kaggle/chat-playground-jailbroken-models/`](../kaggle/chat-playground-jailbroken-models/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-jailbroken-models *(TBD)* |
| Wheels | `taylorsamarel/duecare-chat-playground-jailbroken-models-wheels` ✓ live |
| LOC | 562 |
| GPU | T4 ×2 |
| Runtime | first run ~5-10 min (HF Hub download); subsequent ~30 sec |

Same chat UI + 4-toggle harness as Core #2, but loads an **abliterated
/ cracked / uncensored Gemma 4 variant** instead of the stock instruct
model. Default: `dealignai/Gemma-4-31B-JANG_4M-CRACK`. CONFIG block
supports 6 variants (mlabonne / huihui-ai / AEON-7 / TrevorS / dealignai).
Yellow banner top-left reminds the user the model is ablated. The
demo: toggle harness OFF → cracked model produces operational
exploitation advice; toggle harness ON → same model produces ILO
citations + NGO referrals. **Strongest "real, not faked" proof:**
the safety isn't in the weights, it's in the runtime.

---

## Wheels datasets — full inventory

All 11 wheels datasets are live on Kaggle as of 2026-04-29:

| Dataset slug | Wheels | Notes |
|---|---:|---|
| `duecare-chat-playground-wheels` | 3 | core, models, chat |
| `duecare-chat-playground-with-grep-rag-tools-wheels` | 3 | core, models, chat |
| `duecare-content-classification-playground-wheels` | 3 | core, models, chat |
| `duecare-content-knowledge-builder-playground-wheels` | 3 | core, models, chat |
| `duecare-gemma-content-classification-evaluation-wheels` | 3 | core, models, chat |
| `duecare-live-demo-wheels` | 16 | full stack incl. server, agents, training |
| `duecare-prompt-generation-wheels` | 3 | core, models, chat |
| `duecare-bench-and-tune-wheels` | 6 | core, models, domains, tasks, benchmark, training |
| `duecare-research-graphs-wheels` | 4 | core, models, chat, benchmark |
| `duecare-chat-playground-with-agentic-research-wheels` | 3 | core, models, chat |
| `duecare-chat-playground-jailbroken-models-wheels` | 3 | core, models, chat |

Each kernel auto-installs from `/kaggle/input/duecare-*-wheels/*.whl`
in its Phase 1 install step.

---

## Three deployment modes (cross-cuts the notebooks)

| Mode | Audience | Notebooks | Doc |
|---|---|---|---|
| Worker-side (local laptop) | individual workers / families | Core #2, #3, A4 | [`deployment_local.md`](./deployment_local.md) |
| Agency / NGO dashboard | NGO triage officers, hotlines | Core #5 | (in #5 notebook README) |
| Enterprise (Dockerized API) | platform integrations | (uses the chat package's `create_classifier_app` directly) | [`deployment_enterprise.md`](./deployment_enterprise.md) |

---

## Companion artifacts (not Kaggle notebooks, but referenced from the writeup)

| Artifact | Path | What it shows |
|---|---|---|
| Harness lift report | [`docs/harness_lift_report.md`](./harness_lift_report.md) | Mean **+56.5 pp** quality lift across 207/207 prompts when grading harness-ON vs harness-OFF responses against the cross-cutting `legal_citation_quality` rubric. Reproducible: `python scripts/rubric_comparison.py`. |
| Corpus coverage matrix | [`docs/corpus_coverage.md`](./corpus_coverage.md) | 2D coverage heatmaps (category × sector × corridor × ILO indicator) — surfaces high-priority gaps for new contributions. Reproducible: `python scripts/coverage_matrix.py`. |
| Cross-cutting rubric | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubrics_required.json#legal_citation_quality` | 12-criterion rubric measuring three dimensions stock LLMs commonly fail: jurisdiction-specific statutes, ILO/international regulations, substance-over-form analysis. Surface in the chat UI via `▸ Grade response`. |
| Per-prompt 5-tier rubric | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubrics_5tier.json` | 207 prompts × 5 hand-written tiers (worst/bad/neutral/good/best). Used as ground-truth for the harness-lift comparison and for fine-tune evaluation. |

## What's NOT in this index

- **The 76-notebook research pipeline** at `kaggle/kernels/` — that's the
  experimental code that produced the rules + corpus + benchmark, not
  the submission surface. See [`docs/notebook_guide.md`](./notebook_guide.md)
  for that map.
- **The 17 PyPI packages** at `packages/duecare-llm-*/` — see the
  package READMEs and [`docs/architecture.md`](./architecture.md).
- **HF Hub fine-tunes** under `taylorscottamarel/Duecare-Gemma-4-*` —
  pushed by A2's `bench-and-tune` kernel after a successful run.

---

> **Built with Google's Gemma 4** (base model:
> [google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
> and other IT variants). Used in accordance with the
> [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
