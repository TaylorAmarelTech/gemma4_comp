# A-14 — On-device export (LoRA merge -> GGUF + LiteRT)

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
- `RUN_ID` format: `a14_export_{variant}_{adapter}_{ts}`
  (e.g., `a14_export_e4b-it_safetyjudge-v1_2026-05-12T19-30-00Z`)

The dashboard's artifact tool-card list (rendered by
`build_minimal_shell`) provides one-click downloads for every
produced file.

## Where this slot lives

- **Canonical role:** A-14 on-device export
- **Folder path:** `kaggle/A-14-on-device-export/`
- **Kernel ID:** `a-14-on-device-export`
- **Upstream:** consumes adapters from A-07's HF Hub push
- **Downstream:** GGUF files used by reviewer-side llama.cpp demos;
  LiteRT files used by the Android demo (`apps/duecare-android-app/`)

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A14 appendix — On-device export (LoRA merge -> GGUF + LiteRT)**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Runtime vs weights safety study](../A-10-runtime-vs-weights-safety-study/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- **[#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)**
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
