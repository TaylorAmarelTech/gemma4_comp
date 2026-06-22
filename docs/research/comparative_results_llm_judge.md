# Comparative results — per-model harness lift (LLM-judge — primary)

Which models does the DueCare harness help, and how much? This is the head-to-head model leaderboard scored by the **LLM judge (model + full context)** — the primary evaluator, because it reads the whole response and weighs safety holistically rather than matching rigid surface patterns. (The deterministic grader is ceiling-bound on strong models and under-credits the harness; it is the conservative cross-check, not the headline — see `comparative_results.md` and `convergent_validity.md`.)

> Across **1 model(s)** and **911 (prompt × model) pairs**, the LLM judge scores the harness **+1.73 / 10 higher** (paired z=20.9, p=<0.001), winning **73%** of pairs. This is the powerful, non-rigid view; per-model detail below.

## Per-model leaderboard

| # | Model | n | Baseline | Harnessed | Lift | 95% CI | W / L / T | Win % | Cohen's d | p |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | `gemma4:31b` | 911 | 4.98 | 6.72 | **+1.73** | [+1.57, +1.89] | 668 / 210 / 33 | 73% | 0.69 | <0.001 |

## Reading this

- **Lift** is the paired mean of (harnessed − baseline) per prompt; **95% CI** is a seeded 10k-resample bootstrap; **Win %** is the share of prompts improved by more than 0.1; **Cohen's d** is the paired effect size; **p** is a two-sided paired z-test.
- The **LLM judge** reads the whole response with full context and scores safety holistically — a closer proxy for whether an answer is actually safe and helpful to a worker than a keyword/rule grader, though still a model-based proxy, not ground truth (human adjudication of a sample is the natural next step). It is quasi-deterministic (temp 0) and read relatively (paired delta), so each judge's scale offset cancels; judge independence + the multi-judge panel (diverse frontier judges, self-family excluded) are in `frontier_panel_judges.md`.
- Companion analyses: `frontier_perdim_report.md` (where gains land), `frontier_panel_judges.md` (judge panel + agreement), `negative_control.md` (placebo), `convergent_validity.md` (grader divergence), `evaluation_methodology.md` (method + threats).

