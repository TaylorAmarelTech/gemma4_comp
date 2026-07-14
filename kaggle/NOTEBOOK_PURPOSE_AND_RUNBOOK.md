# Notebook Purpose And Runbook

## Active Notebooks

| Notebook | Purpose | Run Target |
|---|---|---|
| `01-duecare-exploration-workbench` / `duecare-app` | Full workbench and shared primitive source of truth. | Run in Kaggle with Internet and T4 x2. Open the printed Cloudflare URL for `/static/demo-recording.html`, chat, bulk review, knowledge, search, and sharing. |
| `02-live-demo` / `duecare-live-demo` | Focused judge-facing live demo and slides. | Run after 01 is stable. Open the printed Cloudflare URL for `/start`, `/slides`, `/slides/setup`, and `/api/slides/recording-pack`. |
| `A-00-omni-experiment-workbench` / `duecare-fine-tuning-and-evaluation` | Quantitative harness, dataset-candidate, guarded training, four-arm evaluation, and report workbench. | The public Kaggle copy is the May 2026 version. Review the July repository source and its gates before a new Kaggle run or update. |

## A-00 Guarded Path

Use the `Preconfigured Harness, Training, and Evaluation` card for a small
smoke run first. A smoke confirms orchestration, not model quality:

1. Run the same approved prompts through exact base-model and base+harness
   arms.
2. Generate candidate SFT and preference rows from reviewed, comparable
   outputs.
3. Require a manifest-bound bundle with artifact hashes, source and prompt
   lineages, frozen held-out hashes and lineage IDs, licenses/allowed use,
   privacy clearance, clean quality gates, and an immutable model revision.
4. Run response-only SFT followed by the requested preference stage. If DPO is
   requested, missing or failed DPO makes the run incomplete.
5. Run trained and trained+harness arms on the untouched holdout.
6. Save the completion manifest and final HTML/Markdown/JSON report.

The **Already have a file?** importer can inspect JSON, JSONL, or ZIP artifacts
from another controlled system. Loose rows remain inspection-only until the
same manifest and gate contract passes. Final answers, citations, traces, and
deliberately authored visible rationales may be candidates; provider-private
or otherwise hidden chain-of-thought is prohibited.

## Public Version And Dataset Boundary

- The A-00 Kaggle URL is live, but the public page is the May 2026 script
  version. The July guarded source update is pending.
- `A-00-omni-experiment-workbench/kernel-metadata.json` has
  `dataset_sources: []`. No eligible complete advanced training dataset or
  production Gemma adapter is published.
- `shared-datasets/training-data/` is documentation-only. It contains a README
  and placeholder metadata template, no active `dataset-metadata.json`, and no
  training rows.

## Archive

`03-duecare-video-pitch`, `A-01` through `A-24`, and task-notebook snapshots
are archived under `kaggle/_archive/notebooks/`. They are retained as reference
material only.

Root `kaggle/` should not contain appendix `A-*` folders other than active
`A-00-omni-experiment-workbench`. The only root `04-*` folder should be
`04-kaggle-community-benchmark`; other `04-*` notebook snapshots belong under
`kaggle/_archive/notebooks/`.

## Optional Benchmark Kernels

`03-universal-llm-benchmark` is available for endpoint comparisons after the
main recording path is stable. It tests arbitrary model APIs against DueCare
prompts and rubric dimensions, then writes replayable JSON/JSONL/Markdown
artifacts under `/kaggle/working/universal-benchmark/`.

`04-kaggle-community-benchmark` is available when the goal is a Kaggle
Community Benchmark. It uses the official `kaggle_benchmarks` SDK, defines
DueCare rows as `@kbench.task` tasks, and routes model calls through Kaggle's
model proxy instead of external API keys.
