# A-13 — Multimodal document analyzer (Gemma 4 vision)

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile, 02 NGO & regulator

This kernel is the load-bearing demo of Gemma 4's UNIQUE
multimodal capability per the hackathon rubric (Technical Depth
& Execution requires Gemma 4's unique features to be substrate,
not decoration).

## What it does

Upload a photo of a recruitment contract, passport notice, job
advertisement, or fee receipt; Gemma 4 vision extracts the text,
the safety harness flags risks (passport retention, illegal fees,
contract substitution), and emits a structured envelope with ILO
citations.

## Pipeline

1. Phase 0: Unsloth stack install (vision-capable Gemma 4 needs
   the same torch + transformers pin as the text variants).
2. Phase 1: DueCare from GitHub (no Kaggle wheel datasets).
3. Phase 2: Load Gemma 4 base via Unsloth FastModel
   (`unsloth/gemma-4-{variant}-bnb-4bit`; default e4b-it).
4. Phase 3: Workbench-shell upload UI: image dropzone + optional
   text question + Analyze button.
5. Phase 4: Per-upload pipeline:
   - SHA-256 of the image bytes (audit primary key)
   - Gemma 4 vision call with chat-template messages including
     image content blocks
   - GREP rule firing over the model's response text
   - Tool-call discovery (heuristic dispatcher)
   - ILO / POEA / RA / BP2MI citation extraction via regex
6. Rolling v1.0 bundle written on every upload so a mid-session
   crash still leaves usable rows.

## Inputs

- **GPU:** T4 (e4b-it default fits in 16 GB 4-bit; e2b-it is also
  vision-capable for smoke tests)
- **Internet:** ON (GitHub install + HF Hub model download)
- **Optional secret:** `HF_TOKEN` for private repo access (not
  required for `unsloth/gemma-4-*-bnb-4bit`)
- **No Kaggle Dataset attachments required**

## Outputs

To `/kaggle/working/`:

- `<run_id>_multimodal_results.json` — full per-upload results (v1.0)
- `<run_id>_metadata.json` — payload minus `results`
- `<run_id>_bundle.zip` — manifest + above

Per-row schema: `upload_id, image_sha256, image_mime, image_dims,
user_question, extracted_text, risk_flags[].{label, severity,
evidence}, citations[], tools_called[], elapsed_s, error`.

Run-ID format: `a12_multimodal_{variant}_{iso_ts}`.

## Where this slot lives

- **Canonical role:** A-12 multimodal document analyzer (extension
  to the 24-slot ladder; rubric anchor for Gemma 4 unique features)
- **Folder path:** `kaggle/A-13-multimodal-document-analyzer/`
  (new folder; no legacy slot was available)
- **Sibling kernels referenced:**
  `kaggle/A-02-chat-playground-with-grep-rag-tools/` for the
  GREP/RAG/Tools harness pattern.

See `docs/appendix_experiment_ladder.md` and
`docs/appendix_artifact_schema.md`.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A13 appendix — Multimodal document analyzer (Gemma 4 vision)**.

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
- **[#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)**
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
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
