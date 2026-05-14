# DueCare: Migrant-worker safety playground (#01 core)

> AI infrastructure to combat migrant-worker exploitation. This core kernel: every safety layer, every Gemma 4 variant, every grading mode in one workbench.

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator | 04 Researcher | 05 Developer / integration partner

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Unified workbench that exposes every Gemma 4 variant, harness layer, grading mode, and audit view from one Kaggle URL. |
| **What it does** | Starts the full workbench, lets judges toggle Persona / GREP / RAG / Tools / Grading, and shows response evidence with pipeline traces. |
| **Demo path** | Run `kernel.py`, open the cloudflared URL, select a fast Gemma 4 variant, and follow the 5-minute walkthrough below. |
| **Audience** | NGO & regulator, Researcher, and Developer / integration partner. |
| **Inputs** | 9-variant Gemma 4 model picker (E2B / E4B / 26B-A4B / 31B IT + abliterated variants) attached as Kaggle Models; bundled trafficking-prompts library. |
| **Gemma 4 features** | Five chat safety layers, local imports/evidence, 4 grading modes, and a 9-variant Gemma 4 model picker so judges can see the latency/quality tradeoff in one place. |
| **Outputs** | Live chat responses, A/B comparisons, retrieval traces, grading evidence, and `dc_log` events. |
| **Cross-links** | Continue to the focused live demo and appendix notebooks from the quick links at the bottom. |

> **The single configurable DueCare playground.** Every harness layer,
> every Gemma 4 variant, every grading mode visible from one URL.
>
> **Live URL** (manual Kaggle publication target): https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench

## Run it on Kaggle yourself

This folder publishes as a **script kernel** (`kernel.py` only, no
`notebook.ipynb`). To run it on Kaggle:

1. Open <https://kaggle.com>, choose **New Notebook**, then choose Python.
2. In **Notebook settings**, enable GPU (T4 single is fine for E2B/E4B;
   T4x2 or P100 for 26B-A4B / 31B).
3. Use **Add data** and search `taylorsamarel/duecare-harness-chat-wheels`
   and attach.
4. Use **Add model**, search `google/gemma-4`, and attach the variant you
   plan to load (defaults to `gemma-4-e4b-it`). You can also load via
   HuggingFace at runtime if you set `HF_TOKEN` as a Kaggle secret.
5. Open `kernel.py` from this folder, copy the entire file, paste into
   a single Kaggle code cell.
6. **Run All**. The cloudflared URL prints in the cell output before
   the model finishes loading.

Then proceed to the walkthrough below.

## Judge 5-minute walkthrough

1. **Open the notebook** and click "Run All". The server starts with
   no resident model so the public URL appears before GPU loading begins.
2. **Click the cloudflared URL** that prints. The chat UI opens with
   an in-browser model picker overlay.
3. **Pick a model**. E2B/E4B usually load in under a minute; 26B-A4B
   and 31B can take 5-10+ minutes on a first HuggingFace download.
   Keep the picker open and use **View logs** to see live loader phases.
4. **Verify the safety layers loaded** with `curl https://<your-url>/api/brand` (v0.14.2+) or `/api/health-check`. Expected counts include live GREP, RAG, tool, rubric, evaluator-question, citation-edge, and example-prompt totals. The `Safety layers` button in the top bar opens dedicated viewers for each layer (`/static/harness.html` index, grep-rules, rag-corpus, rag-graph, tools, online, persona).
5. **Click any of the 5 colored buttons** in the empty-state. They map to the 5 high-impact demo prompt categories:
   - **Green Headline lift:** the 5-indicator compound case (PHP+HK)
   - **Red Jailbreak:** DAN persona attempt
   - **Yellow Online demo:** recent POEA enforcement query
   - **Purple Compare:** multi-jurisdiction protections
   - **Blue Social-eng:** humanitarian framing trap
6. **Flip toggles** below the input. Try the same prompt with the five safety layers
   off (baseline) vs the five safety layers on (full harness). Or use the new **Compare**
   tab in the top bar for a one-click side-by-side. Expected: baseline
   gives a vague answer; full harness cites specific statutes + hotlines.
7. **Click `View pipeline`** on any response. Top of the modal shows
   a latency-budget bar (per-layer ms + Gemma generation time, with
   harness % of total). Each layer card below shows what fired. The
   **RETRIEVAL PATH TRACE** card surfaces the multi-stage retrieval
   decision (BM25, optional rerank, graph expansion, parent expansion).
8. **Click `Grade`** on any response. 4 modes:
   - **Rule-Based** (fast, deterministic, ~2s): current numeric
     multi-signal grader with citation grounding and numeric applicability checks
   - **Expert** (legacy per-category): for backwards compatibility
   - **LLM-Based** (LLM-as-judge, ~30-90s): sends response back to the
     loaded Gemma with one yes/no question per dimension; pulls
     evidence quotes from the response itself
   - **Combined** (Rule + LLM, ~30-90s): blended 50/50 with
     a disagreement panel showing dimensions where the two graders
     see different evidence (the high-information cases)

## Model picker and switching behavior

The browser picker is now the primary model-selection path. The server
starts with `gemma_call=None`, then `POST /api/load-model` starts a
background loader thread for the chosen variant. During load, the
picker polls `/api/load-model/status` and can open `/api/load-model/logs`
through the **View logs** button.

`GEMMA_MODEL_VARIANT` is still useful as a pre-run hint, especially for
cloud routes that should skip the Unsloth install phase:

```bash
%env GEMMA_MODEL_VARIANT=e4b-it     # default: single T4
%env GEMMA_MODEL_VARIANT=31b-it      # T4x2 in 4-bit (~5-10+ min first run)
%env GEMMA_MODEL_VARIANT=jailbroken-31b   # abliterated; harness still wins
%env GEMMA_MODEL_VARIANT=cloud-gemini    # BYOK (set GEMINI_API_KEY)
```

Runtime guardrails now enforced by the picker/API:

- Multiple clicks on model cards do not start duplicate CUDA loads.
- Switching variants mid-load is rejected because Unsloth/CUDA loads
  are not safely cancellable from Python.
- Once a model is resident in GPU memory, switching requires restarting
  the Kaggle cell to release memory cleanly.
- On success, the picker enters chat directly without a full page reload;
  if hydration lags, **Enter chat** remains as a manual fallback.
- On failure, logs open automatically and show the failing phase.

Full variant list (9 supported):

| Variant | HF id | Hardware | Notes |
|---|---|---|---|
| `e2b-it` | `unsloth/gemma-4-E2B-it` | single T4 | smallest on-device |
| `e4b-it` | `unsloth/gemma-4-E4B-it` | single T4 | **default** |
| `26b-a4b-it` | `unsloth/gemma-4-26B-A4B-it` | T4x2 (4-bit) | MoE |
| `31b-it` | `unsloth/gemma-4-31B-it` | T4x2 (4-bit) | flagship |
| `jailbroken-31b` | `dealignai/Gemma-4-31B-JANG_4M-CRACK` | T4x2 | abliterated; the strongest "real, not faked" proof |
| `jailbroken-e4b` | `mlabonne/Gemma-4-E4B-it-abliterated` | single T4 | smaller abliterated |
| `cloud-gemini` | Gemini 1.5 Flash API | CPU-only | needs `GEMINI_API_KEY` |
| `cloud-openai` | OpenAI-compat | CPU-only | needs `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| `cloud-ollama` | Ollama | CPU-only | needs `OLLAMA_HOST`, `OLLAMA_MODEL` |

## What lives where

- `kernel.py`: minimal orchestration: install wheels, load model
  variant, wire harness, start FastAPI + cloudflared
- `wheels/`: duecare-llm-chat / -core / -models (bundled into the
  Kaggle dataset `taylorsamarel/duecare-harness-chat-wheels`)
- `notebook.ipynb`: archived preview wrapper; paste `kernel.py` into Kaggle as described above

All harness content (GREP rules, RAG docs, tools, rubric dimensions,
and configured LLM-judge questions) lives in the chat package wheel:
not in `kernel.py`. Bumping the dataset version updates everything;
the kernel.py doesn't need to change.

## Recent review: loader observability and UI hardening

This pass focused on making slow/non-standard model loads visible and
safe enough for judges to test live:

- Added an in-memory model-load event ring with timestamps, elapsed
  seconds, phase, severity, and message.
- Mirrored loader events to Kaggle stdout so notebook logs and browser
  logs tell the same story.
- Added `/api/load-model/logs` and expanded `/api/load-model/status`
  with `phase`, `eta`, `last_log`, `active_model`, and recent log
  events.
- Logged the specific load phases that matter for 31B and abliterated
  repos: GPU inventory, torch/Unsloth import, repo resolution, local
  Kaggle attachment vs HF download, `FastModel.from_pretrained`, CUDA
  memory summary, chat-template setup, and final readiness.
- Added traceback-tail logging for import/load failures so non-standard
  repos have actionable failure context instead of a silent spinner.
- Updated 26B/31B ETA language to reflect the observed slow path:
  first-run HF download + shard mapping + 4-bit quantization + CUDA
  memory planning can take 5-10+ minutes.
- Added disabled/loading/loaded card states in the picker to prevent
  duplicate loads and make the active selection obvious.
- Replaced the previous ready-page reload with a direct overlay close,
  badge refresh, harness probe, and input focus.
- Kept the shutdown and compact-layout overlays separate from the
  model picker so each UI injection remains scoped and debuggable.

## Suggested test session (10 minutes)

| Time | Action | What you should see |
|---|---|---|
| 0:00 | Click the cloudflared URL | Model picker opens before chat |
| 0:15 | Pick E4B, then click **View logs** | Live phases appear; card shows loading state |
| 1:15 | Picker auto-enters chat when ready | Chat UI loads with empty state showing 5 colored quick-action buttons |
| 1:30 | Click "Headline lift", toggle the five safety layers ON, then Send | Response cites ILO C029 section 1, POEA MC 14-2017, HK Cap. 57 section 32, and a vetted contacts-pack reference |
| 2:30 | Click `View pipeline` on the response | Latency bar shows per-layer ms; cards show GREP hits + RAG docs + tool results + online results |
| 3:30 | Click `Grade`, then switch to **Combined** | Rule-Based score + LLM-Based score + agreement % + disagreement table |
| 4:30 | Click `Safety layers` in top bar | Opens `/static/harness.html`: layer cards with live counts; click any to drill into the dedicated viewer |
| 6:00 | Click "Jailbreak", toggle the five safety layers OFF, then Send | Should refuse but vaguely (this is baseline Gemma) |
| 7:00 | Same prompt with the five safety layers ON | Refuses with citations + contact pathways |
| 8:00 | Click `Grade`, then select **LLM-Based** mode | LLM judge sends the configured evaluator questions back to Gemma; per-dimension verdicts include evidence quotes from the response |
| 10:00 | `curl https://<url>/api/brand` | Returns chat package version, layer metadata, live counts for GREP, RAG, tools, rubric dimensions, evaluator questions, citations, and examples |

## Full UI Audit Targets

Use this checklist when reviewing the polished workbench:

1. Top chrome: global model status, model picker, DueCare hub link, page width, and consistent navigation.
2. Chat: example picker, harness tiles, input composer, image upload, response cards, pipeline modal, and grade modal.
3. Compare: direct navigation to `/static/compare.html`, same example picker behavior as chat, inherited model status, side-by-side outputs, and prompt visibility.
4. Bulk File Review: upload controls, sample ZIP, graph-chat prompts, extracted entities, document/page rows, media queue, and export links.
5. Knowledge Extraction: target object selector, draft envelope output, validation notes, and promotion pathway to local knowledge packs.
6. Search: search-safety sanitization, optional search call, query trace, redaction summary, and backend status.
7. Safety Layers: harness index, persona, GREP rules, RAG corpus, RAG graph, tools, online/search, hotlines, contacts, and all-tools pages.
8. Evaluation: rule judge, LLM judge, combined judge, dynamic applicability, contact grounding, and N/A behavior driven by the prompt rather than by response verbosity.

## Submission context

This is **core notebook #1** of 3:

- **#1** `duecare-exploration-workbench` (this notebook): flip every toggle,
  switch every model
- **#2** `duecare-live-demo`: focused, scripted demonstration of the
  +56.5pp lift thesis
- **#3** `duecare-video-pitch`: in-app slides + presenter remote + setup
  modes for the video walkthrough

The other 25 notebooks are appendix (A-00..A-24): A-00 is the omni
experiment workbench, followed by specialised playgrounds,
the SafetyJudge / PrivacyRedactor training pipeline, research graphs,
agentic web research, jailbroken-models proof, lift regenerator, and the
zero-inference Gemma 4 feature showcases (long-context, streaming,
function-calling Coordinator). See `docs/FOR_PEER_REVIEW.md` for the full
submission roster.

## Troubleshooting

- **"GPU not available"** with on-device variant: switch to
  `cloud-gemini` / `cloud-openai` / `cloud-ollama` (no GPU needed)
- **31B/26B-A4B fails to load:** set `HF_TOKEN` (these are gated)
- **31B looks stuck:** open **View logs** in the picker. If the last
  phase is `from_pretrained`, it is likely still downloading, mapping
  shards, quantizing, or planning CUDA memory; first runs can take
  5-10+ minutes.
- **Clicked multiple models:** only the first click is honored. Mid-load
  switching is intentionally blocked; restart the cell to change course.
- **Picker does not advance after ready:** click **Enter chat**. The
  API model is ready; the button is a hydration fallback.
- **Online layer returns no results:** DuckDuckGo HTML can rate-
  limit; for Brave Search / Playwright agentic search use appendix A9
  (`duecare-chat-playground-with-agentic-research`)
- **Combined-mode grade is slow:** it runs one configured LLM-judge call per applicable dimension
  against the loaded model (one per applicable rubric dimension);
  ~30-90s for E4B, several minutes for 31B
- **Cold-boot timeout:** the unsloth-stack install can take 90s on
  a fresh Kaggle worker; subsequent restarts skip via marker file

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** this notebook.
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A02 appendix: 4-toggle harness playground](../A-02-chat-playground-with-grep-rag-tools/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#01 core: Migrant-worker safety playground**.

- **[#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)**
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A00 appendix: Omni experiment workbench](../A-00-omni-experiment-workbench/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
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

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)**: the full chat playground with five safety layers, local imports/evidence, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)**: focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step: A-11 grading-evaluation](https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation)**: regenerate the headline +56.5pp lift number live from a git SHA.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)**: knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
