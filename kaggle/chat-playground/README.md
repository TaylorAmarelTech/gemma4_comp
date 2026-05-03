# Duecare Chat Playground (Core Notebook 1 of 6)

A **raw** Gemma 4 chat playground. NOT the safety harness — no
moderation pipeline, no audit trail, no GREP/RAG/Tools toggles.
Just a clean chat UI bound to FastModel for any Gemma 4 variant
(default 31B-it on T4 ×2). Multimodal-capable (image upload).
Cloudflared tunnel like the live demo.

This notebook exists so a judge can see how raw Gemma 4 responds to
exploitation/trafficking prompts **without** the safety harness — the
baseline for comparison against [Core Notebook 2: Chat Playground with
GREP+RAG+Tools](../chat-playground-with-grep-rag-tools/), which adds
the toggleable safety layers.

Built with Google's Gemma 4 (base model:
[google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)
and other IT variants). Used in accordance with the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms).

| Field | Value |
|---|---|
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground |
| **Title on Kaggle** | "Duecare Chat Playground" |
| **Slug** | `taylorsamarel/duecare-chat-playground` |
| **Wheels dataset** | `taylorsamarel/duecare-chat-playground-wheels` (3 wheels, ~160 KB) |
| **Models attached** | `google/gemma-4/Transformers/{e2b,e4b,26b-a4b,31b}-it/1` (all four IT variants) |
| **GPU** | T4 ×2 (default 31B-it; E4B/E2B run on one) |
| **Internet** | ON (cloudflared tunnel + HF Hub fallback) |
| **Secrets** | `HF_TOKEN` Kaggle Secret |
| **Expected runtime** | ~30 s for E4B; ~3-4 min for 31B (cold start) |

## Files in this folder

```
chat-playground/
├── kernel.py            ← source-of-truth (paste into Kaggle)
├── README.md            ← this file
└── wheels/              ← 3 .whl files + dataset-metadata.json
```

## Wheels included (3)

`duecare-llm-core`, `duecare-llm-models`, `duecare-llm-chat`.

## Publishing

### A. Paste-into-Kaggle (preferred)

1. Open https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground (create with title `Duecare Chat Playground` if it doesn't exist).
2. Side panel: GPU T4 ×2 · Internet ON · `HF_TOKEN` Secret · all 4 Gemma 4 models · `taylorsamarel/duecare-chat-playground-wheels` dataset.
3. Replace the single code cell with the contents of [`kernel.py`](./kernel.py) (CTRL+A → paste).
4. **Save Version → Save & Run All**.
5. When the cloudflared URL appears, open it on your laptop.

### B. Script-driven push

```bash
python scripts/push_kaggle_demo.py --kernel chat-playground --skip-kernel
```

(`--skip-kernel` per the no-API-kernel-push rule. The script versions the wheels dataset; you paste the kernel into Kaggle in your browser.)

## What this notebook is NOT

- **Not the safety harness.** Live demo with the full pipeline lives in [`../live-demo/`](../live-demo/).
- **Not the methodology.** Benchmark + fine-tune lives in [`../bench-and-tune/`](../bench-and-tune/).
- **Not a teaching tool.** The toggleable harness layers are in [`../chat-playground-with-grep-rag-tools/`](../chat-playground-with-grep-rag-tools/).
