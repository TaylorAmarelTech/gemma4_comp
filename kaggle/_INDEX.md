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

Version boundary reviewed 2026-07-15: the A-00 Kaggle URL is live and the
public notebook attaches `taylorsamarel/duecare-proof-finetuning-data`. The
proof dataset is ready on Kaggle; the run still needs a terminal Kaggle status
plus artifact review before it is cited as a completed proof run. No
production adapter is attached. Two advanced training-data releases and nine
companion learning notebooks are public; those artifacts do not by themselves
prove a trained model or model improvement.

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
| [`shared-datasets/training-data`](shared-datasets/training-data/) | Documentation and contract map | Explains the manifest-bound supervised fine-tuning, preference, reward-label, loading, and publication contracts. Generated Kaggle payloads remain under gitignored release directories. |

## Auxiliary Public Training Proofs

These are public companions to A-00, not additional active submission kernels:

| Kaggle slug | Type | Purpose | Status reviewed 2026-07-15 |
|---|---|---|---|
| `taylorsamarel/duecare-proof-finetuning-data` | Combined dataset | Approved 24-row supervised fine-tuning preview plus 24 preference pairs, 4 validation rows, and 4 test rows. | Ready |
| `taylorsamarel/duecare-visible-reasoning-sft-preview` | Derived dataset | Exact-row supervised fine-tuning and held-out view. | Ready |
| `taylorsamarel/duecare-preference-pairs-preview` | Derived dataset | Exact-row preference and held-out view. | Ready |
| `taylorsamarel/duecare-training-data-integrity-audit` | Central-processing-unit notebook | Re-verifies file/row hashes, model revision, and split-family isolation. | Complete |
| `taylorsamarel/duecare-gemma-4-lora-training-starter` | Central-processing-unit notebook with graphics-processing-unit opt-in cell | Writes the pinned supervised-fine-tuning-to-preference-optimization plan; the default public run does not train. Low-Rank Adaptation means training small adapter weights beside a frozen base model. | Complete |
| `taylorsamarel/duecare-four-arm-fine-tuning-evaluation` | Central-processing-unit notebook | Freezes the four-arm evaluation plan and held-out prompts. | Complete |

The derived datasets are purpose-specific views of one approved source release,
not independent experimental evidence. The notebook collection does not include
adapter weights or a completed baseline-versus-adapter result.

## Public advanced training-data showcase

These packages passed exact manifest-bound publication approval, privacy,
license, checksum, split-isolation, and local notebook-execution gates before
Kaggle version 4 was made public on 2026-07-15.

| Kaggle dataset ID | Contents | Verified identity | State |
|---|---|---|---|
| [`taylorsamarel/duecare-multiperspective-finetuning-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus) | 25,600 supervised fine-tuning train, 25,600 preference train, 2,048 validation, and 2,048 test rows | Candidate `7cc7573e34aa9300`; release-manifest SHA-256 `ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d` | Public Kaggle version 4; downloaded explorer output verifies 15 Portable Network Graphics charts and 7 comma-separated-value tables |
| [`taylorsamarel/duecare-measured-response-training-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus) | 791 supervised fine-tuning rows and preference pairs (649/66/76), 1,582 reward rows, and raw-text-free inventory/quarantine | Candidate `7fc563c8d583fd7a`; release-manifest SHA-256 `56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b` | Public Kaggle version 4; downloaded explorer output verifies 11 charts and 10 tables; benchmark-contaminated for independent evaluation |

Reviewer notebook route:

1. [Load both datasets](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-loading-quickstart).
2. [Inspect the cross-dataset quality dashboard](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-quality-dashboard).
3. Review the measured-response
   [integrity](https://www.kaggle.com/code/taylorsamarel/duecare-response-corpus-integrity),
   [training plan](https://www.kaggle.com/code/taylorsamarel/duecare-response-training-plan),
   [visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-response-dataset-visual-explorer),
   and [small central-processing-unit baseline](https://www.kaggle.com/code/taylorsamarel/duecare-response-quality-baseline).
4. Review the multiperspective
   [integrity notebook](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-integrity-and-exploration),
   [Gemma plan and smoke preflight](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-large-corpus-plan-and-smoke),
   and [visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-visual-explorer).

No Gemma fine-tuning, graphics-processing-unit training, adapter production,
merged weights, or independent model-lift result is claimed by this release.

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
manifests. Those July changes are now pushed to the public A-00 notebook with
the proof dataset attached. The external importer can inspect loose artifacts,
final answers, citations, and deliberately authored visible rationales, but
only a fully validated bundle may train; private hidden chain-of-thought
remains prohibited.
