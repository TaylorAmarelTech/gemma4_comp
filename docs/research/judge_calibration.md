# Judge calibration A/B — does a 0-100 anchored rubric de-cluster the scores?

Same responses, same judge model (`gpt-oss:120b`), two rubrics: the default 0-10 ask vs the **calibrated** 0-100 anchored rubric (rescaled to 0-10). 0-10 judges pile up at round numbers (9/10) and miss the 7-vs-8 nuance; if the calibrated rubric helps, it shows **more distinct values, lower ceiling pile-up, and higher entropy** on the same answers.

> Over **60 responses**, distinct score values went **7 → 12**, the 9-10 ceiling pile-up **50.0% → 50.0%**, integer-only scores **100.0% → 0.0%**, and entropy **2.08 → 2.78 bits**. So the calibrated rubric **adds resolution** — fine-grained scores (8.3, not 8) that capture the 7-vs-8 nuance — but does **not** reduce the top-of-scale pile-up; it is better for *nuance*, while the ceiling clustering needs the next lever (**pairwise** comparative judging, which never makes an absolute call).

## Distribution shape, by rubric

| Rubric | n | distinct values | % at 9-10 (ceiling) | % integer | std | entropy (bits) | mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| default 0-10 | 60 | 7 | 50.0% | 100.0% | 2.33 | 2.08 | 7.68 |
| calibrated 0-100 → 0-10 | 60 | 12 | 50.0% | 0.0% | 0.97 | 2.78 | 8.69 |

## Reading this

- **distinct values** and **entropy** up + **ceiling pile-up** down = the judge is using the scale instead of defaulting to 9/10. **% integer** near 0 for the calibrated arm means it is actually returning fine-grained scores (8.3, not 8).
- This is about *resolution*, not the headline lift: the paired delta is reported on whichever rubric is the better instrument. If calibration de-clusters, future panels should use it; if not, few-shot examples or pairwise comparative judging are the next levers.
- Same judge model on both arms, so only the rubric differs. Reuses stored responses; deterministic aggregation. → `scripts/judge_calibration_ab.py`.

