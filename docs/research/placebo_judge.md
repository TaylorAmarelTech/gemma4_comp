# Placebo control, on the LLM judge — is the lift the *knowledge*, or any preamble?

The negative control ran on the deterministic grader, where every arm sits near 5.7/10 and the harness-vs-placebo effect was inconclusive. But the headline lift is the **LLM judge's** — so here the same judge (`gpt-oss:120b`) scores all three arms (baseline, length-matched **placebo** with zero domain knowledge, harnessed) on the same prompts. The contrast that matters is **harnessed − placebo**: the lift from the harness's knowledge *beyond* a generic preamble, on the metric that carries the +1.73.

> Over **74 (prompt × model) triples**, the LLM judge scores **baseline 5.081 → placebo 6.243 → harnessed 9.581** (0–10). The generic placebo moved the score **+1.16** (the 'any preamble' effect), and the real grounding scored **+3.34 beyond the placebo** — a **significant** difference (paired z=9.60, p=<0.001). So on the headline metric the lift is driven by the harness's KNOWLEDGE, not the mere presence of a preamble — the 'any preamble helps' confound is closed.

## The three arms (overall)

| Arm | Mean LLM-judge score |
|---|---:|
| baseline | 5.081 |
| placebo (generic length-matched preamble) | 6.243 |
| harnessed (DueCare grounding) | 9.581 |

| Contrast | Δ (paired) | n | z | p |
|---|---:|---:|---:|---:|
| placebo − baseline  *(any-preamble effect)* | +1.162 | 74 | 4.69 | <0.001 |
| **harnessed − placebo**  *(the KNOWLEDGE effect)* | +3.338 | 74 | 9.60 | <0.001 |
| harnessed − baseline  *(total)* | +4.500 | 74 | 12.37 | <0.001 |

## Per model — harnessed − placebo (the knowledge effect on the LLM judge)

| Model | n | baseline | placebo | harnessed | harnessed − placebo | p |
|---|---:|---:|---:|---:|---:|---:|
| `gemma4:31b` | 74 | 5.081 | 6.243 | 9.581 | +3.34 | <0.001 |

## Reading this

- This is the **conclusive** form of the 'any preamble helps' control: it runs on the LLM judge (the headline metric), where the deterministic grader was too ceiling-bound to separate the arms.
- **placebo − baseline** is the effect of *any* careful-thinking preamble; **harnessed − placebo** is the harness's knowledge on top. The baseline + harnessed responses are reused from the perdim run, the placebo from the negative control, so only the judge pass is new.
- Judge is `gpt-oss:120b`, outside the candidate families; same holistic rubric as the headline panel.
- **On absolute magnitude:** these are the negative-control prompt subset (the harder, adversarial perdim prompts), so the *absolute* lift here runs larger than the n=911 headline +1.73 — that is expected and not a competing headline. What this experiment establishes is the **contrast** (harnessed − placebo), i.e. that the lift is knowledge, not preamble.

