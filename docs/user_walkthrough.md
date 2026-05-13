# User walkthrough -- three time budgets, three paths

> Companion to [`FOR_KAGGLE_JUDGES.md`](FOR_KAGGLE_JUDGES.md).
> That doc covers "what every claim maps to". This doc covers
> "what to actually click in what order, depending on how much
> time you have". Optimized for:
>
> - **Clean run-through** -- every step is verified to land on a
>   page that immediately tells you what you're looking at.
> - **Zero waiting on inference** -- the 3-minute path uses only
>   the four kernels that ship cached responses (03, A-18, A-19,
>   A-20). No GPU. No cold-start. No 8-second token waits.
> - **Video friendly** -- the 3-minute path is the same path used
>   to record the submission video, so the demo your audience
>   watches is the path the camera saw.

## Three time budgets

| You have... | Path | Inference required? | Best for |
|---|---|---|---|
| 3 minutes | Zero-inference path (4 kernels) | No | First-pass scan; matches the submission video |
| 15 minutes | Live-demo path (#02 + one appendix) | Yes (E4B-IT on T4) | "Did the lift number actually appear?" |
| 60 minutes | Full ladder + appendix sweep | Yes | Reproducibility verification + audit |

## The 3-minute zero-inference path

These four kernels load no Gemma model and run no inference. They
ship with their entire data payload embedded inline or in
`/kaggle/working/<RUN>_bundle.zip`. Open each in the Kaggle UI;
hit Save & Run All; the dashboard renders in seconds.

| Step | Kernel | What you see | Time |
|---|---|---|---|
| 1 | [`03-duecare-video-pitch`](../kaggle/03-duecare-video-pitch/) | In-app tabbed nav: Slides / Presentation / Setup. The same 8 slides that anchor the YouTube video. | 30 s |
| 2 | [`A-18-demo-replay`](../kaggle/A-18-demo-replay/) | Pre-recorded harness OFF vs ON for a known compound-indicator prompt. The +56.5pp lift visible without running inference. | 30 s |
| 3 | [`A-19-multilingual-demo`](../kaggle/A-19-multilingual-demo/) | Same recruitment-fee scenario answered in EN / TL / NE / BN / ID. Click language tabs. | 45 s |
| 4 | [`A-20-privacy-boundary`](../kaggle/A-20-privacy-boundary/) | Local-state vs aggregate-share state side-by-side. The "what stays on device vs what leaves" claim made concrete. | 45 s |

End of 3-minute path. By this point you have:

- Seen the harness lift claim (#2)
- Seen the multilingual reach claim (#3)
- Seen the privacy claim made concrete (#4)
- Read the 8-slide pitch (#1)

If any of those four kernels failed to render, **the rest of the
ladder is unlikely to render either** -- inspect their `kernel.py`
console output for the failure and re-run.

### Optional zero-inference additions (still no GPU, ~2 min more)

Added 2026-05-12 with the closure of the long-context + streaming
gaps in `docs/gemma4_feature_showcase.md`:

| Step | Kernel | What you see | Time |
|---|---|---|---|
| 5 | [`A-21-long-context-demo`](../kaggle/A-21-long-context-demo/) | 5-statute compliance corpus + 3 cross-statute QA pairs that each correlate 2-3 statutes in one thinking step (Gemma 4's 128K window in practice). | 45 s |
| 6 | [`A-22-streaming-demo`](../kaggle/A-22-streaming-demo/) | Server-Sent Events stream pre-recorded responses at realistic Gemma 4 E4B-IT latencies (500ms first token, 25ms subsequent). Live first-token / token-rate / total stats. | 45 s |

Both are zero-inference cached patterns -- recording-friendly,
no GPU required.

## The 15-minute live-demo path

Adds two kernels that DO require inference.

| Step | Kernel | What you see | Time |
|---|---|---|---|
| 5 | [`02-live-demo`](../kaggle/02-live-demo/) | Live chat against Gemma 4 E4B-IT with the full harness. Click "Compare" -- send the same prompt with harness OFF and harness ON. | 5-8 min (incl. cold start) |
| 6 | [`A-02-chat-playground-with-grep-rag-tools`](../kaggle/A-02-chat-playground-with-grep-rag-tools/) | The 4-toggle harness (Persona / GREP / RAG / Tools). Flip toggles individually to see which layer contributes which delta. | 5-6 min |

By the end you have empirical evidence of the lift claims in #2
and #6.

## The 60-minute full sweep

Everything above plus:

- `01-duecare-exploration-workbench` -- the unified surface with
  9-variant model picker and all 6 harness layers.
- `A-03 / A-08 / A-11` -- run any of the comparison kernels
  (they read attached bundles, no fresh inference) to see
  reproducibility.
- `A-06 -> A-07 -> A-12` -- run the full training appendix path
  if you want to inspect the Unsloth + DPO + GGUF flow.
- `A-13 multimodal-document-analyzer` -- ship a synthetic
  receipt image and watch Gemma 4 vision + native function
  calling produce a risk envelope.
- `A-14 on-device-export` -- pull the GGUF and run it locally via
  `llama-server`. Same harness, no Kaggle.

See [`docs/gemma4_feature_showcase.md`](gemma4_feature_showcase.md)
for the per-kernel "which Gemma 4 capability does this exercise"
mapping.

## For the submission video

The video is recorded against the 3-minute zero-inference path so:

1. The audience never watches a loading spinner.
2. The on-screen lift numbers are the SAME numbers a first-time
   viewer sees on first click (no race condition between "what
   got recorded" and "what the kernel actually emits today").
3. Re-recording a scene is one-click: re-open #03's Setup tab,
   edit the cached prompt/response, hit Save, re-render.

To author / re-author the cached responses:

1. Open `03-duecare-video-pitch` in the Kaggle UI.
2. Click the **Setup** tab on the homepage.
3. Edit each scene's prompt + response + harness trace inline.
4. Hit **Save** -- writes `/kaggle/working/demo_script_authored.json`.
5. The **Presentation** tab now plays the new script.

The cached-response format is the canonical demo-script JSON
documented in
[`docs/data_primitives.md`](data_primitives.md#44-demo-replay--video-pitch-script).

## Naming + nomenclature notes

This submission uses precise terminology rather than slogans:

- "Migrant worker" / "exploited worker" -- never "victim", which
  removes agency.
- "Recruitment fee" / "placement fee" -- the precise legal terms
  the cited statutes (POEA MC 14-2017 / RA 8042 / BP2MI Reg 8-2023)
  actually use.
- "Domestic worker" -- the precise ILO C189 term, not "maid" or
  "helper".
- "Harness ON / OFF" -- the harness is a discrete boolean toggle,
  not "enhanced / unenhanced".
- "Bundle" / "envelope" / "RunID" -- canonical terms defined in
  [`docs/data_primitives.md`](data_primitives.md). Used identically
  across every kernel.
- "Five lanes" -- the audience taxonomy. Lanes are numbered
  (01 platform safety, 02 NGO & regulator, 03 individual worker /
  mobile, 04 researcher, 05 developer / integration partner) so
  they're search-friendly and unambiguous.
- "User" / "audience" / "peer reviewer" -- people clicking through
  the submission. Reserve "judge" for the formal hackathon-evaluation
  role only; for casual reviewers the lighter terms read better.

A glossary lives in [`docs/FAQ.md`](FAQ.md) if a term you read in
the writeup looks unfamiliar.

## When something doesn't render

The two most-likely failure modes for the person clicking through:

1. **Kaggle didn't attach a required dataset / model.** The 3-min
   path kernels self-bootstrap from GitHub release wheels (no
   external dataset attachment required). The 15-min path
   kernels need Gemma 4 IT models attached -- the kernel.py prints
   an early-exit message if not.
2. **HF_TOKEN secret missing.** Only required for the 15-min and
   60-min paths that load gated Gemma weights. The 3-min path is
   secret-free.

If you hit either, read the kernel.py's first 30 lines for the
expected side-panel configuration.
