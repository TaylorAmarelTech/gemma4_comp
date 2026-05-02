# Duecare Content Classification Playground (Core Notebook 3 of 6)

The HANDS-ON sandbox where judges learn HOW Duecare classifies content
**before** they see the polished live-demo. Pairs with
`content-knowledge-builder-playground` (the knowledge-base sandbox);
both are prerequisites for understanding what the live-demo does.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
and other IT variants). Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-content-classification-playground *(TBD)* |
| **Title on Kaggle** | "Duecare Content Classification Playground" |
| **Slug** | `taylorsamarel/duecare-content-classification-playground` |
| **Wheels dataset** | `taylorsamarel/duecare-content-classification-playground-wheels` *(TBD)* |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b,26b-a4b,31b}-it/1` |
| **GPU** | T4 ×2 (default E4B-it; switchable to E2B for CPU-fast) |
| **Internet** | ON (cloudflared tunnel + HF Hub) |
| **Secrets** | `HF_TOKEN` |
| **Expected runtime** | ~30 sec for E4B; interactive after that |

## How this differs from `gemma-content-classification-evaluation`

- **Evaluation/dashboard notebook** — polished NGO/agency UI: form,
  history queue, threshold filter, production polish.
- **THIS playground** — sandbox for understanding the mechanics. Shows
  the merged prompt Gemma actually receives, the raw response, the
  parsed JSON envelope, parse errors highlighted in red, elapsed_ms.
  Switch between 4 schema modes inline. No history, no filter — just
  paste, classify, inspect, iterate.

## The four schema modes

1. **single_label** — exactly one category from a configurable set.
   Returns `{category, confidence, rationale}`.
2. **multi_label** — any subset of a configurable tag set. Returns
   `{tags, confidences, rationale}`.
3. **risk_vector** — per-dimension magnitude scores (the same shape
   the NGO dashboard uses). Returns `{vectors, overall_risk,
   recommended_action}`.
4. **custom** — paste your own JSON Schema, get strict-JSON output.
   Useful for evaluating Gemma 4's structured-output capability on
   schemas the bundled modes don't cover.

Each classification surfaces:
- the merged prompt Gemma saw (byte-for-byte — system persona + user
  message)
- the raw response Gemma produced (no parsing)
- the parsed JSON envelope, with parse errors highlighted
- elapsed_ms (Gemma generation time only) + total roundtrip

## Files in this folder

```
content-classification-playground/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── notebook.ipynb       ← built artifact
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← dataset-metadata.json (3 wheels TBD: core, models, chat)
```

## Status

**Built 2026-04-29.** Self-contained FastAPI playground with
cloudflared quick-tunnel auto-launch, same pattern as the other 4
chat / classifier kernels. The wheels dataset
(`duecare-content-classification-playground-wheels`) needs 3 wheels
uploaded: `duecare-llm-core`, `duecare-llm-models`, `duecare-llm-chat`.
