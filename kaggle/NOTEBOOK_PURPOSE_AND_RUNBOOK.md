# Notebook Purpose And Runbook

## Active Notebooks

| Notebook | Purpose | Run Target |
|---|---|---|
| `01-duecare-exploration-workbench` | Full workbench and shared primitive source of truth. | Run in Kaggle with Internet and T4 x2. Open the printed Cloudflare URL. |
| `02-live-demo` | Focused judge-facing live demo. | Run after 01 is stable. Open the printed Cloudflare URL and walk the five DueCare use-case lanes. |
| `A-00-omni-experiment-workbench` | Quantitative control plane for benchmark, synthetic data, fine-tuning, grading, and reports. | Run the preconfigured pipeline first; use Custom only for partial reruns or uploads. |

## A-00 Happy Path

Use the `Preconfigured Harness, Training, and Evaluation` card:

1. Set prompt count to 5-10 for a smoke run.
2. Keep synthetic rows at 10 for a first LoRA pass.
3. Leave Execute training enabled when Kaggle GPU/dependencies are ready.
4. Click `Run preconfigured pipeline`.
5. Watch Activity and Jobs for phase-by-phase progress.
6. Open the generated report from the job card.

The pipeline runs:

1. Base Gemma without harness.
2. Base Gemma with DueCare harness.
3. Harnessed Gemma synthetic SFT generation.
4. LoRA fine-tuning.
5. Fine-tuned Gemma without harness.
6. Fine-tuned Gemma with harness.
7. Normal base Gemma plus rules combined grading.
8. Final HTML/Markdown/JSON report.

## Archive

`03-duecare-video-pitch` and `A-01` through `A-24` are archived under `kaggle/_archive/notebooks/`. They are retained as reference material only.
