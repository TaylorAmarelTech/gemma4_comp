# ADR-006: 3 core + 24 appendix Kaggle submission shape

- **Status:** Superseded for the current competition push
- **Date:** 2026-05-11
- **Deciders:** Taylor Amarel
- **Supersedes:** [ADR-004](./004-six-plus-five-notebook-shape.md)

> **Current-scope note:** this records an intermediate notebook-era shape. Use
> [`../current_kaggle_notebook_state.md`](../current_kaggle_notebook_state.md)
> for the active three-kernel path.

## Context

The earlier 6 core + 5 appendix plan made sense while the notebooks
were still a collection of independent demos. The final submission needs a
clearer judge path: one omni workbench, one focused live demo, and all
specialized notebooks grouped as appendices for depth and reproducibility.

## Decision

Use **3 core + 24 appendix notebooks = 13 total** for the Gemma 4 Good
Hackathon Kaggle surface.

The two core notebooks are:

1. `01-duecare-exploration-workbench` — omni playground with the full
   harness, model selector, grading modes, trace views, and audience paths.
2. `02-live-demo` — focused thesis demo for the recorded video and first
   judge walkthrough.

The appendix notebooks are A-01 through A-11 in canonical order. They are
not required for first-run deployment; they provide baseline contrast,
harness ablation, classifier/knowledge-builder sandboxes, synthetic data,
adapter training, research visualization, adversarial model proof, and the
runtime harness-lift regenerator.

## Consequences

- Judge docs should lead with the two core notebooks.
- Appendix copy should describe each notebook's specific job instead of
  treating the appendices as a loose demo collection.
- A-06 and A-07 carry the model-improvement story: two-track synthetic data
  generation followed by SafetyJudge adapter training and benchmarking, with
  PrivacyRedactor kept as a separate adapter/evaluation track.
- A-11 remains a runtime harness OFF/ON measurement with weights held
  constant; it does not validate fine-tuned-model lift.
