# Kaggle Kernel Index

## Active Submission Path

Only three Kaggle script kernels are active for the current competition scope.
The first two are the primary recording path; A-00 is the quantitative proof
and training/evaluation path:

| Order | Folder | Kaggle slug | Title | Purpose |
|---|---|---|---|---|
| 01 | `01-duecare-exploration-workbench` | `taylorsamarel/duecare-app` | **DueCare App** | Full reviewer workbench: chat, harness comparison, bulk file review, knowledge extraction, search, sharing, traces, and activity logs. |
| 02 | `02-live-demo` | `taylorsamarel/duecare-live-demo` | **DueCare Live Demo** | Focused live demo for judges and video capture. Hosts the recording-grade pitch deck at `/start` and `/slides`. |
| A-00 | `A-00-omni-experiment-workbench` | `taylorsamarel/duecare-fine-tuning-and-evaluation` | **DueCare Fine-tuning and Evaluation** | Quantitative proof path for baseline, harnessed, synthetic-data, fine-tuning, judging, checkpointing, and report artifacts. |

Each active kernel is intended to be copied into Kaggle, run on T4 x2 with Internet enabled, install DueCare from GitHub, write outputs under `/kaggle/working`, launch the local server, and print a public `https://*.trycloudflare.com` URL.

Version boundary reviewed 2026-07-14: the A-00 Kaggle URL is live, but the
public page is the May 2026 script version. The July guarded source in this
repository is pending publication. No advanced training dataset or production
adapter is publicly attached.

## Optional Evaluation Surface

This repository also includes optional benchmark kernels that are useful for
post-submission comparison work but are not required for the primary recording
path:

| Folder | Kaggle slug | Title | Purpose |
|---|---|---|---|
| `03-universal-llm-benchmark` | `taylorsamarel/duecare-universal-llm-benchmark` | **DueCare Universal LLM Benchmark** | Benchmarks arbitrary OpenAI-compatible, Anthropic Messages, or raw JSON endpoints against DueCare prompt/rubric/evidence cues, with Claude Opus judging when an Anthropic key is configured. |
| `04-kaggle-community-benchmark` | `taylorsamarel/duecare-kaggle-community-benchmark` | **DueCare Kaggle Community Benchmark** | Publishes DueCare safety rows as `kaggle_benchmarks` tasks so model calls can use Kaggle's model proxy and benchmark leaderboard flow. |

## Shared Dataset Surfaces

These directories do not change the active-kernel count:

| Folder | Status | Purpose |
|---|---|---|
| `shared-datasets/trafficking-prompts` | Existing | Shared prompt/rubric surface. |
| `shared-datasets/eval-results` | Existing | Evaluation-result metadata and reproduction notes. |
| [`shared-datasets/training-data`](shared-datasets/training-data/) | Documentation template only | Future manifest-bound SFT/preference dataset contract. It intentionally has no active `dataset-metadata.json`, no rows, and no publishable release. |

## Archived Notebooks

The former `03-duecare-video-pitch` notebook, appendix notebooks `A-01`
through `A-24`, and task-notebook snapshots have been moved to
`kaggle/_archive/notebooks/`. They remain reference material only; they are
not part of active validation, recording, or the required Kaggle run path.

Root `kaggle/` should not contain appendix `A-*` folders other than active
`A-00-omni-experiment-workbench`. The only root `04-*` folder should be
`04-kaggle-community-benchmark`; other `04-*` notebook snapshots belong under
`kaggle/_archive/notebooks/`.

## A-00 Proof Path

A-00 now opens with two choices:

| Card | Use |
|---|---|
| Preconfigured Harness, Training, and Evaluation | One guided pipeline: base Gemma, base+harness, candidate SFT/preference rows, manifest and held-out gates, optional LoRA SFT&rarr;DPO, trained base, trained+harness, combined Gemma+rules grading, completion manifest, and final report. |
| Custom | Full control surface for prompt sets, adapters, imports, research graph, knowledge packs, and partial reruns. |

The current repository source adds manifest-bound SFT and preference files,
lineage-safe train/validation/holdout assignments, exact base revisions,
privacy and licensing fields, requested-DPO enforcement, and completion
manifests. Those July changes are not yet the public May Kaggle version. The
external importer can inspect loose artifacts, final answers, citations, and
deliberately authored visible rationales, but only a fully validated bundle may
train; private hidden chain-of-thought remains prohibited.
