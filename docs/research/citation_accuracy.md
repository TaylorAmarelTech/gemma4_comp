# Citation accuracy -- a judge-independent check of the 'cites the law' lift

The benchmark's criterion B (cites the specific law) is scored by an LLM judge, which rewards citation *presence*, not *correctness*. This is the deterministic answer to the obvious reviewer challenge -- *are the harnessed replies citing real law, or gaming the rubric with citation theatre?* No model is called: every statute-section reference is checked against the known article/section ranges (the harness's `_verify_section_numbers`), and every cited ILO convention number is bounded to the real range (C001..C190).

> The harness adds real citations, not fabricated ones. Baseline replies cite on average **0** conventions and **0** statute sections; harnessed replies cite **1.11** conventions and **0.07** sections. The implausible (hallucinated) rate stays low in BOTH arms: a hallucinated citation appears in **0.0%** of baseline and **0.0%** of harnessed replies, and of the section numbers that can be checked, **100.0%** of the harnessed ones fall in the real range. So the large criterion-B lift is grounded citation, not citation theatre.

## Per-arm citation accuracy

| Arm | n | conventions cited (mean) | statute sections cited (mean) | section numbers in-range | hallucinated-citation rate |
|---|---:|---:|---:|---:|---:|
| `baseline` | 100 | 0 | 0 | - | 0.0% |
| `harness_core` | 100 | 0.89 | 0 | - | 0.0% |
| `harness_full` | 100 | 1.11 | 0.07 | 100.0% | 0.0% |

## Reading this

- **conventions / sections cited** -- the harness's grounding should raise these (it supplies the specific instrument). That is the mechanism behind the criterion-B lift.
- **section numbers in-range** -- of the statute/convention section numbers cited that we can check, the share that fall within the instrument's real article/section count. A high number means the citations are accurate, not invented (e.g. 'ILO C029 Art. 99' would fail, since C029 has 33 articles).
- **hallucinated-citation rate** -- the share of replies containing at least one implausible section number or an out-of-range convention number. The honest test is that the harnessed arm does NOT hallucinate more than baseline despite citing far more.
- This check is **deterministic and judge-independent**, so it is ground-truth-like evidence that partially answers the 'it is all LLM judges' critique.
- **Coverage, stated honestly.** It checks ILO convention numbers (C001..C190) and statute *section* numbers against known ranges -- not every named national statute, so a baseline reply that cites an origin-state statute by name (for example 'Proclamation 923/2016') is not counted here, and it checks citation *plausibility*, not *relevance* to the scenario. A named-statute registry and a relevance check are future work. Reproduce: `python scripts/citation_accuracy.py`.

