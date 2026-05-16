# A-16 — NGO local-KB / case-file ingestion

<!-- duecare:lane-label -->
> **Serves lanes:** 02 NGO & regulator

## What it does

Lets an NGO caseworker ingest case files into a local SQLite
knowledge base. PII is redacted via the A-11 PrivacyRedactor
adapter; entities (PERSON, EMPLOYER, RECRUITER, AMOUNT, CORRIDOR)
are extracted and salt-hashed so the same person across cases is
linkable without ever storing the raw identifier.

Closes the Lane 02 gap — the website's NGO caseworker use case +
the `local-kb.html` mechanics.

## Pipeline

1. Accept synthetic case files (text or a small set of files) via
   the dashboard.
2. Run each through the A-11 PrivacyRedactor adapter to redact PII.
3. Extract entities and salt-hash them for the local SQLite store.
4. Build the entity graph linking cases by salted-hash overlap.
5. Emit `local_kb.sqlite` ready for a caseworker to query.
6. Optional: render the "share aggregate" preview (anonymized
   signal stream) for the NGO data-share flow.

## Inputs

- **GPU:** T4 ×2 (PrivacyRedactor adapter inference)
- **Internet:** ON (cloudflared tunnel)
- **Kaggle Datasets:** wheels dataset
- **Models:** `google/gemma-4/Transformers/<variant>-it/1`
- **Adapters:** `taylorscottamarel/duecare-gemma-4-*-PrivacyRedactor-*`
  (HF Hub)
- **Upload:** small set of case-file text via the dashboard's
  `<input type="file">` (this is the kernel's PRIMARY input,
  not an upstream-bundle handoff)
- **Secrets:** `HF_TOKEN`

## Outputs

To `/kaggle/working/`:

- `<RUN>_bundle.zip` — v1.0 envelope with canonical `summary`
  (+ legacy `aggregate`) + canonical `results[]`
  (+ legacy `ingested[]`); rows carry `error: null` defaults
- `<RUN>_local_kb.json` — full envelope payload
- `<RUN>_run.jsonl` — streaming per-row form
- `<RUN>_metadata.json` — envelope minus `results[]`
- `local_kb.sqlite` — the caseworker-queryable store
- `RUN_ID` format: `a16_local_kb_{ts}`
  (e.g., `a16_local_kb_2026-05-12T19-30-00Z`)

The dashboard exposes `<a id="bundle-link">` populated via
`fetch('/api/state')` once ingestion completes.

## Where this slot lives

- **Canonical role:** A-16 NGO local-KB / case-file ingestion
- **Folder path:** `kaggle/A-16-ngo-local-kb/`
- **Kernel ID:** `a-16-ngo-local-kb`
- **Upstream:** consumes A-11 PrivacyRedactor adapter from HF Hub
- **Downstream:** aggregate signals feed the website's
  `/submit-information` flow (`aggregate_signal` submission kind)

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A16 appendix — NGO local-KB / case-file ingestion**.

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
- **[#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)**
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- [#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
