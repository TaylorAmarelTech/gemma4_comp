# DueCare Kaggle Kernels

## Active Kernels

The current submission path uses two script kernels:

| Folder | Role |
|---|---|
| `01-duecare-exploration-workbench` / `taylorsamarel/duecare-app` | Full product workbench and source of truth for shared primitives, harnesses, model picker, bulk processing, knowledge extraction, search, sharing, tracing, activity logs, and `/static/demo-recording.html`. |
| `02-live-demo` / `taylorsamarel/duecare-live-demo` | Focused live demo surface for judges, including `/start`, `/slides`, `/slides/setup`, and `/api/slides/recording-pack`. |

Run each by copying its `kernel.py` into a Kaggle code cell, enabling Internet and T4 x2 GPU, and running the cell. The kernel installs the DueCare packages from GitHub, stages outputs under `/kaggle/working`, launches the server, and prints a `https://*.trycloudflare.com` URL.

## Archived Reference Notebooks

The former `03-duecare-video-pitch` notebook, A-00 experiment console, appendix
notebooks `A-01` through `A-24`, and task-notebook snapshots are archived under
`kaggle/_archive/notebooks/`. They are not part of the active run path.

Root `kaggle/` should not contain appendix `A-*` folders. The only root
`04-*` folder should be `04-kaggle-community-benchmark`; other `04-*` notebook
snapshots belong under `kaggle/_archive/notebooks/`.

## Optional Benchmarks

`03-universal-llm-benchmark` is an optional endpoint-comparison kernel. It
loads DueCare prompt/rubric/evidence cues when available, can call
OpenAI-compatible, Anthropic Messages, or raw JSON endpoints, and uses Claude
Opus as judge when an Anthropic key is configured. It is useful for external
model comparisons, but it does not replace the two-kernel recording path.

`04-kaggle-community-benchmark` is the Kaggle-native benchmark-publishing
surface. It defines DueCare rows as `kaggle_benchmarks` tasks and routes model
calls through `kbench.llm` / `kbench.llms[...]`, which is the path that can use
Kaggle-hosted model quota and produce Community Benchmark task/run artifacts.

## Recommended Run Order

1. `01-duecare-exploration-workbench`: verify the main harness UI and product surfaces.
2. `02-live-demo`: verify the focused judge-facing demo.
3. Optional only: use archived A-00 proof artifacts from `kaggle/_archive/notebooks/A-00-omni-experiment-workbench/` if a prior fine-tuning/evaluation reference is needed.

## Archived A-00 Preconfigured Pipeline

The default A-00 path is designed to be one or two clicks:

1. Run Gemma 4 on the shared prompts without the DueCare harness.
2. Run Gemma 4 on the same prompts with the DueCare harness.
3. Generate synthetic SFT rows with harnessed Gemma 4.
4. Fine-tune a small LoRA adapter from the synthetic rows.
5. Run the fine-tuned model without the harness.
6. Run the fine-tuned model with the harness.
7. Reload the normal base model for combined Gemma 4 plus rule grading.
8. Write the final comparison report under `/kaggle/working/a00_runs`.
