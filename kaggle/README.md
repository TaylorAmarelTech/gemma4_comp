# DueCare Kaggle Kernels

## Active Kernels

The current submission path uses three script-kernel folders:

| Folder | Role |
|---|---|
| `01-duecare-exploration-workbench` / `taylorsamarel/duecare-app` | Full product workbench and source of truth for shared primitives, harnesses, model picker, bulk processing, knowledge extraction, search, sharing, tracing, activity logs, and `/static/demo-recording.html`. |
| `02-live-demo` / `taylorsamarel/duecare-live-demo` | Focused live demo surface for judges, including `/start`, `/slides`, `/slides/setup`, and `/api/slides/recording-pack`. |
| `A-00-omni-experiment-workbench` / `taylorsamarel/duecare-fine-tuning-and-evaluation` | Quantitative proof path for baseline, harnessed, synthetic-data, fine-tuning, judging, checkpointing, and report artifacts. |

Run `01` and `02` by copying `kernel.py` into a Kaggle code cell, enabling Internet and T4 x2 GPU, and running the cell. Those kernels install the DueCare packages from GitHub, stage outputs under `/kaggle/working`, launch the server, and print a `https://*.trycloudflare.com` URL. Use `A-00` when you want the longer proof pipeline and report artifacts rather than the reviewer web UI.

Live Kaggle status checked 2026-07-27: `duecare-app` is `COMPLETE`, while
`duecare-live-demo` and `duecare-fine-tuning-and-evaluation` are both
`CANCEL_ACKNOWLEDGED`. Cancellation is terminal but is not successful
completion. A-00's public page attaches
`taylorsamarel/duecare-proof-finetuning-data`; a fresh successful run plus
artifact review is still required before it is cited as completed proof. No
production Gemma adapter or full advanced training corpus is published.

## Auxiliary Interim Training Collection

These public artifacts support data inspection and reproducible handoff. They
do not increase the count of active submission kernels above three:

| Public artifact | Purpose | Verified status on 2026-07-15 |
|---|---|---|
| [`duecare-visible-reasoning-sft-preview`](https://www.kaggle.com/datasets/taylorsamarel/duecare-visible-reasoning-sft-preview) | Exact-row SFT view of the approved proof release, with isolated validation and test splits. | Dataset `ready` |
| [`duecare-preference-pairs-preview`](https://www.kaggle.com/datasets/taylorsamarel/duecare-preference-pairs-preview) | Exact-row chosen/rejected preference view of the same release. | Dataset `ready` |
| [`duecare-training-data-integrity-audit`](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-integrity-audit) | CPU manifest, file-hash, row-hash, model-revision, and lineage-family audit. | Run `COMPLETE`; inline results |
| [`duecare-gemma-4-lora-training-starter`](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-lora-training-starter) | CPU-safe release preflight and pinned Gemma 4 SFT&rarr;DPO plan; GPU execution requires a fork and explicit opt-in. | Run `COMPLETE`; `training-plan.json` |
| [`duecare-four-arm-fine-tuning-evaluation`](https://www.kaggle.com/code/taylorsamarel/duecare-four-arm-fine-tuning-evaluation) | Freezes stock, stock+harness, adapter, and adapter+harness evaluation inputs and gates. | Run `COMPLETE`; plan and prompt artifacts |

The two dataset views contain no new or modified training rows and are not
independent experiments. They inherit exact-row redistribution permission from
the manifest-bound combined proof release. All public reasoning fields are
deliberately authored visible decision scaffolds; hidden model chain-of-thought
is excluded.

## Archived Reference Notebooks

The former `03-duecare-video-pitch` notebook, appendix
notebooks `A-01` through `A-24`, and task-notebook snapshots are archived under
`kaggle/_archive/notebooks/`. They are not part of the active run path.

Root `kaggle/` should not contain appendix `A-*` folders other than active
`A-00-omni-experiment-workbench`. The only root `04-*` folder should be
`04-kaggle-community-benchmark`; other `04-*` notebook snapshots belong under
`kaggle/_archive/notebooks/`.

## Optional Benchmarks

`03-universal-llm-benchmark` is an optional endpoint-comparison kernel. It
loads DueCare prompt/rubric/evidence cues when available, can call
OpenAI-compatible, Anthropic Messages, or raw JSON endpoints, and uses Claude
Opus as judge when an Anthropic key is configured. It is useful for external
model comparisons, but it does not replace the primary recording path.

`04-kaggle-community-benchmark` is the Kaggle-native benchmark-publishing
surface. It defines DueCare rows as `kaggle_benchmarks` tasks and routes model
calls through `kbench.llm` / `kbench.llms[...]`, which is the path that can use
Kaggle-hosted model quota and produce Community Benchmark task/run artifacts.

## Shared Dataset Surfaces

| Folder | Status | Purpose |
|---|---|---|
| `shared-datasets/trafficking-prompts` | Existing prompt surface | Shared prompt/rubric inputs used by legacy and optional notebook flows. |
| `shared-datasets/eval-results` | Existing evaluation surface | Metadata and documentation for reproducible evaluation artifacts. |
| [`shared-datasets/training-data`](shared-datasets/training-data/) | **Template only; not publishable** | Documents the manifest, data card, license, privacy, lineage, holdout, and visible-rationale contract for a future advanced training dataset. It contains no active `dataset-metadata.json` and no rows. |

The training-data template is not an A-00 input today. A future immutable full
dataset version may be attached only after the candidate audit is clean, every
row satisfies the current training contract, the release bundle is verified,
and the public Kaggle copy is re-downloaded and checksum-checked.

## Recommended Run Order

1. `01-duecare-exploration-workbench`: verify the main harness UI and product surfaces.
2. `02-live-demo`: verify the focused judge-facing demo.
3. Use `kaggle/A-00-omni-experiment-workbench/` when a quantitative fine-tuning/evaluation proof path is needed.

## A-00 Preconfigured Pipeline

The default A-00 source path is guided, but training remains fail-closed:

1. Run Gemma 4 on the shared prompts without the DueCare harness.
2. Run Gemma 4 on the same prompts with the DueCare harness.
3. Generate candidate SFT and preference rows with harnessed Gemma 4.
4. Validate provenance, license, privacy, hashes, frozen held-out prompt and
   lineage IDs, and the exact model revision.
5. Fine-tune a small LoRA adapter with response-only SFT followed by the
   requested preference stage; a missing DPO artifact blocks an SFT&rarr;DPO run.
6. Run the fine-tuned model without the harness.
7. Run the fine-tuned model with the harness.
8. Reload the normal base model for combined Gemma 4 plus rule grading.
9. Write the completion manifest and final comparison report under
   `/kaggle/working/a00_runs`.

The pushed public notebook contains the July gate source and attached proof
dataset, but the repository source and its tests remain authoritative until a
fresh Kaggle run completes successfully and its `/kaggle/working` artifacts
are reviewed.
