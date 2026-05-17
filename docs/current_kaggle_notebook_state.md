# Current Kaggle Submission State

This file is the short operational pointer for the current Kaggle scope.
Older generated notebook mirrors still exist for provenance and tooling, but
they are not the active submission path.

## Active Judge-Facing Kernels

The active competition and recording path is exactly three script kernels,
also listed in [`kaggle/_INDEX.md`](../kaggle/_INDEX.md):

| Folder | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad workbench: chat, harness comparison, bulk review, knowledge extraction, search, sharing, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo for judges and video capture. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative pipeline for baseline, harnessed, synthetic-data, fine-tuning, judging, and report artifacts. |

Each active folder uses `kernel.py` as source of truth. Do not recreate or
publish historical `.ipynb` wrappers for these active folders unless Taylor
explicitly asks.

## Archived Or Reference-Only Material

- `kaggle/_archive/notebooks/` contains the former `03` and `A-01` through
  `A-24` notebook-era surfaces.
- `kaggle/kernels/` contains generated/research notebook mirror material used
  by older tooling and tests. It is not the current judge path.
- `_archive/kaggle-notebook-previews-2026-05-11/` contains historical notebook
  wrappers and metadata snapshots.

## Current Review Anchors

- [`docs/copilot_handoff_2026_05_16.md`](copilot_handoff_2026_05_16.md) for
  the latest runtime, harness, A-00, and test baseline handoff.
- [`docs/harness_ecosystem.md`](harness_ecosystem.md) for the authoritative
  registered-harness inventory.
- [`docs/harness_standard_contract.md`](harness_standard_contract.md) for the
  universal harness contract.
- [`docs/model_loading_trace.md`](model_loading_trace.md) for the shared
  Gemma 4 runtime path.
