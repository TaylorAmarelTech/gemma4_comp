# Duecare Content Knowledge Builder Playground (Core Notebook 4 of 6)

The HANDS-ON sandbox for **building** Duecare's knowledge base.
Pairs with `content-classification-playground`; both are
prerequisites for understanding what the polished `live-demo`
notebook does. The live-demo bundles classification AND
knowledge-building into one polished UI; these two playgrounds let
judges (and downstream NGO partners) work with each piece
independently first.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
and other IT variants). Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-content-knowledge-builder-playground *(TBD)* |
| **Title on Kaggle** | "Duecare Content Knowledge Builder Playground" |
| **Slug** | `taylorsamarel/duecare-content-knowledge-builder-playground` |
| **Wheels dataset** | `taylorsamarel/duecare-content-knowledge-builder-playground-wheels` *(TBD)* |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b}-it/1` (optional) |
| **GPU** | NOT REQUIRED for the builder UI; GPU only needed if user clicks "ask Gemma" in the Test tab |
| **Internet** | ON (cloudflared tunnel) |
| **Secrets** | `HF_TOKEN` (only for the optional Gemma test) |
| **Expected runtime** | ~15 sec without Gemma; ~30 sec with E4B-it loaded |

## How this differs from `chat-playground-with-grep-rag-tools`

- **chat-playground-with-grep-rag-tools** is a CHAT UI with toggle
  tiles + Persona library + per-message custom rule additions. It's
  a CONSUMER of the harness for chat conversations. You drive it
  with messages; the knowledge base is mostly fixed.
- **THIS notebook** is a BUILDER. You don't chat — you EDIT the
  knowledge base inline. Add new GREP regex patterns; add new RAG
  documents; inspect the corridor fee caps, fee-camouflage labels,
  and NGO intake hotlines; test what fires on a sample text; export
  the full knowledge JSON for downstream use.

## The five tabs

1. **GREP rules** — add / remove regex-based detection rules.
   Fields: rule name, patterns (one regex per line), severity,
   citation, indicator, all-required-vs-any. Live table shows
   bundled + user rules with delete buttons.
2. **RAG corpus** — add / remove documents. BM25 index rebuilds
   automatically. Each doc has id, title, source, snippet (the
   chunk indexed).
3. **Tools (lookups)** — read-only view of the corridor fee caps,
   fee camouflage labels, and NGO intake hotlines. Edit via Export →
   modify JSON → Import (UI-driven editing for these is a placeholder).
4. **Test** — paste a sample text, see what fires across your
   edited knowledge base: GREP hits, RAG retrievals, the merged
   pre-context Gemma would receive. Optional "ask Gemma" button
   sends the merged prompt to Gemma 4 for a real response (requires
   GPU + HF_TOKEN).
5. **Export / Import** — download the full knowledge JSON; upload a
   modified one to override; reset to bundled built-ins.

## Minimal-deps mode

The builder logic is **pure Python** (regex matching + BM25 over
small corpora). The notebook works WITHOUT a GPU and WITHOUT loading
any LLM — perfect for downstream NGO partners who want to extend
Duecare for their corridor / domain on their laptop. Set
`ENABLE_GEMMA = False` at the top of the kernel to skip Gemma loading
entirely; the Test tab will still show GREP hits + RAG retrievals.

## Files in this folder

```
content-knowledge-builder-playground/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── notebook.ipynb       ← built artifact
├── kernel-metadata.json ← Kaggle kernel config
├── README.md            ← this file
└── wheels/              ← dataset-metadata.json (3 wheels TBD: core, models, chat)
```

## Status

**Built 2026-04-29.** Self-contained FastAPI builder UI with
cloudflared quick-tunnel auto-launch. The wheels dataset
(`duecare-content-knowledge-builder-playground-wheels`) needs 3
wheels uploaded: `duecare-llm-core`, `duecare-llm-models`,
`duecare-llm-chat`.
