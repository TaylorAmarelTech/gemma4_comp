# Current Kaggle Submission State

This file is the short operational pointer for the current Kaggle scope.
Older generated notebook mirrors still exist for provenance and tooling, but
they are not the active submission path.

## Active Judge-Facing Kernels

The active competition scope is exactly three script kernels, also listed in
[`kaggle/_INDEX.md`](../kaggle/_INDEX.md). The first two are the primary
recording path; A-00 is the quantitative proof and training/evaluation path.

| Folder | Role |
|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad workbench: chat, harness comparison, bulk review, knowledge extraction, search, sharing, traces, and activity logs. |
| `kaggle/02-live-demo/` | Focused live demo for judges and video capture. |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline, harnessed, synthetic-data, fine-tuning, judging, checkpoints, and report artifacts. |

Public-version boundary reviewed 2026-07-14: the A-00 Kaggle URL returns the
public May 2026 version (script version `320178883`). The July 2026 guarded
dataset/training source in this repository is not yet deployed there. A-00's
current repository metadata has `dataset_sources: []`; no public advanced
training dataset, production Gemma adapter, or merged weights are attached.

Each active folder uses `kernel.py` as source of truth. Do not recreate or
publish historical `.ipynb` wrappers for these active folders unless Taylor
explicitly asks.

## Optional Evaluation Kernels

`kaggle/03-universal-llm-benchmark/` is a separate endpoint-comparison kernel.
It can test OpenAI-compatible, Anthropic Messages, or raw JSON APIs against
DueCare prompts and rubric cues, with Claude Opus judging when configured. It
is useful for model comparison work, but it is not part of the primary
recording path above.

`kaggle/04-kaggle-community-benchmark/` is a separate Kaggle-native benchmark
kernel. It defines DueCare rows as `kaggle_benchmarks` tasks so model calls can
use Kaggle's model proxy/quota and publish Community Benchmark task/run
artifacts. It is also optional and not part of the primary recording path.

## Archived Or Reference-Only Material

- `kaggle/_archive/notebooks/` contains the former `03`, `A-01` through
  `A-24` notebook-era surfaces, task-notebook snapshots, and provenance copies.
- Root `kaggle/` must not contain appendix `A-*` folders other than the active
  `A-00-omni-experiment-workbench`, and the only root `04-*` folder should be
  `04-kaggle-community-benchmark`.
- `kaggle/kernels/` contains generated/research notebook mirror material used
  by older tooling and tests. It is not the current judge path.
- [`kaggle/shared-datasets/training-data/`](../kaggle/shared-datasets/training-data/)
  is a documentation-only template for
  a future manifest-bound SFT/preference release. It intentionally contains no
  active `dataset-metadata.json` and no data rows.
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
