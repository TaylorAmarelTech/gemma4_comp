# DueCare Report Card

Status date: 2026-05-19

This page is the stable report-card link for readers coming from the GitHub
README, package metadata, Kaggle notes, or judge walkthroughs.

## Current Submission Path

The active public submission path is intentionally narrow:

1. `kaggle/01-duecare-exploration-workbench/` - broad live workbench.
2. `kaggle/02-live-demo/` - focused screen-recording surface and slides.
3. `kaggle/A-00-omni-experiment-workbench/` - evaluation, training, and
   benchmarking console.

Archived A-series notebooks remain under `kaggle/_archive/notebooks/` as
reference material, but they are not the default reviewer path.

## What Is Ready

- The README, Kaggle quick path, package inventory, and public docs point at
  stable GitHub-local files.
- The live demo has cached, recording-friendly paths for moderation, bulk
  review, knowledge extraction, search, anonymization, and slides flows.
- The workbench keeps raw worker evidence local to the Kaggle kernel until a
  reviewer explicitly exports or submits sanitized artifacts.
- The six-lane product story is consistent: platform safety, NGO/regulator,
  worker/mobile, researcher, anonymized knowledge sharing, and developer/API
  integration.
- The Android companion is maintained in the sibling
  `duecare-journey-android` repository; large model files are intentionally
  downloaded through model hosting or release assets rather than committed to
  git.

## Verification Links

- Judge quick path: [FOR_KAGGLE_JUDGES.md](./FOR_KAGGLE_JUDGES.md)
- Full peer-review path: [FOR_PEER_REVIEW.md](./FOR_PEER_REVIEW.md)
- Readiness audit: [submission_readiness_audit.md](./submission_readiness_audit.md)
- Current Kaggle state: [current_kaggle_notebook_state.md](./current_kaggle_notebook_state.md)
- Harness lift report: [harness_lift_report.md](./harness_lift_report.md)
- Package inventory: [PACKAGE_INVENTORY.md](./PACKAGE_INVENTORY.md)
- Credits and attribution: [CREDITS.md](./CREDITS.md)

## Known Scope Boundaries

- Local Gemma 4 model loading can still take minutes on Kaggle GPUs,
  especially after a model switch. The demo surfaces should use cached
  examples for recording when latency would distract from the product story.
- Media OCR and multimodal extraction are separated from deterministic bulk
  parsing. Queued media work is labeled explicitly instead of being hidden as
  background work.
- The repository includes archived research material. Public validation should
  focus on the active README, docs, examples, packages, and Kaggle folders.

