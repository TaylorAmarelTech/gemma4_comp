# Length-bias ablation — is the harness lift just longer answers?

LLM judges are known to reward longer responses, and the DueCare harness produces longer responses. So the fair objection is: maybe the LLM-judged lift is a length artifact. This ablation tests it on 146 stored responses (no new model calls).

> **The judge does reward length (pooled r(length, score) = 0.56), but the harness lift survives controlling for it.** An OLS of score on length + arm attributes only **+0.63/10** of the raw **+1.75** lift to the length increase, and **+1.12/10 to the harness holding length constant** (t = 4.6, |t|>2 ⇒ not chance). The effect is not only length.

## 1. The judge's length sensitivity

- Pooled **Pearson r(response length, judge score) = 0.56** (r² = 0.32, so length explains ~32% of score variance — real, but far from all of it).
- The harness adds **1710 chars** per reply on average; that is the length the objection is about.

## 2. OLS decomposition — `score ~ length + arm`

| Term | Coefficient | t-stat | Reading |
|---|---:|---:|---|
| length (per +1000 chars) | +0.370 | 4.75 | the judge's length reward |
| **arm = harnessed** | **+1.120** | **4.6** | **harness effect, length held constant** |

*R² = 0.403, n = 146. Raw lift +1.75 ≈ length-attributable +0.63 + harness-attributable +1.12.*

## 3. Length-matched comparison (non-parametric control)

Within each length band, do harnessed replies still outscore baseline ones?

| Length band | Baseline | Harnessed | Δ | n |
|---|---:|---:|---:|---:|
| 859-3674 chars | 7.36 | 8.00 | +0.64 | 37 |
| 3690-4405 chars | 7.75 | 9.46 | +1.71 | 37 |
| 4426-5464 chars | 8.64 | 9.64 | +1.00 | 36 |
| 5475-10525 chars | 8.80 | 9.68 | +0.88 | 36 |

If Δ stays positive *within* a length band, the lift is not explained by length.

## 4. Per-pair: does a bigger length increase mean a bigger score increase?

- Pearson r(Δlength, Δscore) over 73 prompt-pairs = **0.27**. A weak correlation means the prompts where the harness helped most are *not* the ones where it added the most length.

## 5. Convergent evidence from the deterministic grader

The strongest argument is that the deterministic 69-dimension grader (no LLM judge, no length sensitivity by construction) shows the harness **regresses** some dimensions (e.g. `operational_information_provided`, `multilingual_localization`) while sharply improving others (legal grounding, jurisdiction). **Pure length bias cannot produce a decrease.** A uniformly-longer answer would raise every dimension; the harness does not, so its effect is content, not length. See `frontier_failure_report.md`.

## Conclusion

The judge has a measurable length bias, and we do not hide it. But controlling for length three independent ways — OLS coefficient, length-matched bands, and per-pair correlation — the harness retains a positive effect, and the deterministic grader (length-immune) confirms the gains are dimension-specific, not uniform inflation. The honest reading: a portion of the *LLM-judged* lift is length, which is why the **deterministic per-dimension grader is the headline metric** and the LLM-judge view is the secondary, length-caveated companion.

