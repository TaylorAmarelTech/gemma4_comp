# Demo recording runbook

Goal: show the complete DueCare system in under three minutes without waiting for live inference during the main take.

## The recording strategy

Use a **cached-response primary take** and a **live-system proof layer**.

- Primary take: record `/demo-recording` and the already-loaded hub pages. It contains the five scenes and response snippets needed for pacing.
- Proof layer: keep the live pages open in adjacent tabs: `/demo`, `/knowledge-packs`, `/admin`, `/evaluation`, `/privacy-boundary`.
- Optional B-roll: record one warmed live inference after the main take. Do not depend on it for the three-minute cut.

This is not fake: the cached snippets must be generated from the real runtime or existing demo artifacts before recording. The point is to avoid dead air while a model warms up.

## Five scenes

| Time | Surface | What the viewer sees | Why it matters |
|---:|---|---|---|
| 0:00-0:25 | Human story | Composite worker scenario plus privacy boundary | Impact and vision |
| 0:25-0:55 | Private checker | GREP + RAG + tool-grounded safe answer | Gemma-powered local assistance without exporting case text |
| 0:55-1:25 | Document/case analysis | Extracted facts, timeline, complaint/interrogatory prep | Multimodal/document-understanding story |
| 1:25-2:05 | Public hub | Knowledge-pack registry, submissions, admin logs | NGO-to-NGO and NGO-to-regulator knowledge sharing |
| 2:05-2:55 | Training loop | Harness traces become SFT + DPO pairs, then release gate | Technical depth and model-improvement story |

## Exact tab set

1. `/demo-recording` — no-wait shot deck and narration spine.
2. `/demo` — public demo page.
3. `/knowledge-packs` — public pack registry and filters.
4. `/admin` — token-gated troubleshooting view for the recording operator.
5. `/evaluation` — SFT + DPO training spine.
6. `/privacy-boundary` — backup tab for the concrete data-boundary explanation.

## Cached-response notebook fallback

If a notebook is needed for Kaggle proof, mirror `/demo-recording` into a small notebook with:

1. one markdown cell for the five-scene timeline,
2. one JSON constant containing cached responses,
3. one render cell that displays the responses as tables/cards,
4. no model-load cell and no live inference dependency.

The notebook should cite the API route or artifact path that produced every cached response. It should use synthetic/composite examples only and should never store raw PII.

## Priority examples

The canonical synthetic example set now lives at `/api/demo/priority-examples` and is rendered by `/demo-recording`:

1. platform moderation, text-only social post JSON,
2. platform moderation with a synthetic image description,
3. NGO case analysis and legal-packet drafting,
4. worker mobile chat with opt-in anonymized knowledge sharing,
5. research ZIP/folder graph extraction and factoid candidates,
6. full-circle stakeholder email vetting to vetted pack release.

For the final cut, keep those IDs stable and replace fixture results with warmed Gemma 4 + DueCare harness outputs. That gives the video real model outputs without forcing the screen recording to wait for inference.

## Admin dashboard during recording

Use `/admin` to check the website while recording:

- set `DUECARE_ADMIN_TOKEN` on the deployment,
- paste the token into the page locally,
- confirm `signals.jsonl`, `updates.jsonl`, counters, and latest submissions,
- use the dashboard only for troubleshooting; do not expose the token in the video.

The admin API redacts detector-class PII and suppresses free-form payloads before display.
