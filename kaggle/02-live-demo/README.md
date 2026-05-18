# DueCare Live Demo (#02 Core)

> Focused product demo with real Gemma 4 inference. Use this notebook when
> judges want to click a running product surface.

## Role in the Submission

- **01 Exploration Workbench:** full UI/UX and every harness surface.
- **02 Live Demo:** focused live website that loads Gemma 4 and demonstrates
  the safety harness on a curated scenario.
- **A-00 Omni Workbench:** quantitative proof, bulk prompt runs, reruns,
  scoring, reports, synthetic data, and fine-tuning jobs.

The former video-pitch and appendix kernels are archived under
`../_archive/notebooks/` so the active Kaggle path stays focused on the
working runtime surfaces.

## Judge Quick Path

| Section | This notebook |
|---|---|
| Lede | Focused live product demo for the DueCare harness. |
| What it does | Starts FastAPI, loads the selected Gemma 4 variant, opens a Cloudflare URL, and runs the safety-harness pipeline with audit trail. |
| Demo path | Run all, open the printed URL, send the curated PH-HK prompt, inspect the harness trace, then use A-00 for quantitative comparison. |
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

For a screen-recording walkthrough:

1. Open the printed `/start` URL. The two-tile landing appears
   (Project slides + Project slide setup).
2. Click **Project slide setup**. Pick an audience + use case,
   click Generate, then Save for slides. (Repeat once per slide
   you want a custom cached row for.)
3. Click **Project slides**. The full-screen 10-slide deck loads.
   Press arrow keys / space to advance.
4. On the demo-chat slide (slide 5), the cached prompt + response
   from step 2 appears immediately -- no inference wait.
5. On the demo-bulk slide (slide 6), narrate over the typed-edge
   panel; if you want the live Bulk File Review surface, open
   `/wb-static/process.html` in a separate tab.
6. Use A-00 (`kaggle/A-00-omni-experiment-workbench`) for the
   quantitative report that backs the harness-lift claim on
   slide 8.

Workbench surfaces (`/`, `/enterprise`, `/individual`, `/knowledge`,
`/settings`) remain available for deeper exploration but are not the
primary recording path.

## Reuse From Kernel 01

Notebook 02 should stay focused, but it should not fork the workbench
contract. Treat notebook 01 as the runtime source of truth and reuse the
same package primitives:

- `duecare.chat.portability` for the version floor, required endpoints,
  sample artifact names, and reusable primitive list.
- `/api/portability` for the same contract at runtime.
- `/api/audit/workbench-inventory` for live page, harness, sample, and
  taxonomy counts.
- `/api/harnesses` for the canonical harness surface map.
- `/api/knowledge/type-catalog` for knowledge-object leaf language.
- `case_files_media_rich_sample.zip` and `prompt_eval_training_seed_sample.zip`
  for the unified PH-HK demo story and comparison/evaluation seed.

Before recording, the live demo should either pass the same portability
contract or clearly state that it is a focused subset of Kernel 01.

## Review Checklist

Before recording or sharing the live URL, verify:

1. The first screen has a clear model status and no stale "getting started" language.
2. The curated PH-HK fee prompt returns a bounded answer rather than payment-collection advice.
3. The trace shows the applied harness layers and the exact evidence used.
4. The grading output includes dynamic dimensions, contact grounding, and non-uplift checks.
5. The run context is documented: model variant, quantization, GPU, package version, and public URL.
6. A-00 can reproduce the same prompt set as a baseline and harnessed comparison export.

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
- `../A-00-omni-experiment-workbench/`: proof reports, synthetic data, and training.
- `../_archive/notebooks/`: former appendix and video-pitch kernels, kept as reference material only.
