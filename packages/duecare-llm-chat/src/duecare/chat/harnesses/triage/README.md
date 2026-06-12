# Triage harness

Platform-scale waterfall screening — the live surface for the
platform-safety lane (deployment mode 1). Screens batches of job ads and
recruiter messages so deep-model time is spent only on the risky few.

```
GREP rules            deterministic, microseconds — flags known patterns
   -> fast model      one flag/clear JSON verdict per item
      -> deep model   full GREP/RAG/tools-grounded Gemma 4 analysis,
                      ONLY for escalated items
```

## Routes

| Route | What it does |
|---|---|
| `POST /api/triage/screen` | Screen up to 200 items (20k chars each) through the waterfall; returns per-item status, per-stage timings, measured fast-tier items/min |
| `GET /api/triage/status` | Which tiers are configured + the routing policy |

## Fast-tier backend resolution

1. `DUECARE_FAST_MODEL_BASE_URL` (+ `DUECARE_FAST_MODEL_ID`, optional
   `DUECARE_FAST_MODEL_API_KEY`) — any OpenAI-compatible endpoint. The
   designed-for target is **DiffusionGemma**
   (`google/diffusiongemma-26B-A4B-it`, 256-token parallel diffusion
   blocks, up to 4x faster than autoregressive Gemma 4) served via
   `vllm serve`; see `docs/diffusiongemma_fast_tier.md`.
2. The in-process loaded Gemma model (`app.state.gemma_call`).
3. None — GREP-only honest mode.

## Honesty invariants (tested)

- The fast tier ROUTES, it never answers. DiffusionGemma's quality sits
  below standard Gemma 4, which is acceptable only because no worker,
  caseworker, or moderator ever reads fast-tier text.
- A malformed or errored fast-model reply can never clear an item — it
  degrades to `review`.
- A medium-severity GREP hit overrides even a confident fast-tier
  "clear" (deterministic evidence wins).
- Without any model, items report `passed_grep_only`, never `cleared`.
- Raw item text is never echoed or persisted — responses and the
  training log carry sha256 + counts only.

## Statuses

`flagged` (grep high-severity, fast-model flag, or both) · `review`
(soft grep signal, low confidence, or parse/backend failure) · `cleared`
(fast model, confident, no grep signal) · `passed_grep_only` (no model
configured).

Tests: `packages/duecare-llm-chat/tests/test_triage.py` (19 tests:
routing matrix, honest degradation, escalation, privacy, endpoint
validation, backend resolution).
