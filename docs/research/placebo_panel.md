# Placebo control under a diverse judge panel - does *every* judge close the confound?

`placebo_judge.md` closed the 'any preamble helps' confound on one judge (gpt-oss:120b): the harness's grounding scored well beyond a length-matched, knowledge-free placebo. The natural skeptic's follow-up is **judge choice** - so here the *same* 3-arm control (baseline, placebo, harnessed) is re-scored by a panel of independent frontier judges from different model families (gpt-oss, GLM, Qwen, Kimi, DeepSeek), with **self-family exclusion**. The question: does the knowledge effect (**harnessed - placebo**) survive for *every* judge?

> Across **5 independent judges**, **every** judge finds the harness adds knowledge *beyond* the generic preamble - harnessed - placebo ranges **+3.78 ... +5.52** (panel mean **+4.55**, judge spread ±0.61), and the effect is significant for **every** one of them. The confound is closed **robustly to judge choice**, not for one judge only.

## Per judge - the placebo control (harnessed - placebo is the knowledge effect)

| Judge | n | baseline | placebo | harnessed | placebo - base | **harnessed - placebo** | p |
|---|---:|---:|---:|---:|---:|---:|---:|
| `qwen3.5:397b` | 29 | 0.0 | 0.345 | 5.862 | +0.34 | **+5.52** | <0.001 |
| `glm-5.2` | 29 | 4.138 | 4.966 | 9.793 | +0.83 | **+4.83** | <0.001 |
| `gpt-oss:120b` | 29 | 4.034 | 5.0 | 9.586 | +0.97 | **+4.59** | <0.001 |
| `deepseek-v4-pro` | 29 | 5.276 | 5.966 | 10.0 | +0.69 | **+4.03** | <0.001 |
| `kimi-k2.7-code` | 29 | 3.948 | 4.983 | 8.759 | +1.03 | **+3.78** | <0.001 |

## Reading this

- The decisive column is **harnessed - placebo**: the lift that remains after subtracting any generic-preamble effect, i.e. the harness's *knowledge*. Every judge computes it on its own paired triples, so each row is a self-contained paired test.
- **Self-family exclusion** keeps the panel independent: a judge never scores a candidate from its own family. (For the `gemma4:31b` candidate every panel judge is eligible, since none is a Gemma model.)
- As in `frontier_panel_perdim.md`, judges may anchor their *absolute* scales differently; what we claim is the **paired contrast**, which cancels each judge's offset. Agreement on the *sign and rough size* of harnessed - placebo across a diverse panel is the robustness result.
- These are the harder negative-control prompts, so absolute scores run high; the result is the **contrast and its consistency across judges**, not the absolute magnitude. The larger-N single-judge magnitude is in `placebo_judge.md`; the headline lift is `harness_lift_report.md`.

