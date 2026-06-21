# Multi-judge panel — is the harness lift robust to the choice of judge?

The LLM-judged frontier reports use one judge at temperature 0 — quasi-deterministic, not exact. This panel re-scores the SAME stored responses with several **independent** judges and asks: do they agree on the **lift** (harnessed − baseline)? If they do, the relative comparison does not depend on any one judge — the real answer to the non-determinism concern, stronger than picking a single 'best' judge.

> **The judges may differ on absolute scores, but they agree on the LIFT.** Krippendorff's α = 0.48 — only weak *absolute* agreement (inter-rater reliability of the *absolute* 0–10 scores); meanwhile the *per-model lift* is consistent across judges (mean spread ±0.31/10). We only ever claim the **relative** lift (the paired delta), and that is what is — and must be — judge-robust: absolute-score disagreement cancels in the pairing. This is the empirical version of *read the delta, not the absolute score*.

## Per-model lift, by judge

| Model | `gpt-oss:120b` | `gpt-oss:20b` | `kimi-k2.7-code` | Panel mean | Judge spread |
|---|---|---|---|---|---|
| `qwen3-coder:480b` | +2.0 | +2.0 | +2.25 | **+2.08** | ±0.12 |
| `deepseek-v4-flash` | +1.25 | +2.25 | +1.5 | **+1.67** | ±0.42 |
| `glm-5.2` | +1.25 | +1.75 | +0.62 | **+1.21** | ±0.46 |
| `gemma4:31b` | +0.75 | +1.25 | +1.0 | **+1.0** | ±0.2 |
| `deepseek-v3.2` | +1.0 | +1.25 | +0.5 | **+0.92** | ±0.31 |
| `glm-4.7` | +1.0 | +0.5 | +1.0 | **+0.83** | ±0.24 |
| `deepseek-v3.1:671b` | +1.0 | +1.33 | +0.0 | **+0.78** | ±0.57 |
| `deepseek-v4-pro` | +0.5 | +0.75 | +1.0 | **+0.75** | ±0.2 |
| `glm-5` | +0.5 | +1.25 | +0.5 | **+0.75** | ±0.35 |
| `qwen3.5:397b` | +0.75 | +0.75 | +0.5 | **+0.67** | ±0.12 |
| `glm-5.1` | +0.75 | +1.0 | +0.12 | **+0.62** | ±0.37 |

## Reading this

- **Krippendorff's α** (above) is the inter-rater reliability of the *absolute* 0–10 scores (1 = perfect, ~0 = chance, < 0 = systematic disagreement; ≥0.80 strong, 0.67–0.80 acceptable). A *weak* α together with a *small* lift-spread is the expected, acceptable pattern: judges can anchor their absolute scale differently yet still agree on how much the harness improved a reply — and the paired design uses only the latter.
- **Judge spread** (last column) is the standard deviation of the per-model lift across judges. Small spread = the judges award the same *relative* improvement, so the headline lift is not an artifact of one judge.
- We report the **lift**, not absolute scores, precisely because the lift is what survives judge disagreement (the paired design cancels each judge's scale).
- **Claude Opus** can be added as a premium absolute-calibration judge via subagents (isolated context), but for this relative comparison the independent Ollama panel is sufficient and zero main-context. The deterministic per-dimension report remains the judge-free, fully reproducible headline.
- **Judges**: `gpt-oss:120b`, `gpt-oss:20b`, `kimi-k2.7-code` (all independent of the candidate models). Panel over 86 stored responses.

