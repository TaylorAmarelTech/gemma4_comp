# User Walkthrough

Current as of 2026-05-17. This walkthrough uses the active three-kernel path.
Older zero-inference appendix-ladder walkthroughs are historical and archived.

## Three Time Budgets

| Time | Path | Goal |
|---|---|---|
| 3 minutes | Kernel 02 live demo | See the focused story and capture video-safe screens. |
| 15 minutes | Kernel 01 comparison | Verify the default harness behavior and traces. |
| 60+ minutes | A-00 proof run | Produce quantitative artifacts and a report bundle. |

## 3-Minute Path: Kernel 02

Open `kaggle/02-live-demo/` and run it on the intended Kaggle runtime.

Verify:

- The app starts and prints a public URL.
- The demo prompt path is clear.
- The model-loading status is understandable.
- The harnessed response shows grounded DueCare context.
- The screen is usable for the video narrative.

## 15-Minute Path: Kernel 01

Open `kaggle/01-duecare-exploration-workbench/`.

Verify:

- The default chat comparison uses the shared harness stack.
- The default offline harness includes Persona + GREP + RAG/context + tools.
- Internet/search/import behavior is off unless explicitly enabled.
- Harness traces show which rules, facts, and tools contributed.
- Model loading follows the shared Gemma 4 runtime path.

## 60+ Minute Path: A-00

Open `kaggle/A-00-omni-experiment-workbench/` and use the preconfigured
pipeline.

For a proof run:

1. Select the model and prompt count in the preconfigured card.
2. Start the pipeline; no duplicate model-selection lightbox should appear.
3. Watch the numbered activity log.
4. Confirm baseline and harnessed prompts use the same prompt set.
5. Confirm synthetic rows, training, checkpoint, judging, and report steps are
   visible when enabled.
6. Download the final evidence artifacts from `/kaggle/working`.

For a long run, keep checkpoint/resume enabled and download artifacts after each
major phase. If Kaggle approaches its runtime limit, resume from the saved
checkpoint in the next session.

## Terms Used In The UI

- **Harness ecosystem** means the set of task-specific wrappers around Gemma 4:
  prompt processing, GREP, RAG/context, tools, search safety, anonymization,
  synthetic-data polishing, fine-tuning, judging, and report export.
- **Offline harness** means Persona + GREP + RAG/context + deterministic tools,
  with online search/import disabled.
- **Combined judging** means rule-based scoring plus an LLM judge.
- **Evidence bundle** means the report, manifest, activity log, prompts,
  responses, training metadata, and score artifacts exported under
  `/kaggle/working`.

## Related Current Docs

- [`FOR_PEER_REVIEW.md`](FOR_PEER_REVIEW.md)
- [`readiness_dashboard.md`](readiness_dashboard.md)
- [`harness_ecosystem.md`](harness_ecosystem.md)
- [`model_loading_trace.md`](model_loading_trace.md)
