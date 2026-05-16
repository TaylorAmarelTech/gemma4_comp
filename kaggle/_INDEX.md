# Kaggle Kernel Index

## Active Submission Path

Only three Kaggle script kernels are active for the current submission and recording path:

| Order | Folder | Purpose |
|---|---|---|
| 01 | `01-duecare-exploration-workbench` | Full DueCare workbench: chat, harness comparison, bulk file review, knowledge extraction, search, sharing, traces, and activity logs. |
| 02 | `02-live-demo` | Focused live demo for judges and video capture. |
| A-00 | `A-00-omni-experiment-workbench` | Experiment console for benchmarking, synthetic data, fine-tuning, grading, and reports. |

Each active kernel is intended to be copied into Kaggle, run on T4 x2 with Internet enabled, install DueCare from GitHub, write outputs under `/kaggle/working`, launch the local server, and print a public `https://*.trycloudflare.com` URL.

## Archived Notebooks

The former `03-duecare-video-pitch` notebook and appendix notebooks `A-01` through `A-24` have been moved to `kaggle/_archive/notebooks/`. They remain reference material only; they are not part of active validation, recording, or the required Kaggle run path.

## A-00 Default Proof Path

A-00 now opens with two choices:

| Card | Use |
|---|---|
| Preconfigured Harness, Training, and Evaluation | One guided pipeline: base Gemma, base+harness, synthetic SFT rows, LoRA fine-tune, fine-tuned base, fine-tuned+harness, combined Gemma+rules grading, final report. |
| Custom | Full control surface for prompt sets, adapters, imports, research graph, knowledge packs, and partial reruns. |
