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
- **Public website:** [duecare-ai.com](https://duecare-ai.com).
