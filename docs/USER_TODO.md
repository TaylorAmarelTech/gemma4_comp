# Manual TODO Checklist

Current as of 2026-07-26. This list is intentionally limited to actions that
cannot be completed by local code edits alone.

The complete succession/access list is in
[`PROJECT_TRANSITION_PLAN.md#owner-only-actions`](PROJECT_TRANSITION_PLAN.md#owner-only-actions),
with acceptance and recovery steps in
[`MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md).

## 1. Final Official Competition Check

- Use this Kaggle writeup title:
  **DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection**
- Use this subtitle:
  **A self-hostable multi-faceted Gemma 4 implementation for content moderation, case analysis,
  worker support, research, and anonymized knowledge sharing.**
- Public Gemma 4 Good overview alignment was reviewed on 2026-05-18:
  Safety & Trust is the primary fit, with Unsloth and LiteRT evidence.
- Before clicking submit, confirm the Kaggle form still shows the same
  track names, 3-minute video requirement, writeup word cap, and public
  repo/demo fields.
- If the live form wording differs, update `docs/writeup_draft.md`,
  `docs/video_script.md`, and the submission text before final submission.

## 2. Run The Two Primary Demo Kernels

These are optional while model credits/quota are being preserved. The current
repository wrap-up does not depend on rerunning them; run them only for a new
recording or deliberately versioned evidence release.

Active scope is exactly:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`

For each kernel:

- Run on the intended Kaggle GPU shape.
- Confirm the notebook prints the public Cloudflare URL.
- Confirm the page loads and Activity logs populate.
- Save the final `/kaggle/working` artifacts before shutting down.

## 3. Preserve The A-00 Evidence Run

The 2026-05-18 smoke matrix has already been back-filled into the writeup
and deck: 29.5% stock, 35.6% stock + chat-offline harness, 26.4%
fine-tuned, 41.2% fine-tuned + harness. For archival quality:

- Download the evidence ZIP, activity bundle, report HTML/MD/JSON, CSV rows,
  charts, and output manifest from `/kaggle/working`.
- Keep the generated static report screenshot available for the video or
  writeup evidence appendix.
- Optional only: rerun the active A-00 preconfigured pipeline from
  `kaggle/A-00-omni-experiment-workbench/` on a larger
  prompt set if there is enough time and GPU budget.

## 4. Capture Final Demo Assets

- Exploration workbench: model load, chat prompt, harness trace, and harness
  catalog pages.
- Active A-00: preconfigured pipeline card, numbered Activity log, training checkpoint
  panel, judging progress, report/evidence download links.
- Final report: score chart, latency chart, prompt/response table, and exported
  evidence ZIP contents.

## 5. Final Pre-Submit Checks

- Run `python scripts/validate_publication_readiness.py --scope handoff` and
  preserve its receipt with the ownership-transfer record.
- Run `python scripts/validate_publication_readiness.py --scope core` and keep
  its exact receipt with the release commit.
- Decide explicitly whether the release makes no new training claim or waits
  for the 75-row corridor-diversification queue and strict training gate.
- Confirm `git status` is clean after committing and pushing.
- Confirm GitHub shows the final commit.
- Confirm Kaggle notebooks use the intended commit or attached wheel version.
- Confirm the writeup references the current active Kaggle path, not archived
  A-series notebook-era material.
- Reconcile package versions, `CITATION.cff`, changelog, and tag as one release
  decision; do not inherit a version from an unrelated package by accident.
