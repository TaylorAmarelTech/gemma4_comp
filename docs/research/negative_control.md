# Negative control — a length-matched placebo preamble

Does the DueCare harness lift come from the **knowledge** it injects, or merely from prepending *any* official-sounding safety reminder? To find out we add a third arm: a **placebo** preamble that is length-matched to the real grounding but carries **no domain knowledge** — no GREP citations, no RAG excerpts, no ILO indicators, no statutes, just generic 'read carefully, be thorough, be ethical' boilerplate. Same models, same deterministic grader, same prompts.

> On **362 (prompt × model) pairs** the means were **baseline 5.804 → placebo 5.693 → harnessed 5.777** (0–10). The generic placebo slightly *lowered* the score (-0.11, the 'any preamble' effect), and the real grounding scored **+0.08 beyond the placebo** — a **marginal, not-quite-significant** (p just above 0.05) difference (paired z=1.85, p=0.064) — so on this rigid, ceiling-bound grader the knowledge effect over a generic preamble is only suggestive — the grader cannot cleanly separate the arms when every arm sits near 5.7/10. The *conclusive* placebo test belongs on the holistic LLM judge (which shows the +1.73-class lift), not the deterministic floor; this deterministic negative control is honestly inconclusive. **That conclusive test is now done:** on the LLM judge the same three arms score baseline 5.08 → placebo 6.24 → harnessed 9.58, and the harness adds **+3.34 beyond the placebo** (z=9.60, p<0.001) — confound closed. See `placebo_judge.md`. (These are the ceiling-bound *deterministic* scores; the holistic LLM-judge lift is larger — see `comparative_results_llm_judge.md`.)

## Length match (so this is a fair control)

The placebo is padded per-prompt to the real grounding preamble's length (verified ~100% on a generation run), so a length-bias explanation is ruled out by construction. (Length stats are computed during generation; regenerate without `--report-only` to print the measured means.)

## The three arms, overall

| Arm | Mean score (0–10) |
|---|---:|
| baseline (raw prompt) | 5.804 |
| placebo (generic preamble) | 5.693 |
| harnessed (DueCare grounding) | 5.777 |

## The two diagnostic contrasts

| Contrast | Δ (mean paired) | n | stat | p |
|---|---:|---:|---|---:|
| placebo − baseline  *(the 'any preamble' effect)* | -0.111 | 362 | z=-2.58 | p=0.010 |
| **harnessed − placebo**  *(the KNOWLEDGE effect)* | +0.084 | 362 | z=1.85 | p=0.064 |
| harnessed − baseline  *(total lift, for reference)* | -0.027 | 362 | z=-0.95 | p=0.340 |

## Per model — harnessed − placebo (the knowledge effect)

| Model | baseline | placebo | harnessed | harnessed − placebo | p |
|---|---:|---:|---:|---:|---:|
| `qwen3-coder:480b` | 5.687 | 5.384 | 5.796 | +0.41 | 0.018 |
| `qwen3.5:397b` | 5.868 | 5.655 | 5.823 | +0.17 | 0.151 |
| `gemma4:31b` | 5.725 | 5.747 | 5.699 | -0.05 | 0.349 |
| `glm-5.2` | 5.887 | 5.865 | 5.811 | -0.05 | 0.190 |
| `deepseek-v3.2` | 5.857 | 5.818 | 5.757 | -0.06 | 0.069 |

## Reading this

- **placebo − baseline** is the effect of prepending *any* careful-thinking preamble. It is usually small — near zero, or even slightly negative on the rigid deterministic grader, where generic boilerplate can dilute the surface-pattern matches the grader rewards. Either way it is the honest baseline against which the harness's knowledge is measured.
- **harnessed − placebo** is the headline: the lift that remains *after* subtracting the generic-preamble effect. It is attributable to the DueCare knowledge (fired indicator rules + retrieved citations + the ILO-reasoning instruction), because that is the only thing the harnessed arm has that the length-matched placebo does not.
- The placebo arm is generated fresh; the baseline + harnessed arms are the SAME graded responses used in the per-dimension report, so the three arms are directly comparable.

