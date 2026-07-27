# Current Kaggle Submission State

This file is the short operational pointer for the current Kaggle scope.
Older generated notebook mirrors still exist for provenance and tooling, but
they are not the active submission path.

## Active Judge-Facing Kernels

The active competition scope is exactly three script kernels, also listed in
[`kaggle/_INDEX.md`](../kaggle/_INDEX.md). The first two are the primary
recording path; A-00 is the quantitative proof and training/evaluation path.

| Folder | Role | Live Kaggle status checked 2026-07-27 |
|---|---|---|
| `kaggle/01-duecare-exploration-workbench/` | Broad workbench: chat, harness comparison, bulk review, knowledge extraction, search, sharing, traces, and activity logs. | `COMPLETE` |
| `kaggle/02-live-demo/` | Focused live demo for judges and video capture. | `CANCEL_ACKNOWLEDGED` |
| `kaggle/A-00-omni-experiment-workbench/` | Quantitative proof path: baseline, harnessed, synthetic-data, fine-tuning, judging, checkpoints, and report artifacts. | `CANCEL_ACKNOWLEDGED` |

The status values above came from the authenticated Kaggle command line on
2026-07-27. Cancellation is terminal but is not successful completion. A-00's
public page still attaches `taylorsamarel/duecare-proof-finetuning-data`, but
its canceled run and unreviewed output boundary cannot be cited as a completed
training/evaluation proof. No production Gemma adapter, merged weights, or full
advanced training corpus is attached.

## Auxiliary Interim Training Proofs

The active judge-facing count remains three. Separately, two exact-row dataset
views and three CPU companion notebooks are public:

- [visible-reasoning SFT data](https://www.kaggle.com/datasets/taylorsamarel/duecare-visible-reasoning-sft-preview)
  and [preference pairs](https://www.kaggle.com/datasets/taylorsamarel/duecare-preference-pairs-preview)
  both report ready;
- the [integrity audit](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-integrity-audit),
  [Gemma 4 training starter](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-lora-training-starter),
  and [four-arm evaluation protocol](https://www.kaggle.com/code/taylorsamarel/duecare-four-arm-fine-tuning-evaluation)
  all reached `COMPLETE` on 2026-07-15.

The training starter's completed public run is a CPU validation and plan export,
not a GPU fine-tune. It wrote `training-plan.json`; the evaluation notebook
wrote `evaluation-plan.json` and `evaluation-prompts.jsonl`. No adapter weights
or claimed model lift are attached.

Each active folder uses `kernel.py` as source of truth. The existing A-00
Kaggle slug is notebook-typed, so publication packages the script source into
a temporary `.ipynb` wrapper without changing the repository source of truth.

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

Live review on 2026-07-27 found the Community Benchmark run `COMPLETE`. The
configured Universal LLM Benchmark slug did not resolve publicly and could not
be verified; keep it source-only until a public URL returns successfully.

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

- [`docs/MAINTAINER_HANDOFF.md`](MAINTAINER_HANDOFF.md) for current operations,
  ownership, release boundaries, and acceptance.
- [`docs/PROJECT_TRANSITION_PLAN.md`](PROJECT_TRANSITION_PLAN.md) and
  [`docs/PUBLICATION_READINESS.md`](PUBLICATION_READINESS.md) for the closeout
  sequence and exact remaining work.
- [`docs/harness_ecosystem.md`](harness_ecosystem.md) for the authoritative
  registered-harness inventory.
- [`docs/harness_standard_contract.md`](harness_standard_contract.md) for the
  universal harness contract.
- [`docs/model_loading_trace.md`](model_loading_trace.md) for the shared
  Gemma 4 runtime path.
