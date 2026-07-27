# A-30 — CoT GPU LoRA Training (Kaggle GPU)

<!-- duecare:lane-label -->
> **Serves lanes:** Researcher; Developer / integration partner.

A **headless batch** training kernel (no server, no UI) that actually fine-tunes on Kaggle GPU.
It LoRA-fine-tunes **gemma-4-E2B (4-bit)** on the published
[`duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning)
chain-of-thought stream, generates before/after on a held-out prompt, and saves the adapter +
`run_evidence.json`. Real end-to-end training — no placeholders.

## Why this is separate from A-00

A-00 (`duecare-fine-tuning-and-evaluation`) is an **interactive server** kernel: it starts FastAPI +
a Cloudflare tunnel and blocks waiting for a browser click, so a headless "Save & Run All" never
trains. This kernel runs top-to-bottom and exits — the shape Kaggle actually executes on a schedule.

## Run it

`kernel-metadata.json` already declares everything, so `kaggle kernels push -p .` uploads **and runs**
it on GPU. Settings baked in:

- **Accelerator:** GPU · **Internet:** ON
- **Dataset:** `taylorsamarel/duecare-cot-reasoning` (attached; the kernel also globs `/kaggle/input`
  for `cot_train.jsonl` if the mount name differs)
- **Model:** `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit` (ungated — no HF token needed)

## Knobs (top of `kernel.py`)

`MAX_STEPS=30`, `TRAIN_SUBSET=300`, `MAX_SEQ=2048` — a fast, real smoke. Raise `MAX_STEPS` /
`TRAIN_SUBSET` for a fuller run.

## Install stack (A-00's proven recipe)

`torch>=2.8 . triton . unsloth . unsloth_zoo>=2026.4.6 . transformers==5.5.0 . bitsandbytes . trl .
peft . accelerate` via `uv pip --system` (falls back to `pip`).

## Debuggability

Headless Kaggle runs can return an empty execution log, so the kernel wraps itself in a traceback
capture that writes `error.txt` to the downloadable output; `kaggle kernels output <slug>` retrieves
it. On success it writes `cot_adapter/` (the LoRA adapter) + `run_evidence.json`.

**Boundary:** a smoke-scale LoRA on illustrative reasoning data — it tests that the format is learned
on Kaggle GPU. It does not claim general legal quality, real-world outcomes, or production readiness.
