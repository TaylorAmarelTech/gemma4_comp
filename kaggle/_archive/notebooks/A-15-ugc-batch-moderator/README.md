# A-15 — UGC batch moderator

<!-- duecare:lane-label -->
> **Serves lanes:** 01 Platform safety

## What it does

Batch-moderates inbound posts, ads, or job-listings ("user-generated
content" / UGC) at platform-safety scale. Each row goes through the
full DueCare harness (Persona + GREP + RAG + Tools) and emits a
v1.0 risk envelope: score / verdict / indicators / citations /
suggested action.

Closes the Lane 01 gap — the website's primary audience for the
"screen exploitative UGC at scale" use case.

## Pipeline

1. Accept a CSV / JSONL of inbound posts via the dashboard's file
   picker (`<input type="file">` on the homepage).
2. Run each row through Persona + GREP + RAG + Tools.
3. Produce a per-row risk envelope: `score`, `verdict`,
   `indicators[]`, `citations[]`, `suggested_action`.
4. Emit a v1.0 bundle with per-row `results[]` + canonical
   `summary` (top indicators, corridor concentration,
   false-positive examples).
5. Render the moderation queue + summary cards in the workbench
   shell with a JS-injected bundle-download link.

## Inputs

- **GPU:** T4 ×2 (Gemma 4 inference for each row)
- **Internet:** ON (cloudflared tunnel)
- **Kaggle Datasets:** wheels dataset
- **Models:** `google/gemma-4/Transformers/<variant>-it/1`
- **Upload:** CSV or JSONL of posts (uploaded via the homepage
  `<input type="file">`; this is the kernel's PRIMARY input,
  not an upstream-bundle handoff)
- **Secrets:** `HF_TOKEN`

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with `summary`
  (+ legacy `aggregate` alias) + per-row `results[]`
- `<RUN>_ugc_moderation.json` — full envelope payload
- `<RUN>_run.jsonl` — streaming per-row form
- `<RUN>_metadata.json` — envelope minus `results[]`
- `RUN_ID` format: `a15_ugc_{variant}_{ts}`
  (e.g., `a15_ugc_e4b-it_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once the run completes.

## Where this slot lives

- **Canonical role:** A-15 UGC batch moderator
- **Folder path:** `kaggle/A-15-ugc-batch-moderator/`
- **Kernel ID:** `a-15-ugc-batch-moderator`
- **Downstream:** moderation queue feeds into A-16 NGO local-KB
  for case-file ingestion, and A-17 sentinel for trend monitoring.

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A15 appendix — UGC batch moderator (Lane 01 platform safety)**.

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
- **[#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)**
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
