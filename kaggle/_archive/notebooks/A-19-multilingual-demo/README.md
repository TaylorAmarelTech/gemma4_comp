# A-19 — Multilingual demo

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile

## What it does

Same recruitment-fee scenario answered in 5 languages relevant to
the migrant-worker corridors:

| Code | Language | Corridor |
|---|---|---|
| EN | English | (baseline) |
| TL | Tagalog / Filipino | PH-HK, PH-UAE |
| NE | Nepali | NP-Gulf |
| BN | Bengali | BD-Gulf |
| ID | Indonesian | ID-HK, ID-Gulf |

Demonstrates Gemma 4's multilingual reach per the hackathon rubric
(Tech Depth 30pts requires unique-feature demonstrations).

Mirrors the `why-gemma.html` "in their language" Lane 03 claim
on the website.

## Pipeline

1. Install DueCare from GitHub (lightweight, no Unsloth needed).
2. Bundled `MULTILINGUAL_DEMO` dict with the same scenario across
   5 languages.
3. Workbench shell with language tabs (click to switch).
4. Zero model load, zero inference — instant playback for video
   recording.

## Inputs

- **GPU:** NOT required
- **Internet:** ON (GitHub install only)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`
(this kernel is the reference implementation):

- `<RUN>_results.json` — v1.0 BundleEnvelope: `{schema_version,
  kernel_id, run_id, config, metadata, summary, results[]}`
- `<RUN>_run.jsonl` — one PerRow per language (EN / TL / NE /
  BN / ID), each line self-describing with envelope metadata
- `<RUN>_metadata.json` — envelope minus `results[]` (for thin
  index reads)
- `<RUN>_bundle.zip` — all three above + `manifest.json` with
  sha256 checksums per file
- `RUN_ID` format: `a19_multilingual_{ts}`
  (e.g., `a19_multilingual_2026-05-12T19-30-00Z`)

On older `duecare-llm-chat` versions without the
`appendix_primitives` module, the kernel falls back to the legacy
2-file form: `<RUN>_multilingual_demo.json` + `<RUN>_bundle.zip`
(with the JSON only, no streaming JSONL or metadata.json).

## Where this slot lives

- **Canonical role:** A-19 multilingual demo
- **Folder path:** `kaggle/A-19-multilingual-demo/`
- **Sibling kernel:** A-24 demo replay (also a video-recording
  surface; A-19 adds the language dimension).

See `docs/appendix_experiment_ladder.md`.

## Cross-links

- **Why Gemma 4 (feature showcases):** [duecare-ai.com/why-gemma](https://duecare-ai.com/why-gemma) — multilingual reach is one of the capabilities the hub names there.
- **BundleEnvelope schema:** [duecare-ai.com/technical-docs](https://duecare-ai.com/technical-docs) — A-19 is the **first reference implementation** of `duecare.appendix_primitives.write_v1_bundle()`.
- **Full kernel roster:** [duecare-ai.com/kernels](https://duecare-ai.com/kernels).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A19 appendix — Multilingual demo (5-language playback)**.

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
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- **[#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)**
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
