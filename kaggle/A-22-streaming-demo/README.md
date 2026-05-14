# A-22 — Token streaming demo (Gemma 4 SSE, zero inference)

<!-- duecare:lane-label -->
> **Serves lanes:** 03 Individual worker / mobile · 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Closes the streaming gap surfaced in `docs/gemma4_feature_showcase.md`: a real Server-Sent Events demo of token-by-token streaming at realistic Gemma 4 E4B-IT latencies. |
| **What it does** | Replays pre-recorded responses via SSE at first-token ~500ms + subsequent ~25ms latencies. Three scenarios: quick refusal, standard fee answer, long cross-statute analysis. Live token-rate stats. |
| **Demo path** | Open the kernel, hit Save & Run All, click any scenario button on the homepage to see the response stream in real time + first-token / token-rate / total stats. |
| **Audience** | Mobile-experience reviewers verifying the "first useful token under 1 second" claim; researchers documenting the streaming UX. |
| **Inputs** | Bundled cached responses (3 scenarios); no GPU; no Kaggle dataset attachments; no secrets. |
| **Gemma 4 features** | **Token streaming** as the headline; SSE event format that matches what live Gemma 4 produces; latency profile tuned to E4B-IT on T4. |
| **Outputs** | v1.0 BundleEnvelope via `duecare.appendix_primitives.write_v1_bundle()` — 4 files (results.json + run.jsonl + metadata.json + bundle.zip with manifest+sha256). |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, gemma4_feature_showcase.md, and public website. |

## What it does

Exercises Gemma 4's **token-streaming** capability via Server-Sent
Events. Pre-recorded responses are replayed at realistic per-token
latencies (first-token ~500ms, subsequent ~25ms) matching what a
real Gemma 4 E4B-IT on T4 produces. The browser shows a true
streaming UX without any model load.

Closes the "Streaming generation" gap noted in
[`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md)
section "Where each capability is not showcased yet".

The "latency on mobile" story made concrete: a worker on a
low-spec phone sees the first useful token in under 1 second
instead of waiting 5-10 seconds for the full response.

## Pipeline

1. Install DueCare from GitHub (lightweight; no Unsloth needed).
2. Load the bundled cached scenarios and pre-tokenize each
   response into whitespace-bounded chunks.
3. Emit the canonical v1.0 bundle via
   `duecare.appendix_primitives.write_v1_bundle()` (third
   reference implementation after A-19 and A-21).
4. Launch the workbench shell with scenario buttons + live
   response box + first-token / token-rate / total stats.
5. SSE endpoint `/stream?scenario_id=...` replays cached tokens
   at realistic latencies; browser EventSource consumes them
   and renders the response progressively.

## Inputs

- **GPU:** NOT required (cached SSE replay).
- **Internet:** ON (GitHub install only).
- **Kaggle Datasets:** none required.
- **Secrets:** none required.
- **Env overrides:** `DC_FIRST_TOKEN_MS` (default 500),
  `DC_SUBSEQUENT_TOKEN_MS` (default 25) for video-recording
  fine-tuning.

## Outputs

To `/kaggle/working/`, via `duecare.appendix_primitives.write_v1_bundle()`:

- `<RUN>_results.json` — v1.0 BundleEnvelope with one PerRow per
  scenario; each row carries prompt + full response + token count
  + simulated elapsed_s.
- `<RUN>_run.jsonl` — one streaming scenario per line.
- `<RUN>_metadata.json` — envelope minus `results[]`, plus the
  scenario IDs, target_model, target_hardware.
- `<RUN>_bundle.zip` — all three above + `manifest.json` with
  per-file sha256 checksums.
- `RUN_ID` format: `a22_streaming_{ts}`
  (e.g., `a22_streaming_2026-05-12T19-30-00Z`).

On older `duecare-llm-chat` versions without the
`appendix_primitives` module, the kernel falls back to the legacy
2-file emit.

## Where this slot lives

- **Canonical role:** A-22 token streaming demo
- **Folder path:** `kaggle/A-22-streaming-demo/`
- **Kernel ID:** `a-22-streaming-demo`
- **Reference for:** SSE / streaming UX. The first kernel in the
  roster that demonstrates `text/event-stream` + EventSource.
- **Sister kernels:** A-19 multilingual, A-20 privacy-boundary,
  A-21 long-context (other zero-inference cached-pattern
  kernels), 03 video-pitch (zero-inference replay).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Gemma 4 feature showcase:** [`docs/gemma4_feature_showcase.md`](../../docs/gemma4_feature_showcase.md).
- **User walkthrough:** [`docs/user_walkthrough.md`](../../docs/user_walkthrough.md).
- **Why Gemma 4 (feature showcases):** [duecare-ai.com/why-gemma](https://duecare-ai.com/why-gemma) -- this kernel demonstrates the token-streaming capability listed there.
- **BundleEnvelope schema:** [duecare-ai.com/technical-docs](https://duecare-ai.com/technical-docs) -- canonical emit shape used by this kernel.
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A22 appendix — Token streaming demo (Gemma 4 SSE)**.

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
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- **[#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)**
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
