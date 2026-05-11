# DueCare — Migrant-worker safety playground (#01 core)
<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator · 04 Researcher · 05 Developer / integration partner

> **The single configurable Duecare playground.** Every harness layer,
> every Gemma 4 variant, every grading mode visible from one URL.
>
> **Live URL** (after publish): https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat

## Run it on Kaggle yourself (until the live URL is back up)

This folder ships as a **script kernel** (`kernel.py` only, no
`notebook.ipynb`). To run it on Kaggle:

1. <https://kaggle.com> → **New Notebook** → Python.
2. **Notebook settings** → enable GPU (T4 single is fine for E2B/E4B;
   T4×2 or P100 for 26B-A4B / 31B).
3. **Add data** → search `taylorsamarel/duecare-harness-chat-wheels`
   and attach.
4. **Add model** → search `google/gemma-4` and attach the variant you
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
4. **Verify the safety layers loaded** with `curl https://<your-url>/api/brand` (v0.14.2+) or `/api/health-check`. Expected counts: **161 GREP rules, 46 RAG docs (across 27 jurisdiction groups), 5 tools, 46-dim rubric v3.10, 21 configured evaluator questions, 587 example prompts across 8 audience buckets**, and all enabled layers set true. The new `Safety layers ↗` button in the top bar opens dedicated viewers for each layer (`/static/harness.html` index → grep-rules / rag-corpus / rag-graph / tools / online / persona).
5. **Click any of the 5 colored buttons** in the empty-state. They map to the 5 high-impact demo prompt categories:
   - 🟢 **Headline lift** — the 5-indicator compound case (PHP+HK)
   - 🔴 **Jailbreak** — DAN persona attempt
   - 🟡 **Online demo** — recent POEA enforcement query
   - 🟣 **Compare** — multi-jurisdiction protections
   - 🔵 **Social-eng** — humanitarian framing trap
6. **Flip toggles** below the input. Try the same prompt with all 6
   off (baseline) vs all 6 on (full harness). Or use the new **Compare**
   tab in the top bar for a one-click side-by-side. Expected: baseline
   gives a vague answer; full harness cites specific statutes + hotlines.
7. **Click `▸ View pipeline`** on any response. Top of the modal shows
   a latency-budget bar (per-layer ms + Gemma generation time, with
   harness % of total). Each layer card below shows what fired. The
   **RETRIEVAL PATH TRACE** card surfaces the multi-stage retrieval
   decision (BM25 → optional rerank → graph expansion → parent expansion).
8. **Click `Grade`** on any response. 4 modes:
   - **Rule-Based** (fast, deterministic, ~2s) — 46-dimension
     multi-signal grader (rubric v3.10) with citation grounding check
   - **Expert** (legacy per-category) — for backwards compatibility
   - **LLM-Based** (LLM-as-judge, ~30-90s) — sends response back to the
     loaded Gemma with one yes/no question per dimension; pulls
     evidence quotes from the response itself
   - **Combined** (Rule + LLM, ~30-90s) — blended 50/50 with
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
%env GEMMA_MODEL_VARIANT=e4b-it     # default — single T4
%env GEMMA_MODEL_VARIANT=31b-it      # T4×2 in 4-bit (~5-10+ min first run)
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
| `26b-a4b-it` | `unsloth/gemma-4-26B-A4B-it` | T4×2 (4-bit) | MoE |
| `31b-it` | `unsloth/gemma-4-31B-it` | T4×2 (4-bit) | flagship |
| `jailbroken-31b` | `dealignai/Gemma-4-31B-JANG_4M-CRACK` | T4×2 | abliterated; the strongest "real, not faked" proof |
| `jailbroken-e4b` | `mlabonne/Gemma-4-E4B-it-abliterated` | single T4 | smaller abliterated |
| `cloud-gemini` | Gemini 1.5 Flash API | CPU-only | needs `GEMINI_API_KEY` |
| `cloud-openai` | OpenAI-compat | CPU-only | needs `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| `cloud-ollama` | Ollama | CPU-only | needs `OLLAMA_HOST`, `OLLAMA_MODEL` |

## What lives where

- `kernel.py` — minimal orchestration: install wheels → load model
  variant → wire harness → start FastAPI + cloudflared
- `wheels/` — duecare-llm-chat / -core / -models (bundled into the
  Kaggle dataset `taylorsamarel/duecare-harness-chat-wheels`)
- `notebook.ipynb` — intentionally not committed for this script kernel;
  paste `kernel.py` into Kaggle as described above

All harness CONTENT (161 GREP rules, 46 RAG docs, 5 tools, 46-dim
rubric, 21 configured LLM-judge questions) lives in the chat package wheel —
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
| 1:30 | Click 🟢 "Headline lift" → toggle ALL 6 layers ON → Send | Response cites ILO C029 §1, POEA MC 14-2017, HK Cap. 57 §32, MfMW HK +852-2522-8264 |
| 2:30 | Click `▸ View pipeline` on the response | Latency bar shows per-layer ms; cards show GREP hits + RAG docs + tool results + online results |
| 3:30 | Click `Grade` → switch to **Combined** | Rule-Based score + LLM-Based score + agreement % + disagreement table |
| 4:30 | Click `Safety layers ↗` in top bar | Opens `/static/harness.html` — 6 layer cards with live counts; click any to drill into the dedicated viewer |
| 6:00 | Click 🔴 "Jailbreak" → toggle ALL 6 layers OFF → Send | Should refuse but vaguely (this is baseline Gemma) |
| 7:00 | Same prompt with all 6 layers ON | Refuses with citations + hotlines |
| 8:00 | Click `Grade` → **LLM-Based** mode | LLM judge sends the configured evaluator questions back to Gemma; per-dimension verdicts include evidence quotes from the response |
| 10:00 | `curl https://<url>/api/brand` | Returns chat package version + 6-layer metadata + live counts (161 GREP / 46 RAG / 46 dims) |

## Submission context

This is **core notebook #1** of 2:

- **#1** `duecare-harness-chat` (this notebook) — flip every toggle,
  switch every model
- **#2** `duecare-live-demo` — focused, scripted demonstration of the
  +56.5pp lift thesis

The other 11 notebooks are appendix (specialised playgrounds, research
graphs, agentic web research, jailbroken-models proof, lift
regenerator). See `docs/FOR_PEER_REVIEW.md` for the full submission roster.

## Troubleshooting

- **"GPU not available"** with on-device variant → switch to
  `cloud-gemini` / `cloud-openai` / `cloud-ollama` (no GPU needed)
- **31B/26B-A4B fails to load** → set `HF_TOKEN` (these are gated)
- **31B looks stuck** → open **View logs** in the picker. If the last
  phase is `from_pretrained`, it is likely still downloading, mapping
  shards, quantizing, or planning CUDA memory; first runs can take
  5-10+ minutes.
- **Clicked multiple models** → only the first click is honored. Mid-load
  switching is intentionally blocked; restart the cell to change course.
- **Picker does not advance after ready** → click **Enter chat**. The
  API model is ready; the button is a hydration fallback.
- **Online layer returns no results** → DuckDuckGo HTML can rate-
  limit; for Brave Search / Playwright agentic search use appendix A9
  (`duecare-chat-playground-with-agentic-research`)
- **Combined-mode grade is slow** → it's running up to 21 configured LLM-judge calls
  against the loaded model (one per applicable rubric dimension);
  ~30-90s for E4B, several minutes for 31B
- **Cold-boot timeout** → the unsloth-stack install can take 90s on
  a fresh Kaggle worker; subsequent restarts skip via marker file

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#01 core — Migrant-worker safety playground**.

- **[#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)**
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Original 4-toggle subset playground](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Gemma generates evaluation prompts](../A-06-prompt-generation/README.md)
- [#A07 appendix: Unsloth fine-tune + GGUF export pipeline](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Grading-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
