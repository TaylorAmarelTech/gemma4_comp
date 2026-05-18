# DueCare Live Demo (#02 Core)

> Focused product demo with real Gemma 4 inference. Use this notebook when
> judges want to click a running product surface.

## Role in the Submission

- **DueCare App (#01):** full UI/UX and every harness surface.
- **DueCare Live Demo (#02, this kernel):** focused live website + recording-grade
  pitch deck. Loads Gemma 4 and demonstrates the safety harness on a curated scenario.
- **DueCare Fine-tuning and Evaluation:** quantitative proof, bulk prompt
  runs, reruns, scoring, reports, synthetic data, and fine-tuning jobs.

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

## Run It On Kaggle (5 clicks)

Copy-paste reproduction path so a judge can run this kernel without leaving Kaggle.

1. **New Notebook** on Kaggle (`https://www.kaggle.com/code`). Choose **+ New Notebook**.
2. **Set the accelerator** in the right-hand panel: **Accelerator: GPU T4 x2**, **Internet: On**.
3. **Add the model** in the right-hand panel: **+ Add Input → Models → `google/gemma-4`**.
   The default kernel resolves to **`gemma-4-2b-it`** (E2B). If you have the
   `gemma-4-4b-it` (E4B) or larger variants attached, the kernel picks them up
   automatically.
4. **Paste `kernel.py`** from this folder into the notebook (overwrite the default cell).
   The wheels and bootstrap install run inside `kernel.py`; you do **not** need to
   attach a separate `wheels/` dataset for the current rolling-source path.
5. **Run All.** Within roughly thirty seconds the kernel prints a public
   `https://*.trycloudflare.com` URL. Click `/start` for the two-tile landing,
   `/slides` for the recording-grade 23-slide pitch deck, or `/slides/setup`
   to pre-bake a cached worker question for the `/slides#demo-chat` slide.

If you only have a single-T4 free tier, the kernel still works for the
small-Gemma path; expect slower load. Heuristic-only mode (no model attached)
still serves `/start`, `/slides`, the deterministic GREP / RAG / tools paths,
and the cached-chat slot — the model only matters for the live `/chat`
endpoint and the optional Gemma edge pass on Bulk File Review.

## What to Show

For a screen-recording walkthrough:

1. Open the printed `/start` URL. The two-tile landing appears
   (Project slides + Project slide setup), with workbench links below.
2. Click **Project slide setup**. Pick an audience + use case,
   click Generate, then Save for slides. This caches one live-looking
   worker or operator exchange for `/slides#demo-chat`.
3. Click **Project slides**. The recording-safe ecosystem deck loads:
   problem scale, solution diagram, Gemma 4 engine, content moderation,
   case analysis, worker information access, research, anonymized
   knowledge sharing, resources, FAQ, and appendix.
4. On `/slides#demo-chat`, the cached prompt + response from step 2
   appears immediately -- no inference wait during the recording.
5. For the live Bulk File Review surface, open `/wb-static/process.html`
   from the Start page. Use the streamlined sample bundle to show
   upload, processing progress, optional local Gemma 4 edge creation,
   graph inspection, and graph chat.
6. Use A-00 (`kaggle/A-00-omni-experiment-workbench`) for quantitative
   proof: baseline vs harnessed responses, rule/LLM judging, grading
   dimensions, and reproducible reports.

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
contract or clearly state that it is a focused subset of Kernel 01. The
slides should use the same audience names and privacy boundary language
as `apps/duecare-ai.com`: platform safety screening, NGO/regulator
copilot, individual worker/mobile, researcher, developer/integration
partner, local raw-case processing, and anonymized hub sharing only.

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
