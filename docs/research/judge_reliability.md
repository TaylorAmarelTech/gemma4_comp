# Inter-judge reliability of the 0-100 panel (offline, no model calls)

> From the committed grades (`reports/rich_lift/panel.jsonl`, 28,114 judge rows). Judges vs each other (not vs the deterministic grader -- that is `convergent_validity.md`). Regenerate with `python scripts/analyze_judge_reliability.py`. Judge labels only.

Panel judges: `deepseek-v4-pro`, `glm-5.2`, `gpt-oss:120b`. **Overall Krippendorff's alpha = 0.922** (interval, over 11,546 cells graded by >=2 judges). Alpha >= 0.80 is the conventional 'reliable' threshold; >= 0.67 'tentative'.

## Agreement per arm (is a harnessed reply more consistently gradeable?)

| Arm | alpha | cells (>=2 judges) | mean per-cell disagreement (stdev) |
|---|---:|---:|---:|
| `baseline` | 0.820 | 3,846 | 6.2 |
| `harness_core` | 0.908 | 3,850 | 2.5 |
| `harness_full` | 0.916 | 3,850 | 2.6 |

## Agreement per criterion (which criterion do judges agree on most?)

| Criterion | alpha | cells |
|---|---:|---:|
| A (indicator) | 0.870 | 11,546 |
| B (cites law) | 0.898 | 11,546 |
| C (refuses) | 0.738 | 11,546 |
| D (resources) | 0.902 | 11,546 |
| E (safety) | 0.909 | 11,546 |

## Per-judge leniency (deviation from the per-cell panel consensus)

`leniency` = mean(judge score - panel-cell mean); positive = this judge scores ABOVE the panel (lenient), negative = below (harsh). A paired measure, so it controls for which prompts each judge happened to grade.

| Judge | cells | leniency | mean score |
|---|---:|---:|---:|
| `deepseek-v4-pro` | 10,999 | -0.25 | 72.5 |
| `glm-5.2` | 10,192 | 0.82 | 72.9 |
| `gpt-oss:120b` | 6,923 | -0.81 | 76.8 |

## Reading

- A high overall alpha means the +37-40 harness lift is not an artifact of one idiosyncratic judge -- independent judges converge on the same 0-100 scores.
- Per-arm alpha: if the harnessed arms agree MORE than baseline, grounding makes replies more consistently gradeable (a structured, cited answer is less ambiguous to score).
- Per-criterion alpha typically peaks on the crisp criteria (does it refuse? does it cite a statute?) and is lower on the holistic ones -- pointing to where a human-calibration pass would most improve the rubric.
- Per-judge leniency near 0 for all judges means no single model is inflating or deflating the board; a large positive/negative would flag a judge to down-weight or recalibrate.

