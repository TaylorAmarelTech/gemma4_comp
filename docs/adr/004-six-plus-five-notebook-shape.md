# ADR-004: 6 core + 5 appendix submission shape (vs single-mega-notebook)

- **Status:** Accepted
- **Date:** 2026-04-20
- **Deciders:** Taylor Amarel

## Context

The Gemma 4 Good Hackathon submission could take any shape: one
notebook, ten notebooks, or the full 76-notebook research pipeline.
Judges have limited time per submission (probably 10-20 minutes
in initial triage; 30-60 if it advances).

Two failure modes:

1. **Too few notebooks.** Judges can't see the breadth of work or
   reproduce nuanced claims (cross-model comparison, fine-tune
   uplift, on-device deployment).
2. **Too many notebooks.** Judges can't tell which to open first;
   the impressive ones get buried; the demo loses focus.

## Decision

Ship **6 core notebooks + 5 appendix notebooks = 11 total**, in
canonical presentation order. Each notebook is independently
runnable. Judges who run only the 6 core notebooks see the
complete deployment story; those who go deeper find the appendix.

The 6 core (in order):

1. `chat-playground` — raw Gemma 4 baseline (no harness)
2. `chat-playground-with-grep-rag-tools` — same UI + 4-toggle harness
3. `content-classification-playground` — hands-on classification
4. `content-knowledge-builder-playground` — hands-on knowledge building
5. `gemma-content-classification-evaluation` — polished NGO dashboard
6. `live-demo` — user-facing combined product + 22-slide deck

The 5 appendix:

- A1 `prompt-generation` — Gemma generates eval prompts
- A2 `bench-and-tune` — Unsloth SFT + DPO + GGUF + HF push
- A3 `research-graphs` — 6 Plotly visualizations
- A4 `chat-playground-with-agentic-research` — chat + 5th toggle for web research
- A5 `chat-playground-jailbroken-models` — harness vs abliterated Gemma

The 76-notebook research pipeline lives at `kaggle/kernels/` and is
**explicitly NOT part of the submission** — it's the source-of-truth
inventory for the rubric numbers, not the artifact judges open.

## Alternatives considered

- **Single mega-notebook.** Rejected because Kaggle's notebook
  rendering limits + cell-by-cell reload speed both punish 5000+ line
  notebooks. Also impossible to demonstrate cross-model comparison
  without dedicated kernels.
- **Each phase as a single notebook (4 notebooks total).**
  Rejected because the chat surface needs its own dedicated kernel
  with the visual GREP/RAG/Tools toggles — that's the headline demo;
  burying it inside a phase notebook reduces its visibility.
- **All 76 notebooks as the submission.** Rejected per the "too
  many" failure mode above.

## Consequences

**Positive:**
- Clear narrative arc for judges: notebooks 1-6 in order tell
  the full story
- Each notebook is single-purpose — easy to iterate, easy to debug
- Appendix expands the technical-depth surface without diluting
  the demo
- The 76-notebook research pipeline stays internal — no judge
  confusion about scope

**Negative:**
- 11 notebooks × 11 wheels datasets = 11 Kaggle pushes per release.
  Mitigated by the daily Kaggle push rate-limit — any release
  takes 2-3 days of pushes minimum
- Cross-notebook code duplication (the harness imports are repeated
  in each kernel.py). Mitigated by `scripts/_canonical_notebook.py`
  shared helpers.
- Maintaining 11 README.md files in lockstep with 11 kernel.py
  files is real overhead

## References

- [`kaggle/README.md`](../../kaggle/README.md)
- [`kaggle/_INDEX.md`](../../kaggle/_INDEX.md)
- [`docs/FOR_JUDGES.md`](../FOR_JUDGES.md)
- [`docs/rubric_evaluation_v07.md`](../rubric_evaluation_v07.md)
