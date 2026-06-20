# Triage harness

Batch safety screening — the live surface for the platform-safety lane
(deployment mode 1). Screens batches of job ads and recruiter messages on
**one model**: the same Gemma already loaded in the kernel (the chat page's
model). No second model, no external endpoint, no model switch.

```
GREP rules         deterministic, microseconds — flags known patterns
   -> Gemma 4      one flag/clear JSON verdict (+ reason) per item the
                   GREP rules did not already high-severity flag
      -> deeper    OPTIONAL GREP/RAG/tools-grounded pass on flagged items,
                   on the SAME loaded Gemma
```

## Routes

| Route | What it does |
|---|---|
| `POST /api/triage/screen` | Screen up to 200 items (20k chars each); returns per-item status, per-stage timings, measured items/min. Body: `items`, optional `run_deep` (deeper grounded pass on flagged items), `use_model` (default true — set false for GREP-only), `clear_threshold` (default 0.7) |
| `GET /api/triage/status` | Whether GREP + the loaded model are wired, plus the routing policy |

## The screening model

One model — the already-loaded in-process Gemma (`app.state.gemma_call`),
the same model the chat page uses. There is no fast/deep *model* split: both
the verdict and the optional deeper grounded pass run on that one model. With
no model loaded the harness degrades to GREP-only (`passed_grep_only`).

## Honesty invariants (tested)

- The model verdict ROUTES, it never answers — `flagged`/`review` items go to
  a human (or the optional deeper pass), never a user-facing reply.
- A malformed or errored model reply can never clear an item — it degrades to
  `review`.
- A medium-severity GREP hit overrides even a confident model "clear"
  (deterministic evidence wins).
- Without a model loaded, items report `passed_grep_only`, never `cleared`.
- Raw item text is never echoed or persisted — responses and the training log
  carry sha256 + counts only.

## Statuses

`flagged` (grep high-severity, model flag, or both) · `review` (soft grep
signal, low confidence, or parse/backend failure) · `cleared` (model,
confident, no grep signal) · `passed_grep_only` (no model loaded).

Tests: `packages/duecare-llm-chat/tests/test_triage.py` (routing matrix,
honest degradation, escalation, privacy, endpoint validation, model resolution).
