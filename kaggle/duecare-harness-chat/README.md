# Duecare harness chat — unified core notebook

> The single configurable Duecare playground. Everything in the
> submission visible from one notebook: every harness layer, every
> Gemma 4 variant, every grading mode.

## What you can flip

- **Model:** select via `GEMMA_MODEL_VARIANT` env var (or edit
  default in `kernel.py`)
  - On-device: `e2b-it`, `e4b-it`, `26b-a4b-it`, `31b-it`
  - Jailbroken (research): `jailbroken-31b`, `jailbroken-e4b`
  - Cloud BYOK: `cloud-gemini`, `cloud-openai`, `cloud-ollama`
- **Harness layers** (toggle in the chat UI tile row):
  - Persona (expert anti-trafficking persona prepended to context)
  - GREP (49 regex KB rules)
  - RAG (BM25 over 33-doc reference corpus)
  - Tools (5 lookup functions auto-dispatched)
- **Online search** (optional 5th layer): `GET /api/online-search?q=...`
  scrapes DuckDuckGo HTML; for full Playwright agentic search use
  notebook A4 (`duecare-chat-playground-with-agentic-research`)
- **Grading modes** (in the Grade modal):
  - Universal — fast deterministic 17-dimension grader
  - Expert — legacy per-category rubrics
  - Deep — LLM-as-judge sending response back to the loaded model
    with one yes/no question per dimension
  - Combined — Universal + Deep blended 50/50 with disagreement
    panel highlighting the high-information cases

## Why this is the entry point

The judge journey:

1. Watch the 3-minute video
2. Click `duecare-harness-chat` (this notebook) — flip every toggle,
   switch between Gemma 4 variants, see the harness work end-to-end
   across the whole capability surface
3. Click `live-demo` — the focused, scripted demonstration with the
   headline +56.5pp lift number

The other 9 notebooks are appendix — they add depth-of-engineering
signal but compete for the judge's first 5 minutes if surfaced
upfront.

## How to test on Kaggle

1. Attach datasets:
   - `taylorsamarel/duecare-harness-chat-wheels`
   - `google/gemma-4` (any variant; auto-detected)
2. Set `GEMMA_MODEL_VARIANT` if not the default `e4b-it`. For cloud
   routes set the matching API key (`GEMINI_API_KEY` /
   `OPENAI_API_KEY` / `OLLAMA_HOST`).
3. Optional: set `HF_TOKEN` for gated 31B / 26B-A4B variants.
4. Run the notebook. ~30s for E2B/E4B; ~2-4 min for 31B/26B-A4B in
   4-bit.
5. Open the printed cloudflared URL → chat UI loads → flip toggles
   on/off and ask the suggested example prompts.

## What lives where

- `kernel.py` — minimal orchestration: install wheels → load model
  variant → wire harness → start FastAPI + cloudflared
- `wheels/` — duecare-llm-chat / -core / -models (bundled into the
  Kaggle dataset `duecare-harness-chat-wheels`)
- `notebook.ipynb` — single-cell wrapper around `kernel.py`

All the harness CONTENT (rules, docs, tools, grader, judge prompts)
lives in the chat package, not the kernel. Update the wheel; bump the
dataset version; this notebook picks it up automatically.
