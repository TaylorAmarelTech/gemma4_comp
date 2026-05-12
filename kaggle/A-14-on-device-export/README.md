# A-13 — On-device export (LoRA merge -> GGUF + LiteRT)

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile, 05 Developer

## What it does

Takes a Gemma 4 base + a DueCare LoRA adapter (SafetyJudge or
PrivacyRedactor) and produces real on-device artifacts a reviewer
can run on a laptop or phone. Closes the Special Tech Track gaps:

- **llama.cpp ($10K)** — produces a real GGUF a reviewer can run via
  `llama-server`.
- **LiteRT ($10K)** — produces a real `.tflite` a reviewer can run on
  a phone via Google AI Edge / MediaPipe.

## Pipeline

1. Load Gemma 4 base + LoRA adapter from HF Hub.
2. Merge LoRA into base via `peft.PeftModel.merge_and_unload()`.
3. Build llama.cpp from source and convert the merged HF model to
   GGUF (default `Q4_K_M`).
4. Optional: LiteRT conversion via `ai-edge-torch` for the mobile
   target.
5. Emit export manifest + GGUF / LiteRT files + downloads via the
   workbench shell.

## Inputs

- **GPU:** T4 ×2 recommended (LoRA merge + GGUF quantize)
- **Internet:** ON (HF Hub adapter pull + llama.cpp source clone)
- **Kaggle Datasets:** wheels dataset (~390 KB)
- **Models:** `google/gemma-4/Transformers/<variant>-it/1`
- **Adapters:** `taylorscottamarel/duecare-gemma-4-*-SafetyJudge-*`
  or `*-PrivacyRedactor-*` from HF Hub
- **Secrets:** `HF_TOKEN`

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with manifest +
  `gguf_files[]` + `litert_files[]` entries
- `<RUN>_results.json` / `<RUN>_run.jsonl` / `<RUN>_metadata.json`
- GGUF files (one per quantization level requested)
- Optional `.tflite` files when LiteRT export is enabled
- `RUN_ID` format: `a13_export_{variant}_{adapter}_{ts}`
  (e.g., `a13_export_e4b-it_safetyjudge-v1_2026-05-12T19-30-00Z`)

The dashboard's artifact tool-card list (rendered by
`build_minimal_shell`) provides one-click downloads for every
produced file.

## Where this slot lives

- **Canonical role:** A-13 on-device export
- **Folder path:** `kaggle/A-14-on-device-export/`
- **Kernel ID:** `a-13-on-device-export`
- **Upstream:** consumes adapters from A-07's HF Hub push
- **Downstream:** GGUF files used by reviewer-side llama.cpp demos;
  LiteRT files used by the Android demo (`apps/duecare-android-app/`)

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
