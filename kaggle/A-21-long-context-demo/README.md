# A-21 — Long-context demo (Gemma 4 128K, zero inference)

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator · 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Closes the long-context gap surfaced in `docs/gemma4_feature_showcase.md`: a real demo of Gemma 4's 128K context window applied to migrant-worker compliance reasoning. |
| **What it does** | Loads a multi-statute corpus (POEA MC 14-2017 + RA 8042 + ILO C189 + BP2MI Reg 8-2023 + ILO C29) and answers 3 cross-statute questions that require correlating across 2-3 docs at once. |
| **Demo path** | Open the kernel, hit Save & Run All, read the corpus stats card + the 3 cached Q&A panels. Zero inference; renders in seconds. |
| **Audience** | NGO caseworkers verifying cross-jurisdiction protections; researchers documenting the long-context advantage over RAG-only. |
| **Inputs** | Bundled compliance corpus (public-source statute extracts); no GPU; no Kaggle dataset attachments; no secrets. |
| **Gemma 4 features** | **Long context (128K)** as the headline feature; cross-statute reasoning in a single thinking step; the value of long context vs separate retrieval calls. |
| **Outputs** | v1.0 BundleEnvelope via `duecare.appendix_primitives.write_v1_bundle()` — 4 files (results.json + run.jsonl + metadata.json + bundle.zip with manifest+sha256). |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, gemma4_feature_showcase.md, and public website. |

## What it does

Exercises Gemma 4's **long-context (128K)** capability on a real
DueCare-scope task: cross-statute reasoning. Each of the 3 cached
Q&A pairs requires Gemma 4 to find information across 2-3 statutes
in a single thinking step — the operational value of long context
over retrieval-only architectures.

Closes the "Long-context demonstration at 128K boundary" gap noted
in [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md)
section "Where each capability is not showcased yet".

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Load the bundled multi-statute compliance corpus into memory.
3. Compute corpus stats (n_statutes, total chars, approx tokens).
4. Emit the canonical v1.0 bundle via
   `duecare.appendix_primitives.write_v1_bundle()` (this is the
   second reference implementation after A-19 multilingual).
5. Launch the workbench shell with stats card + corpus table + 3
   cached Q&A panels.

## Inputs

- **GPU:** NOT required (cached-mode default).
- **Internet:** ON (GitHub install only).
- **Kaggle Datasets:** none required for the cached mode.
- **Secrets:** none required.
- **Bundled corpus:** 5 public-source statute extracts shipped
  in `kernel.py` as `COMPLIANCE_CORPUS`.

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`:

- `<RUN>_results.json` — v1.0 BundleEnvelope:
  `{schema_version, kernel_id, run_id, config, metadata, summary,
   results[]}`. Each row carries a `qa_id` (row_id), the full
  prompt + response, and the citation list.
- `<RUN>_run.jsonl` — one PerRow per Q&A, each line self-describing
  with envelope metadata.
- `<RUN>_metadata.json` — envelope minus `results[]`, plus corpus
  stats + the list of statute IDs used.
- `<RUN>_bundle.zip` — all three above + `manifest.json` with
  per-file sha256 checksums.
- `RUN_ID` format: `a21_long_context_{ts}`
  (e.g., `a21_long_context_2026-05-12T19-30-00Z`).

On older `duecare-llm-chat` versions without the
`appendix_primitives` module, the kernel falls back to the legacy
2-file emit: `<RUN>_long_context_demo.json` + `<RUN>_bundle.zip`
with just the JSON.

## Where this slot lives

- **Canonical role:** A-21 long-context demo
- **Folder path:** `kaggle/A-21-long-context-demo/`
- **Kernel ID:** `a-21-long-context-demo`
- **Reference for:** future kernels migrating to
  `duecare.appendix_primitives.write_v1_bundle()`. A-19 multilingual
  was the first reference; A-21 is the second, with a longer per-row
  payload and richer `summary`/`metadata` envelopes.
- **Sister kernels:** A-19 multilingual (zero-inference cached
  pattern), A-20 privacy-boundary (zero-inference cached pattern),
  03 video-pitch (zero-inference replay).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Gemma 4 feature showcase:** [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md).
- **User walkthrough:** [`docs/user_walkthrough.md`](../../docs/user_walkthrough.md).
- **Why Gemma 4 (feature showcases):** [duecare-ai.com/why-gemma](https://duecare-ai.com/why-gemma) -- this kernel demonstrates the long-context capability listed there.
- **BundleEnvelope schema:** [duecare-ai.com/technical-docs](https://duecare-ai.com/technical-docs) -- canonical emit shape used by this kernel.
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A21 appendix — Long-context demo (Gemma 4 128K)**.

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
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- **[#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)**
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
