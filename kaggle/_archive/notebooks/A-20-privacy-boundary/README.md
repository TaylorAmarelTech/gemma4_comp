# A-20 — Privacy boundary visualization

<!-- duecare:lane-label -->
> **Serves lanes:** all (trust surface for every audience)

## What it does

Side-by-side visualization showing EXACTLY what stays on the
caseworker's machine vs what would leave if the operator clicks
"share aggregate". Mirrors `privacy-boundary.html` on the website.

CPU-only, zero inference. Pre-baked sample intake + redaction +
salt-hash + aggregate side-by-side, with the BOUNDARY between
local-only and outside-the-machine drawn explicitly.

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Bundled synthetic intake (`SAMPLE_INTAKE` with fake PII).
3. Regex PII detector splits raw -> redacted + salt-hash mapping.
4. Aggregate-share preview shows exactly what JSON would leave.
5. Workbench shell renders side-by-side panels with the visual
   boundary band between them.

## Inputs

- **GPU:** NOT required
- **Internet:** ON (GitHub install only; everything else offline)
- **Kaggle Datasets:** none
- **Secrets:** none

## Outputs

To `/kaggle/working/`:

- `<RUN>_privacy_boundary_demo.json` — the side-by-side state with
  fields `local_state.{raw_intake, redacted_intake, entities[]}` +
  `aggregate_state_what_would_leave.{period_days, n_cases,
  entity_label_counts, repeat_hashes, note}`
- `<RUN>_bundle.zip` — manifest + above
- `RUN_ID` format: `a20_privacy_{ts}`
  (e.g., `a20_privacy_2026-05-12T19-30-00Z`)

## Where this slot lives

- **Canonical role:** A-20 privacy-boundary visualization
- **Folder path:** `kaggle/A-20-privacy-boundary/`
- **Sibling kernels:** A-15 (NGO local-KB — uses the same regex
  PII detector + salt-hash pattern); A-10 (PII synth) and A-11
  (PrivacyRedactor trainer) for the upstream pipeline.

See `docs/appendix_experiment_ladder.md`.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A20 appendix — Privacy boundary visualization**.

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
- **[#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)**
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
