# Per-dimension granular harness lift (LLM judges, one call per dimension)

This report presents the DueCare harness lift measured at the finest LLM-judge granularity the rubric
supports: one dedicated judge call per rubric dimension, graded by independent cross-family judges. It
is distinct from `frontier_perdim_report.md` (the deterministic ~77-dimension grader) and from
`rich_harness_lift_100.md` (the batched 0-100 board metric). The question it answers: when a judge scores
each safety dimension in isolation, and more than one independent judge does so, does the harness lift
hold, and which dimensions does it move?

Subject model: `gemma4:31b`. Arms compared: `baseline` versus `harness_core` (the lightweight harness =
fired GREP indicator rules + RAG legal grounding + the ILO-reasoning preamble). Scale: 0-100, summed over
five calibrated components A-E.

## The result converges around +55 to +57 across independent configurations

The headline is not a single number from a single setup. The same lift appears across three different
grading configurations that vary the judge, the grading method, and the prompt wording:

| Configuration | Pooled total lift | n | notes |
|---|---|---:|---|
| Single judge, single framing | +56.8 | 20 | gpt-oss-120b, one call per dimension |
| Single judge, framing-averaged | +54.1 | 16 | each dimension asked with 2 distinct framings, averaged |
| Two judges, cross-family | +57.5 | 60 | gpt-oss (openai family) + qwen3.5 (qwen family) |

The pooled totals land within roughly three points of one another. That convergence is the load-bearing
result: the measured lift does not appear to be an artifact of any single judge, any single prompt
wording, or any single grading method. A number that survives changing all three of those may be treated
as more defensible than any one measurement on its own.

## Two independent cross-family judges agree on magnitude and ordering

The two-judge run (n=60 = 30 prompts graded by two judges from different model families, each
cross-family with the gemma4:31b subject so no judge scores its own family):

| Dimension | gpt-oss (openai) | qwen3.5 (qwen) | Pooled |
|---|---:|---:|---:|
| A. Identifies the indicator | +18.2 | +17.1 | +17.7 |
| B. Cites the specific law | +11.4 | +14.3 | +12.8 |
| D. Concrete resources | +9.6 | +10.3 | +10.0 |
| C. Refuses to enable | +8.2 | +10.0 | +9.1 |
| E. Privacy and safety | +7.3 | +8.5 | +7.9 |
| Total (0-100) | +54.6 | +60.3 | +57.5 |

Both judges lift every dimension positively. Both rank indicator-identification (A) as the single
largest lift, with law-citation (B) second. That ordering maps onto what the harness injects: the GREP
indicator rules and the RAG legal corpus. The dimensions the harness is designed to move are the ones
the independent judges find move most, so the mechanism and the measurement point the same way.

Agreement is strongest on the more objective dimensions (A, B, D land within a few points across judges)
and looser on the more subjective ones (C refusal-quality and E privacy, where qwen scores the lift
somewhat higher). That divergence pattern is expected and is reported rather than smoothed over: two
judges may reasonably differ more on a judgment call than on whether a statute was cited.

## Method and robustness controls

- One call per dimension. Each component gets its own dedicated judge prompt (`build_component_rubric_single`)
  so the judge spends its full reasoning budget on one criterion and no dimension is anchored to a round
  grand total. This costs 5-6x the judge calls of a batched grade and is reserved for the headline, not
  the high-throughput sweep.
- Cross-family judging. A judge never scores a response from its own model family (`model_family`), which
  removes the most direct self-preference confound.
- Sub-call resilience. A transient sub-call failure is retried once and, if it still fails, that one
  dimension is skipped rather than dropping the whole cell (`judge_components_perdim`). A grade where
  every sub-call fails omits the total entirely rather than reporting a phantom zero, so a judge that
  cannot follow the rubric does not deflate the pooled number.
- Framing robustness. Each dimension can be asked with several distinct question framings and averaged;
  doing so moves the total only marginally (+56.8 to +54.1), which indicates the score is not an artifact
  of one prompt wording.

## Reproduce

```
python scripts/perdim_headline_regrade.py --n 30 \
  --judges nvidia:openai/gpt-oss-120b,nvidia:qwen/qwen3.5-397b-a17b
```

Add a third cross-family judge with `,nvidia:meta/llama-3.1-70b-instruct`, or average across question
framings with `--phrasings-per-dim 2`. The tool re-grades already-generated responses, so it does not
regenerate model output and does not depend on the subject model's provider.

## Notes and limitations

- Absolute magnitudes are sample-dependent and judge-dependent. Runs judged by a single strong model on a
  small fresh sample may read higher than the full 3-judge panel on the large committed board (which
  reports a batched pooled lift nearer +39). The load-bearing claim here is the convergence across
  configurations and the consistent per-dimension ordering, not the exact point value.
- The samples in this report are bounded (tens of prompts). A larger multi-judge run would tighten the
  confidence around each dimension.
- Not every model can serve as a per-dimension judge: the single-component JSON rubric is strict, and
  some models wrap or ignore it. Judges verified to follow it are recorded alongside this work.
- These numbers describe measured rubric-scored quality. A rubric that rewards citing the specific law and
  naming the indicator will reward a harness that supplies exactly those, so the honest framing is that
  grounding measurably improves rubric-scored trafficking-safety, not that the model became more capable.
- Figures may shift as more data is graded; this report describes a point-in-time measurement and the
  reproduce command above regenerates it.
