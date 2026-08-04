# Duecare â€” Kaggle Kernel Index

> Single-page reference for all 26 submission kernels (3 core + 23
> appendix). For the full 30-second / 2-minute / 5-minute verification
> paths, see [`FOR_PEER_REVIEW.md`](./FOR_PEER_REVIEW.md). For the
> complete writeup, see [`writeup_draft.md`](./writeup_draft.md).
>
> **Canonical mapping authority:** the "Submission shape" block right
> below is the source of truth. The per-kernel detail sections
> further down preserve their **original April-2026 section numbering**
> (when the project briefly used a 6-core / 5-appendix split before
> the 2-core / 11-appendix re-numbering). The kernel *folder* names
> are correct; the section *header numbers* are historical. Use the
> Submission shape block above, [`kaggle/_INDEX.md`](../kaggle/_INDEX.md),
> or [`kaggle/README.md`](../kaggle/README.md) for the canonical
> mapping when in doubt.
>
> Active source is `kernel.py`, not `.ipynb`. Historical notebook wrappers
> have been archived under `_archive/kaggle-notebook-previews-2026-05-11/`.

---

## Submission shape

```
2 CORE (judges evaluate first; the omni surface + the focused thesis demo)
  1. duecare-exploration-workbench                      â˜… omni playground
                                                          (6 toggles + 4 grade modes
                                                          + 9 model variants)
  2. duecare-live-demo                                  â˜… focused live URL with
                                                          the +56.5pp lift demonstration

11 APPENDIX (specialised playgrounds, research, fine-tune, lift regen)
  A1. duecare-chat-playground                           raw Gemma 4 baseline (no harness)
  A2. duecare-chat-playground-with-grep-rag-tools       harness ablation runner
  A3. duecare-content-classification-playground         classification sandbox
  A4. duecare-content-knowledge-builder-playground      knowledge-base builder
  A5. duecare-gemma-content-classification-evaluation   NGO/agency dashboard
  A6. duecare-prompt-generation                         two-track synthetic data generator
  A7. duecare-bench-and-tune                            adapter training + new-model benchmark
  A8. duecare-research-graphs                           6 Plotly charts
  A9. duecare-chat-playground-with-agentic-research     Playwright + DuckDuckGo + Wikipedia
  A10. duecare-a10-runtime-vs-weights-safety-study        abliterated-model proof
  A11. duecare-grading-evaluation                       runtime harness-lift regenerator
```

---

## Kernel Detail Sections

### 1. `duecare-chat-playground` â€” *raw Gemma 4 baseline*

| | |
|---|---|
| Folder | [`kaggle/A-01-chat-playground/`](../kaggle/A-01-chat-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground |
| Wheels | `taylorsamarel/duecare-chat-playground-wheels` âœ“ live |
| LOC | 611 |
| GPU | T4 Ã—2 (default 31B; E2B/E4B run on single T4) |
| Cold start | ~30 sec for E4B; ~3-4 min for 31B |

Pure Gemma 4 chat playground â€” **no harness wired**. Persona / GREP /
RAG / Tools tiles are hidden via CSS injection (the kernel doesn't pass
the harness callables AND forces `app.state.persona_default = ""`).
This is the baseline for the comparison story: see how raw Gemma 4
responds to exploitation prompts before the harness transforms them
in #2.

### 2. `duecare-chat-playground-with-grep-rag-tools` â€” *â˜… headline demo*

| | |
|---|---|
| Folder | [`kaggle/A-02-chat-playground-with-grep-rag-tools/`](../kaggle/A-02-chat-playground-with-grep-rag-tools/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools |
| Wheels | `taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels` âœ“ live |
| LOC | 557 |
| GPU | T4 Ã—2 |

Same chat UI as #1 with **4 toggleable safety tiles**: Persona /
GREP / RAG / Tools. Per-message customization via the Persona library
+ custom rule additions. Click `â–¸ View pipeline` on any response to
see the byte-for-byte prompt transformation in a 7-card modal. This is
the "watch what happens when I turn on GREP" demo the video centers on.

### 3. `duecare-content-classification-playground` â€” *classification sandbox*

| | |
|---|---|
| Folder | [`kaggle/A-03-content-classification-playground/`](../kaggle/A-03-content-classification-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground *(TBD â€” kernel needs creation)* |
| Wheels | `taylorsamarel/duecare-content-classification-playground-wheels` âœ“ live |
| LOC | 815 |
| GPU | T4 Ã—2 |

Hands-on classification sandbox. Paste content, pick a schema mode
(single-label / multi-label / risk-vector / custom JSON Schema), see
the merged prompt Gemma actually receives + the raw response + the
parsed JSON envelope side-by-side. Lighter than #5 â€” no history queue,
no threshold filter, just iterate on classification mechanics.

### 4. `duecare-content-knowledge-builder-playground` â€” *KB builder*

| | |
|---|---|
| Folder | [`kaggle/A-04-content-knowledge-builder-playground/`](../kaggle/A-04-content-knowledge-builder-playground/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground *(TBD)* |
| Wheels | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` âœ“ live |
| LOC | 1082 |
| GPU | optional (pure-Python rule firing + BM25; Gemma only for the Test tab) |

Hands-on knowledge-base builder with 5 tabs: GREP rules / RAG corpus /
Tools / Test / Export-Import. Add new regex rules with live regex
preview, add new RAG documents (BM25 re-indexes automatically),
inspect lookup tables, test what fires on a sample text, export the
full knowledge JSON. Works WITHOUT a GPU â€” perfect for downstream NGO
partners extending Duecare to their corridor / domain on a laptop.

### 5. `duecare-gemma-content-classification-evaluation` â€” *NGO & regulator scorecard*

| | |
|---|---|
| Folder | [`kaggle/A-05-gemma-content-classification-evaluation/`](../kaggle/A-05-gemma-content-classification-evaluation/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-content-classification-evaluation |
| Wheels | `taylorsamarel/duecare-gemma-content-classification-evaluation-wheels` âœ“ live |
| LOC | 526 |
| GPU | T4 Ã—2 |

The polished NGO & regulator evaluation surface. Form-based content submission
(text + optional document image â€” passport scan, fee receipt, complaint
form) â†’ structured JSON classification with risk vectors +
threshold-filterable history queue + per-response Pipeline modal.
Ships with 16 example items (6 with embedded SVG document mockups
exercising Gemma 4's multimodal path).

### 6. `duecare-live-demo` â€” *â˜… user-facing live URL*

| | |
|---|---|
| Folder | [`kaggle/02-live-demo/`](../kaggle/02-live-demo/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-live-demo |
| Wheels | `taylorsamarel/duecare-live-demo-wheels` âœ“ live (16 wheels) |
| LOC | 1951 |
| GPU | T4 Ã—2 |

The polished deployed product. Full safety-harness pipeline (heuristic
prescan â†’ GREP â†’ RAG â†’ tools â†’ Gemma 4 verdict â†’ audit trail) +
guided walkthrough at `/overview` + **Workbench** for paste-your-own-data
+ **Benchmark tab** with the bundled smoke_25 set + GGUF export option
for the llama.cpp track.

---

## Appendix Kernels

### A1. `duecare-prompt-generation` â€” *generate new evaluation prompts*

| | |
|---|---|
| Folder | [`kaggle/A-06-prompt-generation/`](../kaggle/A-06-prompt-generation/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-prompt-generation *(TBD)* |
| Wheels | `taylorsamarel/duecare-prompt-generation-wheels` âœ“ live |
| LOC | 646 |
| GPU | T4 Ã—1 |
| Runtime | ~50-75 min for 50 prompts Ã— 5 grades = 250 graded responses |

Loads the 5 trafficking-prompts YAML rubrics (jurisdictional, financial,
victim-revictimization, etc.). For each scenario, asks Gemma 4 to
generate a new realistic adversarial test prompt in the same shape
as `smoke_25.jsonl`. Then for each generated prompt, generates 5
graded response examples on a worstâ†’best scale (HARMFUL / INCOMPLETE
/ ADEQUATE / GOOD / BEST). Output JSONL feeds A2's SFT/DPO pipelines.

### A2. `duecare-bench-and-tune` â€” *SFT â†’ DPO â†’ GGUF â†’ HF Hub*

| | |
|---|---|
| Folder | [`kaggle/A-07-bench-and-tune/`](../kaggle/A-07-bench-and-tune/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune *(TBD)* |
| Wheels | `taylorsamarel/duecare-bench-and-tune-wheels` âœ“ live (6 wheels) |
| LOC | 1247 |
| GPU | T4 Ã—2 |
| Runtime | ~30-50 min end-to-end |

The science / methodology piece. Stock smoke benchmark â†’ Unsloth SFT
(LoRA on harness-distilled prompt/response pairs) â†’ DPO (chosen =
harness-on, rejected = harness-off) â†’ re-benchmark to compute deltas â†’
GGUF Q8_0 export â†’ HF Hub push of all three artifacts under
`taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0[-DPO|-GGUF]`.

### A3. `duecare-research-graphs` â€” *6 Plotly visualizations, CPU-only*

| | |
|---|---|
| Folder | [`kaggle/_archive/notebooks/A-08-research-graphs/`](../kaggle/_archive/notebooks/A-08-research-graphs/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-research-graphs *(TBD)* |
| Wheels | `taylorsamarel/duecare-research-graphs-wheels` âœ“ live |
| LOC | 667 |
| GPU | NOT required |
| Runtime | ~30 sec |

6 interactive Plotly charts rendered from the bundled harness data:
entity graph (NetworkX force-directed), corridor flow Sankey,
per-category benchmark pass-rate bars (stock vs fine-tuned),
fee-camouflage co-occurrence heatmap, ILO indicator hits per category,
RAG corpus sunburst by source family. CPU-only, no model load.

### A4. `duecare-chat-playground-with-agentic-research` â€” *BYOK + browser agent*

| | |
|---|---|
| Folder | [`kaggle/A-09-chat-playground-with-agentic-research/`](../kaggle/A-09-chat-playground-with-agentic-research/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-agentic-research *(TBD)* |
| Wheels | `taylorsamarel/duecare-chat-playground-with-agentic-research-wheels` âœ“ live |
| LOC | 1378 |
| GPU | T4 Ã—2 |
| Runtime | ~30 sec startup + ~10-15 sec per agentic turn |

Same chat UI as Core #2 + a **5th toggle for agentic web research**.
When ON, Gemma 4 multi-step loop (max 5 steps): decide â†’ tool call
â†’ summarize â†’ repeat. Tools: `web_search` (BYOK or no-key Playwright
browser via brave.com / duckduckgo.com / ecosia.org), `web_fetch`
(httpx + trafilatura), `wikipedia` (REST API). **BYOK panel** in the
sidebar lets users paste optional Tavily / Brave / Serper API keys
(stored in browser localStorage, never on server). PII filter on
every outbound query; audit log records sha256(query) only.

### A5. `duecare-a10-runtime-vs-weights-safety-study` â€” *abliterated model proof*

| | |
|---|---|
| Folder | [`kaggle/A-10-runtime-vs-weights-safety-study/`](../kaggle/A-10-runtime-vs-weights-safety-study/) |
| Notebook URL | https://www.kaggle.com/code/taylorsamarel/duecare-a10-runtime-vs-weights-safety-study *(TBD)* |
| Wheels | `taylorsamarel/duecare-a10-runtime-vs-weights-safety-study-wheels` âœ“ live |
| LOC | 562 |
| GPU | T4 Ã—2 |
| Runtime | first run ~5-10 min (HF Hub download); subsequent ~30 sec |

Same chat UI + 4-toggle harness as Core #2, but loads an **abliterated
/ cracked / uncensored Gemma 4 variant** instead of the stock instruct
model. No default and no bundled model: the operator supplies a checkpoint via
`DUECARE_STRIPPED_MODEL`.
Yellow banner top-left reminds the user the model is ablated. The
demo: toggle harness OFF â†’ cracked model produces operational
exploitation advice; toggle harness ON â†’ same model produces ILO
citations + NGO referrals. **Strongest "real, not faked" proof:**
the safety isn't in the weights, it's in the runtime.

---

## Wheels datasets â€” full inventory

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
| `duecare-a10-runtime-vs-weights-safety-study-wheels` | 3 | core, models, chat |

Each kernel auto-installs from `/kaggle/input/duecare-*-wheels/*.whl`
in its Phase 1 install step.

---

## Three Deployment Modes (Cross-Cuts The Kernels)

| Mode | Audience | Kernels | Doc |
|---|---|---|---|
| Individual worker (local laptop) | individual workers / families | Core #2, #3, A4 | [`deployment_local.md`](./deployment_local.md) |
| NGO & regulator | NGO triage officers, hotlines, labor inspectors | Core #5 | (in #5 kernel README) |
| Platform safety API (Dockerized API) | platform integrations | (uses the chat package's `create_classifier_app` directly) | [`deployment_enterprise.md`](./deployment_enterprise.md) |

---

## Companion artifacts (not Kaggle kernels, but referenced from the writeup)

| Artifact | Path | What it shows |
|---|---|---|
| Harness lift report | [`docs/harness_lift_report.md`](./harness_lift_report.md) | Mean **+56.5 pp** quality lift across 207/207 prompts when grading harness-ON vs harness-OFF responses against the cross-cutting `legal_citation_quality` rubric. Reproducible: `python scripts/rubric_comparison.py`. |
| Corpus coverage matrix | [`docs/corpus_coverage.md`](./corpus_coverage.md) | 2D coverage heatmaps (category Ã— sector Ã— corridor Ã— ILO indicator) â€” surfaces high-priority gaps for new contributions. Reproducible: `python scripts/coverage_matrix.py`. |
| Cross-cutting rubric | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubrics_required.json#legal_citation_quality` | 12-criterion rubric measuring three dimensions stock LLMs commonly fail: jurisdiction-specific statutes, ILO/international regulations, substance-over-form analysis. Surface in the chat UI via `â–¸ Grade response`. |
| Per-prompt 5-tier rubric | `packages/duecare-llm-chat/src/duecare/chat/harness/_rubrics_5tier.json` | 207 prompts Ã— 5 hand-written tiers (worst/bad/neutral/good/best). Used as ground-truth for the harness-lift comparison and for fine-tune evaluation. |

## What's NOT in this index

- **The former generated/research notebook mirrors** â€” these are archived under
  [`_archive/kaggle-notebook-previews-2026-05-11/`](../_archive/kaggle-notebook-previews-2026-05-11/), not part of the active submission surface.
  Older 52/74/77-kernel maps are historical archive context.
- **The 17 PyPI packages** at `packages/duecare-llm-*/` â€” see the
  package READMEs and [`docs/architecture.md`](./architecture.md).
- **HF Hub fine-tunes** under `taylorscottamarel/Duecare-Gemma-4-*` â€”
  pushed by A2's `bench-and-tune` kernel after a successful run.

---

> **Built with Google's Gemma 4** (base model:
> [google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
> and other IT variants). Used in accordance with the
> [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
