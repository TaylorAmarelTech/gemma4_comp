# DueCare — Stock Gemma 4 chat baseline (#A01 appendix)
<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

A **raw** Gemma 4 chat playground. NOT the safety harness — no
moderation pipeline, no audit trail, no GREP/RAG/Tools toggles.
Just a clean chat UI bound to FastModel for any Gemma 4 variant
(default 31B-it on T4 ×2). Multimodal-capable (image upload).
Cloudflared tunnel like the live demo.

This notebook exists so a judge can see how raw Gemma 4 responds to
exploitation/trafficking prompts **without** the safety harness — the
baseline for comparison against the full [core harness playground](../01-duecare-exploration-workbench/README.md)
and the [4-toggle appendix playground](../A-02-chat-playground-with-grep-rag-tools/README.md),
which add the toggleable safety layers.

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

- **Not the safety harness.** Live demo with the full pipeline lives in [`../02-live-demo/`](../02-live-demo/README.md).
- **Not the methodology.** Benchmark + fine-tune lives in [`../A-07-bench-and-tune/`](../A-07-bench-and-tune/README.md).
- **Not a teaching tool.** The toggleable harness layers are in [`../A-02-chat-playground-with-grep-rag-tools/`](../A-02-chat-playground-with-grep-rag-tools/README.md).

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#A01 appendix — Stock Gemma 4 chat baseline**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- **[#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)**
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
