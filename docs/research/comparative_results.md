# Comparative results — per-model harness lift (deterministic — cross-check)

The conservative cross-check: the head-to-head leaderboard from the **deterministic** per-dimension grader (free, reproducible, identical on re-run). The LLM judge is the primary view (`comparative_results_llm_judge.md`); this rigid text-matcher is included as a reproducible floor. Read it with the ceiling effect in mind.

> Across **5 strong frontier models** and **500 (prompt × model) pairs**, the harness's effect on the deterministic *all-dimension mean* is **-0.02 / 10** — essentially flat — because these models already pass most of the rubric, so concentrated gains wash out (a **ceiling effect**); the rigid matcher under-credits the harness. Dimension by dimension it still **improves 184 and regresses 73**, concentrated on the safety-critical dimensions. The real lift is the LLM-judge view.

## Per-model leaderboard

| # | Model | n | Baseline | Harnessed | Lift | 95% CI | W / L / T | Win % | Cohen's d | p |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | `qwen3-coder:480b` | 102 | 5.71 | 5.76 | **+0.05** | [-0.09, +0.22] | 43 / 43 / 16 | 42% | 0.06 | 0.529 |
| 2 | `qwen3.5:397b` | 100 | 5.83 | 5.82 | **-0.01** | [-0.08, +0.05] | 38 / 31 / 31 | 38% | -0.04 | 0.680 |
| 3 | `gemma4:31b` | 100 | 5.71 | 5.70 | **-0.02** | [-0.12, +0.09] | 35 / 50 / 15 | 35% | -0.03 | 0.776 |
| 4 | `glm-5.2` | 102 | 5.84 | 5.78 | **-0.06** | [-0.14, +0.01] | 35 / 39 / 28 | 34% | -0.16 | 0.111 |
| 5 | `deepseek-v3.2` | 96 | 5.83 | 5.76 | **-0.08** | [-0.14, -0.02] | 29 / 45 / 22 | 30% | -0.26 | 0.010 |

## Ceiling-robust signal — dimensions improved vs regressed

| Model | Dims ↑ / ↓ | Mean lift on ↑ |
|---|---:|---:|
| `qwen3-coder:480b` | **50 / 8** | +0.57 |
| `qwen3.5:397b` | **31 / 8** | +0.20 |
| `gemma4:31b` | **36 / 25** | +0.65 |
| `glm-5.2` | **32 / 26** | +0.57 |
| `deepseek-v3.2` | **35 / 6** | +0.29 |

## Reading this

- **Lift** is the paired mean of (harnessed − baseline) per prompt; **95% CI** is a seeded 10k-resample bootstrap; **Win %** is the share of prompts improved by more than 0.1; **Cohen's d** is the paired effect size; **p** is a two-sided paired z-test.
- **Dims ↑ / ↓** is the ceiling-robust signal: rubric dimensions the harness moved up vs down (per-dimension mean, |Δ| > 0.05). The grader is applicability-gated; treat it as a conservative floor, not the headline.
- Companion analyses: `frontier_perdim_report.md` (where gains land), `frontier_panel_judges.md` (judge panel + agreement), `negative_control.md` (placebo), `convergent_validity.md` (grader divergence), `evaluation_methodology.md` (method + threats).

