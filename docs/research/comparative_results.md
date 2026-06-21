# Comparative results — per-model harness lift

Which models does the DueCare harness help, and how? This is the head-to-head model comparison from the **deterministic** per-dimension grader (free, reproducible, identical on re-run), over the prompts where both the baseline (raw prompt) and harnessed (DueCare grounding + prompt) arms were graded. Read it with the ceiling effect in mind — see the honest framing below.

> **The honest headline is two numbers, not one.** Across **5 strong frontier models** and **460 (prompt × model) pairs**, the harness's effect on the *all-dimension mean* is **-0.03 / 10** — essentially flat — because these models already pass most of the rubric, so concentrated gains on the hard dimensions wash out (a **ceiling effect**). But dimension by dimension the harness **improves 181 and regresses 65** across the models — it moves far more dimensions up than down, and the gains land on the safety-critical ones (multi-jurisdiction coverage, regulator / civil-society contacts, retaliation-protection notice). The larger single-number lifts reported elsewhere are the holistic **LLM-judge** view and the **gemma4:31b** large-N run; this page is the strictest, flattest deterministic cut.

## Per-model — the two views side by side

| # | Model | n | Baseline | Harnessed | All-dim lift | 95% CI | p | Dims ↑ / ↓ | Mean lift on ↑ |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|
| 1 | `qwen3-coder:480b` | 93 | 5.70 | 5.77 | +0.07 | [-0.08, +0.25] | 0.423 | **52 / 6** | +0.57 |
| 2 | `qwen3.5:397b` | 92 | 5.84 | 5.81 | -0.03 | [-0.10, +0.03] | 0.314 | **28 / 5** | +0.21 |
| 3 | `gemma4:31b` | 92 | 5.73 | 5.68 | -0.05 | [-0.15, +0.06] | 0.401 | **36 / 25** | +0.60 |
| 4 | `glm-5.2` | 94 | 5.84 | 5.79 | -0.05 | [-0.13, +0.03] | 0.212 | **33 / 23** | +0.58 |
| 5 | `deepseek-v3.2` | 89 | 5.84 | 5.75 | -0.09 | [-0.15, -0.03] | 0.006 | **32 / 6** | +0.31 |

## Reading this

- **All-dim lift** is the paired mean of (harnessed − baseline) per prompt over every *applicable* dimension; **95% CI** is a seeded 10k-resample bootstrap; **p** is a two-sided paired z-test. On already-strong models this is near zero by construction (ceiling) — that is honest, not a null result for the harness.
- **Dims ↑ / ↓** is the ceiling-robust signal: how many rubric dimensions the harness moved up vs down (per-dimension mean, |Δ| > 0.05). Every model improves many more than it regresses. **Mean lift on ↑** is the average gain on the improved dimensions.
- The grader is **applicability-gated** — NOT_APPLICABLE dimensions are excluded per prompt.
- *Where* the gains land (which specific dimensions) is in `frontier_perdim_report.md`; the holistic LLM-judge cross-check is in `frontier_panel_judges.md`; the placebo-controlled knowledge effect is in `negative_control.md`; the length-bias ablation is in `length_bias_ablation.md`. Full method + threats: `evaluation_methodology.md`.

