# Duecare harness chat — unified core notebook

> **The single configurable Duecare playground.** Every harness layer,
> every Gemma 4 variant, every grading mode visible from one URL.
>
> **Live URL** (after publish): https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat

## Judge 5-minute walkthrough

1. **Open the notebook** and click "Run All". The server starts with
   no resident model so the public URL appears before GPU loading begins.
2. **Click the cloudflared URL** that prints. The chat UI opens with
   an in-browser model picker overlay.
3. **Pick a model**. E2B/E4B usually load in under a minute; 26B-A4B
   and 31B can take 5-10+ minutes on a first HuggingFace download.
   Keep the picker open and use **View logs** to see live loader phases.
4. **Verify the harness loaded** with `curl https://<your-url>/api/brand` (v0.14.2+) or `/api/health-check`. Expected counts: **161 GREP rules, 46 RAG docs (across 27 jurisdiction groups), 5 tools, 46-dim rubric v3.10, 46 evaluator questions, 587 example prompts across 8 audience buckets**, and all wired layers set true. The new `Harness ↗` button in the top bar opens dedicated viewers for each layer (`/static/harness.html` index → grep-rules / rag-corpus / rag-graph / tools / online / persona).
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
   - **Universal** (fast, deterministic, ~2s) — 46-dimension
     multi-signal grader (rubric v3.10) with citation grounding check
   - **Expert** (legacy per-category) — for backwards compatibility
   - **Deep** (LLM-as-judge, ~30-90s) — sends response back to the
     loaded Gemma with one yes/no question per dimension; pulls
     evidence quotes from the response itself
   - **Combined** (Universal + Deep, ~30-90s) — blended 50/50 with
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
- `notebook.ipynb` — single-cell wrapper around `kernel.py`

All harness CONTENT (161 GREP rules, 46 RAG docs, 5 tools, 46-dim
rubric, 46 LLM-judge questions) lives in the chat package wheel —
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
| 3:30 | Click `Grade` → switch to **Combined** | Universal score + Judge score + agreement % + disagreement table |
| 4:30 | Click `Harness ↗` in top bar | Opens `/static/harness.html` — 6 layer cards with live counts; click any to drill into the dedicated viewer |
| 6:00 | Click 🔴 "Jailbreak" → toggle ALL 6 layers OFF → Send | Should refuse but vaguely (this is baseline Gemma) |
| 7:00 | Same prompt with all 6 layers ON | Refuses with citations + hotlines |
| 8:00 | Click `Grade` → **Deep** mode | LLM-judge sends 46 questions back to Gemma; per-dimension verdicts with evidence quotes from the response |
| 10:00 | `curl https://<url>/api/brand` | Returns chat package version + 6-layer metadata + live counts (161 GREP / 46 RAG / 46 dims) |

## Submission context

This is **core notebook #1** of 2:

- **#1** `duecare-harness-chat` (this notebook) — flip every toggle,
  switch every model
- **#2** `duecare-live-demo` — focused, scripted demonstration of the
  +56.5pp lift thesis

The other 9 notebooks are appendix (specialised playgrounds, research
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
- **Combined-mode grade is slow** → it's running up to 46 LLM-judge calls
  against the loaded model (one per applicable rubric dimension);
  ~30-90s for E4B, several minutes for 31B
- **Cold-boot timeout** → the unsloth-stack install can take 90s on
  a fresh Kaggle worker; subsequent restarts skip via marker file
