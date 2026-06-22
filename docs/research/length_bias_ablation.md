# Length-bias ablation — is the harness lift just longer answers?

LLM judges are known to reward longer responses, and the DueCare harness produces longer responses. So the fair objection is: maybe the LLM-judged lift is a length artifact. This ablation tests it on 1906 stored responses (no new model calls).

> **The judge does reward length (pooled r(length, score) = 0.40), but the harness lift survives controlling for it.** An OLS of score on length + arm attributes only **+0.42/10** of the raw **+1.77** lift to the length increase, and **+1.35/10 to the harness holding length constant** (t = 14.39, |t|>2 ⇒ not chance). The effect is not only length.

## 1. The judge's length sensitivity

- Pooled **Pearson r(response length, judge score) = 0.40** (r² = 0.16, so length explains ~16% of score variance — real, but far from all of it).
- The harness adds **780 chars** per reply on average; that is the length the objection is about.

## 2. OLS decomposition — `score ~ length + arm`

| Term | Coefficient | t-stat | Reading |
|---|---:|---:|---|
| length (per +1000 chars) | +0.533 | 15.1 | the judge's length reward |
| **arm = harnessed** | **+1.348** | **14.39** | **harness effect, length held constant** |

*R² = 0.245, n = 1906. Raw lift +1.77 ≈ length-attributable +0.42 + harness-attributable +1.35.*

## 2b. Controlling for citation density too (the *sharper* objection)

"The judge rewards longer answers" and "the judge rewards citation-dense legal-jargon style" are **different** hypotheses — and the harness adds both. The length-only OLS above does not test the second. So we add a citation-density covariate (ILO/convention/statute markers per 1000 chars): the harness adds **+2.88** citations/1k over baseline. Regressing `score ~ length + citation_density + arm`:

| Term | Coefficient | t-stat |
|---|---:|---:|
| length (per +1000 chars) | +0.526 | — |
| citation density (per +1/1k) | +0.077 | 2.47 |
| **arm = harnessed** | **+1.133** | **8.86** |

With **both length and citation density held constant**, the harness term is **+1.133** (t = 8.86). It survives — the lift is not merely citation-dense style; the harness changes *what* the reply does, not just how legalistic it reads.

## 3. Length-matched comparison (non-parametric control)

Within each length band, do harnessed replies still outscore baseline ones?

| Length band | Baseline | Harnessed | Δ | n |
|---|---:|---:|---:|---:|
| 35-3078 chars | 4.12 | 5.85 | +1.73 | 478 |
| 3080-3796 chars | 6.12 | 6.72 | +0.60 | 476 |
| 3797-4325 chars | 5.68 | 6.94 | +1.26 | 476 |
| 4327-5778 chars | 4.57 | 6.93 | +2.36 | 476 |

If Δ stays positive *within* a length band, the lift is not explained by length.

## 4. Per-pair: does a bigger length increase mean a bigger score increase?

- Pearson r(Δlength, Δscore) over 911 prompt-pairs = **0.26**. A weak correlation means the prompts where the harness helped most are *not* the ones where it added the most length.

## 5. Convergent evidence from the deterministic grader

The deterministic 75-dimension grader (no LLM judge, no length sensitivity by construction) shows the harness **regresses** some dimensions (e.g. `operational_information_provided`, `multilingual_localization`) while sharply improving others (legal grounding, jurisdiction). **Pure length bias cannot produce a decrease.** A uniformly-longer answer would raise every dimension; the harness does not, so its effect is content, not length. See `frontier_failure_report.md`. The strongest content evidence is in `robustness_checks.md` §3 (the harness lifts 21/21 *incidental* dimensions it never injects).

## Conclusion

The judge has a measurable length bias, and we do not hide it. But controlling for length three ways (OLS, length-matched bands, per-pair correlation) **and** for citation density (§2b), the harness retains a positive effect, and the length-immune deterministic grader confirms the gains are dimension-specific, not uniform inflation. Honest reading: a portion of the *LLM-judged* lift is length/style, which is exactly why we report the LLM judge **as a relative paired delta**, cross-check it with the length-immune deterministic floor, and lead the safety claim with the behavioural evidence (the egregious harm-enablement swings), not the judge's absolute score.

