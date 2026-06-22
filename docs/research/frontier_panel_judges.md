# Multi-judge panel — is the harness lift robust to the choice of judge?

The LLM-judged frontier reports use one judge at temperature 0 — quasi-deterministic, not exact. This panel re-scores the SAME stored responses with several **independent** judges and asks: do they agree on the **lift** (harnessed − baseline)? If they do, the relative comparison does not depend on any one judge — the real answer to the non-determinism concern, stronger than picking a single 'best' judge.

> **The judges differ on absolute scores and on exact magnitude, but they agree on the DIRECTION of the lift.** Under this **8-judge** panel, **11 of 11 candidate models** show a positive panel-mean lift (panel mean **+0.85/10**), and the cross-family-only mean (below) confirms same-family judges do not drive it. Krippendorff's α = 0.118 (weak — judges anchor their absolute scales differently). The per-judge *magnitudes* are noisy at this small n (mean spread ±0.76/10, comparable to the smaller per-model lifts), so from the panel we claim the **sign and rough ordering** of the lift, not its magnitude — the magnitude is the large-N single-judge reports (`harness_lift_report.md`, `comparative_results_llm_judge.md`). The paired design cancels each judge's absolute scale; this is *read the delta's direction, not one judge's number*.

## Per-model lift, by judge

| Model | n | `gpt-oss:120b` | `gpt-oss:20b` | `glm-5.2` | `qwen3.5:397b` | `qwen3-coder:480b` | `kimi-k2.7-code` | `deepseek-v4-pro` | `deepseek-v4-flash` | Panel mean | Judge spread |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `qwen3-coder:480b` | 4 | +2.0 | +2.0 | +3.25 | +5.5 | +2.0 | +2.25 | +2.0 | +2.25 | **+2.66** | ±1.15 |
| `deepseek-v4-flash` | 4 | +1.25 | +2.25 | +1.0 | +1.75 | +0.25 | +1.5 | +0.5 | +0.5 | **+1.12** | ±0.65 |
| `deepseek-v3.2` | 4 | +1.0 | +1.25 | +0.25 | +5.0 | +0.25 | +0.5 | +0.0 | +0.0 | **+1.03** | ±1.56 |
| `glm-5` | 4 | +0.5 | +1.25 | +0.0 | +3.33 | +0.75 | +0.5 | +0.0 | +0.0 | **+0.79** | ±1.04 |
| `glm-4.7` | 4 | +1.0 | +0.5 | +0.0 | +2.5 | +1.0 | +1.0 | +0.0 | +0.25 | **+0.78** | ±0.76 |
| `glm-5.1` | 4 | +0.75 | +1.0 | +0.0 | +3.33 | +0.5 | +0.12 | +0.0 | +0.0 | **+0.71** | ±1.05 |
| `glm-5.2` | 4 | +1.25 | +1.75 | +0.25 | +0.0 | +0.75 | +0.62 | +0.0 | +0.0 | **+0.58** | ±0.61 |
| `gemma4:31b` | 4 | +0.75 | +1.25 | +0.0 | +0.0 | +0.5 | +1.0 | +0.0 | +0.5 | **+0.5** | ±0.45 |
| `deepseek-v3.1:671b` | 3 | +1.0 | +1.33 | +0.33 | +0.0 | +0.0 | +0.33 | +0.33 | +0.33 | **+0.46** | ±0.44 |
| `qwen3.5:397b` | 4 | +0.75 | +0.75 | +0.0 | +0.0 | +0.75 | +0.5 | +0.0 | +0.25 | **+0.38** | ±0.33 |
| `deepseek-v4-pro` | 4 | +0.5 | +0.75 | +0.25 | +0.0 | +0.0 | +1.0 | +0.0 | +0.0 | **+0.31** | ±0.37 |

This panel uses **all available large models as judges** and, by design, **includes same-family judge–candidate pairs** (e.g. `glm-5.2` judging a `glm-*` candidate). Dropping every same-family judge–candidate pair, the panel mean lift is **+0.91/10** vs **+0.85/10** with all judges — the result does not depend on same-family judges. **n** is the prompts per model with both arms scored; the per-judge columns make any single judge's or family's influence visible. The panel's job is to show the lift is **judge-robust**, not to pin its magnitude (the larger-N magnitude is in the single-judge reports `harness_lift_report.md`, `comparative_results_llm_judge.md`).

## Reading this

- **Krippendorff's α** (above) is the inter-rater reliability of the *absolute* 0–10 scores (1 = perfect, ~0 = chance, < 0 = systematic disagreement; ≥0.80 strong, 0.67–0.80 acceptable). A *weak* α together with a *small* lift-spread is the expected, acceptable pattern: judges can anchor their absolute scale differently yet still agree on how much the harness improved a reply — and the paired design uses only the latter.
- **Judge spread** (last column) is the standard deviation of the per-model lift across judges. Small spread = the judges award the same *relative* improvement, so the headline lift is not an artifact of one judge.
- We report the **lift**, not absolute scores, precisely because the lift is what survives judge disagreement (the paired design cancels each judge's scale).
- **Claude Opus** can be added as a premium absolute-calibration judge via subagents (isolated context), but for this relative comparison the independent Ollama panel is sufficient and zero main-context. The deterministic per-dimension report is the judge-free, fully reproducible *floor*; the LLM judge is the primary holistic view.
- **Judges**: `gpt-oss:120b`, `gpt-oss:20b`, `glm-5.2`, `qwen3.5:397b`, `qwen3-coder:480b`, `kimi-k2.7-code`, `deepseek-v4-pro`, `deepseek-v4-flash` — a broad panel of the newest, largest frontier models across families (gpt-oss, GLM, Qwen, Kimi, DeepSeek). Per the design choice to use *all available large models as judges*, same-family judge–candidate pairs are **included**; the cross-family-only panel mean (above) plus the per-judge columns confirm no single family drives the result, and the paired (lift) design cancels each judge's absolute scale. Panel over 86 stored responses.

