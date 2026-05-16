# A-17 — Knowledge-pack builder + verifier

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher, 05 Developer / integration partner

## What it does

Builds versioned, content-hashed knowledge packs from public-source
URLs and files. Each pack carries a `manifest.json` with curator
metadata + a sha256 hash over content. A verifier step simulates
the researcher pull-and-verify path so a reviewer can see end-to-end
reproducibility.

Closes the "researcher reproducibility" gap — the website's
`knowledge-packs.html` + `client-connect.html` mechanics.

## Pipeline

1. Accept a list of public-source URLs / files for a corridor pack
   via the dashboard.
2. Build a versioned pack manifest with content + curator metadata.
3. Sign the pack with a deterministic content_hash (sha256 over
   content + manifest).
4. Verify pack pull: simulate a researcher running
   `duecare-cli pack pull <slug>@<version>` and verify the hash
   matches the signed manifest.
5. Emit `<pack_slug>-v<version>.tar.gz` + signed manifest entries
   in the v1.0 bundle.

## Inputs

- **GPU:** NOT required (CPU-only pack assembly)
- **Internet:** ON (public-source URL fetch)
- **Kaggle Datasets:** wheels dataset
- **Upload:** list of public-source URLs / small files via the
  dashboard's `<input type="file">` (PRIMARY input, not an
  upstream-bundle handoff)
- **Secrets:** none

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with `summary` + per-pack
  `results[]` (+ legacy `packs_built[]` alias). Each row carries
  `slug + version` as the primary key plus the pack `content_hash`.
- `<RUN>_results.json` / `<RUN>_run.jsonl` / `<RUN>_metadata.json`
- `<pack_slug>-v<version>.tar.gz` — one per built pack (the
  reviewer-pullable artifact)
- `RUN_ID` format: `a17_pack_session_{ts}`
  (e.g., `a17_pack_session_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once a pack-session completes.

## Where this slot lives

- **Canonical role:** A-17 knowledge-pack builder + verifier
- **Folder path:** `kaggle/A-17-knowledge-pack-builder/`
- **Kernel ID:** `a-17-knowledge-pack-builder`
- **Downstream:** built packs are consumed by every harnessed
  kernel that loads packs via `duecare.publishing.packs.load(...)`.
  The pack manifest shape matches the website's `/api/packs/{slug}`
  endpoint shape so a partner can submit + retrieve packs through
  the same envelope.

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A17 appendix — Knowledge-pack builder + verifier**.

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
- **[#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)**
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
