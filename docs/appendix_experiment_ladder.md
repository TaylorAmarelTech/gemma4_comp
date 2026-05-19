# Appendix Experiment Ladder

The original A-series notebook ladder is now archived. The active Kaggle
submission path is:

| Slot | Folder | Role |
|---|---|---|
| 01 | `kaggle/01-duecare-exploration-workbench/` | Broad workbench and reviewer entry point. |
| 02 | `kaggle/02-live-demo/` | Focused screen-recording surface and slides. |
| A-00 | `kaggle/A-00-omni-experiment-workbench/` | Evaluation, fine-tuning, and benchmark console. |

Archived slots A-01 through A-24 live under `kaggle/_archive/notebooks/`.
They document the research path that led to the active kernels, but new judge
links and README cross-references should point to 01, 02, or A-00 unless a
historical artifact is being discussed explicitly.

## Relationship Between Active Kernels

1. `01-duecare-exploration-workbench` demonstrates the full local workbench:
   chat, harness comparison, bulk file review, knowledge extraction, search,
   anonymization, sharing, and grading.
2. `02-live-demo` is optimized for video recording and judge viewing. It
   includes the slide route and cached demo material so the narrative does not
   depend on a long live model call.
3. `A-00-omni-experiment-workbench` is the quantitative proof surface. It
   compares stock, harnessed, fine-tuned, and fine-tuned-plus-harness arms and
   exports reproducible artifacts.

## Adding New Kernels

New kernels should only be added when they create a distinct reviewer value.
Register them in [kaggle/_INDEX.md](../kaggle/_INDEX.md), keep outputs in the
[BundleEnvelope v1.0](./data_primitives.md) shape, and mark archived or
roadmap material clearly.

