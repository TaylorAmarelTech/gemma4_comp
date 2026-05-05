# Duecare harness chat — unified core notebook

> **The single configurable Duecare playground.** Every harness layer,
> every Gemma 4 variant, every grading mode visible from one URL.
>
> **Live URL** (after publish): https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat

## Judge 5-minute walkthrough

1. **Open the notebook** and click "Run All". Cold-boot to ready URL:
   ~30s for E2B/E4B, ~2-4 min for 31B/26B-A4B in 4-bit.
2. **Click the cloudflared URL** that prints. The chat UI loads.
3. **Verify the harness loaded** — `curl https://<your-url>/api/health-check`
   returns wired layers + grade modes + counts:
   ```json
   {
     "ok": true, "ready": true,
     "layers_wired": {"persona": true, "grep": true, "rag": true,
                      "tools": true, "online": true},
     "grade_modes": {"universal": true, "expert": true,
                     "deep": true, "combined": true},
     "harness_counts": {"grep_rules": 49, "rag_docs": 33, "tools": 5,
                         "rubric_dimensions": 17, "judge_questions": 17}
   }
   ```
4. **Click any of the 5 colored buttons** in the empty-state. They map
   to the 5 judge-impact prompt categories:
   - 🟢 **Headline lift** — the 5-indicator compound case (PHP+HK)
   - 🔴 **Jailbreak** — DAN persona attempt
   - 🟡 **Online demo** — recent POEA enforcement query
   - 🟣 **Compare** — multi-jurisdiction protections
   - 🔵 **Social-eng** — humanitarian framing trap
5. **Flip toggles** below the input. Try the same prompt with all 5
   off (baseline) vs all 5 on (full harness). Expected: baseline gives
   a vague answer; full harness cites specific statutes + hotlines.
6. **Click `▸ View pipeline`** on any response. Top of the modal shows
   a latency-budget bar (per-layer ms + Gemma generation time, with
   harness % of total). Each layer card below shows what fired.
7. **Click `Grade`** on any response. 4 modes:
   - **Universal** (fast, deterministic, ~2s) — 17-dimension
     multi-signal grader with citation grounding check
   - **Expert** (legacy per-category) — for backwards compatibility
   - **Deep** (LLM-as-judge, ~30-90s) — sends response back to the
     loaded Gemma with one yes/no question per dimension; pulls
     evidence quotes from the response itself
   - **Combined** (Universal + Deep, ~30-90s) — blended 50/50 with
     a disagreement panel showing dimensions where the two graders
     see different evidence (the high-information cases)

## Switching the model

Set `GEMMA_MODEL_VARIANT` in the kernel (env var or edit the default):

```bash
%env GEMMA_MODEL_VARIANT=e4b-it     # default — single T4
%env GEMMA_MODEL_VARIANT=31b-it      # T4×2 in 4-bit (~3 min boot)
%env GEMMA_MODEL_VARIANT=jailbroken-31b   # abliterated; harness still wins
%env GEMMA_MODEL_VARIANT=cloud-gemini    # BYOK (set GEMINI_API_KEY)
```

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

All harness CONTENT (49 GREP rules, 33 RAG docs, 5 tools, 17-dim
rubric, 17 LLM-judge questions) lives in the chat package wheel —
not in `kernel.py`. Bumping the dataset version updates everything;
the kernel.py doesn't need to change.

## Suggested test session (10 minutes)

| Time | Action | What you should see |
|---|---|---|
| 0:00 | Click the cloudflared URL | Chat UI loads with empty state showing 5 colored quick-action buttons |
| 0:30 | Click 🟢 "Headline lift" → toggle ALL 5 layers ON → Send | Response cites ILO C029 §1, POEA MC 14-2017, HK Cap. 57 §32, MfMW HK +852-2522-8264 |
| 1:30 | Click `▸ View pipeline` on the response | Latency bar shows per-layer ms; cards show GREP hits + RAG docs + tool results + online results |
| 2:30 | Click `Grade` → switch to **Combined** | Universal score + Judge score + agreement % + disagreement table |
| 5:00 | Click 🔴 "Jailbreak" → toggle ALL 5 layers OFF → Send | Should refuse but vaguely (this is baseline Gemma) |
| 6:00 | Same prompt with all 5 layers ON | Refuses with citations + hotlines |
| 7:00 | Click `Grade` → **Deep** mode | LLM-judge sends ~17 questions back to Gemma; per-dimension verdicts with evidence quotes from the response |
| 9:00 | `curl https://<url>/api/health-check` | All layers wired, all grade modes available |

## Submission context

This is **core notebook #1** of 2:

- **#1** `duecare-harness-chat` (this notebook) — flip every toggle,
  switch every model
- **#2** `duecare-live-demo` — focused, scripted demonstration of the
  +56.5pp lift thesis

The other 9 notebooks are appendix (specialised playgrounds, research
graphs, agentic web research, jailbroken-models proof, lift
regenerator). See `docs/FOR_JUDGES.md` for the full submission roster.

## Troubleshooting

- **"GPU not available"** with on-device variant → switch to
  `cloud-gemini` / `cloud-openai` / `cloud-ollama` (no GPU needed)
- **31B/26B-A4B fails to load** → set `HF_TOKEN` (these are gated)
- **Online layer returns no results** → DuckDuckGo HTML can rate-
  limit; for Brave Search / Playwright agentic search use appendix A9
  (`duecare-chat-playground-with-agentic-research`)
- **Combined-mode grade is slow** → it's running ~17 LLM-judge calls
  against the loaded model; ~30-90s for E4B, ~3-5 min for 31B
- **Cold-boot timeout** → the unsloth-stack install can take 90s on
  a fresh Kaggle worker; subsequent restarts skip via marker file
