# Manual TODO Checklist

Current as of 2026-05-17. This list is intentionally limited to actions that
cannot be completed by local code edits alone.

## 1. Verify Official Competition Facts

- Confirm the final Kaggle judging rubric, track names, video duration cap,
  writeup word cap, public repo/demo requirements, and multi-track prize rules.
- If any official competition wording differs from our assumptions, update
  `docs/writeup_draft.md`, `docs/video_script.md`, and any public-facing claims
  before final submission.

## 2. Run The Three Active Kaggle Kernels

Active scope is exactly:

- `kaggle/01-duecare-exploration-workbench/`
- `kaggle/02-live-demo/`
- `kaggle/A-00-omni-experiment-workbench/`

For each kernel:

- Run on the intended Kaggle GPU shape.
- Confirm the notebook prints the public Cloudflare URL.
- Confirm the page loads and Activity logs populate.
- Save the final `/kaggle/working` artifacts before shutting down.

## 3. Produce The A-00 Evidence Run

For the writeup-quality run:

- Use the preconfigured A-00 pipeline.
- Select the smaller Gemma 4 model for generation/fine-tuning.
- Use a larger Gemma or optional external frontier/Ollama judge only for final
  judging if credentials and time allow.
- Keep checkpoint/resume enabled.
- Download the evidence ZIP, activity bundle, report HTML/MD/JSON, CSV rows,
  charts, and output manifest from `/kaggle/working`.

If Kaggle runtime is close to the time limit, stop after a checkpointed phase
and resume from the saved checkpoint in the next session.

## 4. Capture Final Demo Assets

- Exploration workbench: model load, chat prompt, harness trace, and harness
  catalog pages.
- A-00: preconfigured pipeline card, numbered Activity log, training checkpoint
  panel, judging progress, report/evidence download links.
- Final report: score chart, latency chart, prompt/response table, and exported
  evidence ZIP contents.

## 5. Final Pre-Submit Checks

- Run the focused contract gate in `docs/FOR_PEER_REVIEW.md`.
- Confirm `git status` is clean after committing and pushing.
- Confirm GitHub shows the final commit.
- Confirm Kaggle notebooks use the intended commit or attached wheel version.
- Confirm the writeup references the current three-kernel path, not archived
  A-series notebook-era material.
