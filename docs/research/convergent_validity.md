# Convergent validity — how far do the two graders agree?

DueCare scores each response two **independent** ways: a deterministic rule-based grader (the reproducible per-dimension headline) and an LLM judge. This measures their agreement on the high-variance **harness_lift_1000** run, where both graders scored every response — the right place to test it, since the deterministic grader is ceiling-bound (near-constant) on already-strong models, which would understate agreement on a compressed subset.

> **The honest result is partial, directional convergence — not interchangeable graders.** Both independently find the harness helps on average (deterministic lift **+0.18**, judge lift **+1.73**, both > 0), and mean judge-lift trends up across deterministic-lift bins — directional convergence. But the per-prompt **lift correlation is negligible (Pearson r = 0.176)** and absolute-score correlation is negligible (r = 0.184): the deterministic grader (a strict surface-pattern matcher, ceiling-bound) and the holistic judge **agree on direction but diverge on magnitude and per-prompt ranking.** Neither is a proxy for the other; we report both.

## Three views of agreement

| View | n | Pearson r | Spearman ρ | strength |
|---|---:|---:|---:|---|
| Absolute scores (per prompt × arm) | 1906 | 0.184 | 0.056 | negligible |
| **Harness lift (per prompt)** | 911 | 0.176 | 0.161 | negligible |

Per-prompt **sign agreement** on the lift: **50%** (both graders agree whether the harness helped, hurt, or was neutral on that prompt).

## Directional convergence — mean judge-lift across deterministic-lift bins

If the deterministic grader carries real signal, prompts it scores as higher-lift should also get higher judge-lift, even if the per-prompt correlation is noisy.

| Det-lift bin (low→high) | n | mean det lift | mean judge lift |
|---:|---:|---:|---:|
| 1 | 183 | -0.39 | +1.58 |
| 2 | 182 | -0.06 | +1.60 |
| 3 | 182 | +0.09 | +1.07 |
| 4 | 182 | +0.25 | +1.53 |
| 5 | 182 | +0.99 | +2.88 |

## Reading this honestly

- **What converges:** the *direction*. Two independently-built graders both find the harness raises safety on average, and they trend together in aggregate. That the result survives two unrelated scoring methods is real evidence it is not an artifact of one method.
- **What does not:** the *magnitude and per-prompt ranking*. The deterministic grader is a strict pattern/citation matcher with a small dynamic range on strong models (so it reports a small lift); the LLM judge holistically weighs safety (so it reports a larger one). Their weak per-prompt correlation means we must **not** treat the cheap deterministic grader as a stand-in for the holistic judge.
- **Consequence for the headline:** the large single-number lift is the **LLM-judge** view (`harness_lift_report.md`); the deterministic grader is a **conservative, reproducible floor** and the per-dimension diagnostic (`comparative_results.md`, `frontier_perdim_report.md`). Ground truth from human experts is still the missing piece (`evaluation_methodology.md` §6).

