# DueCare — Hands-on classification sandbox (#A03 appendix)

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

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#A03 appendix — Hands-on classification sandbox**.

- [#01 core: Migrant-worker safety playground](../01-duecare-harness-chat/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Original 4-toggle subset playground](../A-02-chat-playground-with-grep-rag-tools/README.md)
- **[#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)**
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Gemma generates evaluation prompts](../A-06-prompt-generation/README.md)
- [#A07 appendix: Unsloth fine-tune + GGUF export pipeline](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Grading-lift regenerator](../A-11-grading-evaluation/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
