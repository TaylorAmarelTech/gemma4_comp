# DueCare Live Demo (#02 Core)

> Focused product demo with real Gemma 4 inference. Use notebook 03 for the
> polished screen-recording deck. Use this notebook when judges want to click a
> running product surface.

## Role in the Submission

- **01 Exploration Workbench:** full UI/UX and every harness surface.
- **02 Live Demo:** focused live website that loads Gemma 4 and demonstrates
  the safety harness on a curated scenario.
- **03 Video Pitch:** slide deck plus cached replay for the three-minute
  recording. It avoids inference delays and exports presentation evidence.
- **A-00 Omni Workbench:** quantitative proof, bulk prompt runs, reruns,
  scoring, reports, synthetic data, and fine-tuning jobs.

02 and 03 are not duplicates. Notebook 02 is for real interaction. Notebook 03
is for a predictable video recording.

## Judge Quick Path

| Section | This notebook |
|---|---|
| Lede | Focused live product demo for the DueCare harness. |
| What it does | Starts FastAPI, loads the selected Gemma 4 variant, opens a Cloudflare URL, and runs the safety-harness pipeline with audit trail. |
| Demo path | Run all, open the printed URL, send the curated PH-HK prompt, inspect the harness trace, then compare against the recorded story in notebook 03. |
| Audience | Platform safety, NGO/regulator, worker, researcher, developer. |
| Gemma 4 features | Local inference, structured tool use, grounded response generation, and harnessed safety behavior. |
| Outputs | Live web demo, responses, traces, and audit events. |

## Requirements

| Field | Value |
|---|---|
| Kaggle URL | `https://www.kaggle.com/code/taylorsamarel/duecare-live-demo` |
| GPU | T4 x2 recommended |
| Internet | On |
| Secrets | `HF_TOKEN` when downloading gated weights |
| Models | Gemma 4 E2B, E4B, 26B-A4B, or 31B IT variants |
| Expected runtime | About 30 seconds for E4B after install, longer for larger variants |

## What to Show

1. Open the Cloudflare URL.
2. Confirm the model status is visible.
3. Send a compound PH-HK worker-safety prompt.
4. Open the trace and show persona, GREP, RAG, tools, and audit events.
5. Use notebook 03 for the polished slide and cached replay version.
6. Use A-00 for the quantitative report that backs the video claim.

## Files

```text
02-live-demo/
  kernel.py
  kernel-metadata.json
  README.md
  wheels/
```

## Related Notebooks

- `../01-duecare-exploration-workbench/`: full workbench.
- `../03-duecare-video-pitch/`: screen-recording deck and cached replay.
- `../A-00-omni-experiment-workbench/`: proof reports, synthetic data, and training.
- `../A-11-grading-evaluation/`: narrow harness-lift regenerator.
