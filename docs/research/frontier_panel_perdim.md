# Multi-judge panel — is the harness lift robust to the choice of judge?

The LLM-judged frontier reports use one judge at temperature 0 — quasi-deterministic, not exact. This panel re-scores the SAME stored responses with several **independent** judges and asks: do they agree on the **lift** (harnessed − baseline)? If they do, the relative comparison does not depend on any one judge — the real answer to the non-determinism concern, stronger than picking a single 'best' judge.

> **The judges may differ on absolute scores, but they agree on the LIFT.** Krippendorff's α = 0.605 — only weak *absolute* agreement (inter-rater reliability of the *absolute* 0–10 scores); meanwhile the *per-model lift* is consistent across judges (mean spread ±1.12/10). We only ever claim the **relative** lift (the paired delta), and that is what is — and must be — judge-robust: absolute-score disagreement cancels in the pairing. This is the empirical version of *read the delta, not the absolute score*.

## Per-model lift, by judge

| Model | n | `gpt-oss:120b` | `glm-5.2` | `qwen3.5:397b` | `kimi-k2.7-code` | `deepseek-v3.2` | Panel mean | Judge spread |
|---|---|---|---|---|---|---|---|---|
| `deepseek-v3.2` | 9 | +5.11 | +4.44 | +8.89 | +4.89 | — | **+5.83** | ±1.78 |
| `gemma4:31b` | 9 | +5.67 | +7.11 | +5.56 | +3.72 | +6.67 | **+5.75** | ±1.17 |
| `glm-5.2` | 9 | +4.56 | — | +7.78 | +3.83 | +4.78 | **+5.24** | ±1.51 |
| `qwen3-coder:480b` | 9 | +5.67 | +6.33 | — | +4.17 | +4.75 | **+5.23** | ±0.83 |
| `qwen3.5:397b` | 9 | +1.56 | +2.0 | — | +2.33 | +2.25 | **+2.04** | ±0.3 |

A &mdash; is a **self-family exclusion**: a judge never scores a response from its own model family (so GLM doesn't judge `glm-5.2`, etc.). **n** is the prompts per model with both arms scored &mdash; modest here (this is a balanced sample on the harder perdim subset, where baselines are weak so the *absolute* lift runs large). This panel's job is to show the lift is **judge-robust**, not to pin its magnitude; the larger-N magnitude estimates are the single-judge reports (`harness_lift_report.md`, `comparative_results_llm_judge.md`).

## Reading this

- **Krippendorff's α** (above) is the inter-rater reliability of the *absolute* 0–10 scores (1 = perfect, ~0 = chance, < 0 = systematic disagreement; ≥0.80 strong, 0.67–0.80 acceptable). A *weak* α together with a *small* lift-spread is the expected, acceptable pattern: judges can anchor their absolute scale differently yet still agree on how much the harness improved a reply — and the paired design uses only the latter.
- **Judge spread** (last column) is the standard deviation of the per-model lift across judges. Small spread = the judges award the same *relative* improvement, so the headline lift is not an artifact of one judge.
- We report the **lift**, not absolute scores, precisely because the lift is what survives judge disagreement (the paired design cancels each judge's scale).
- **Claude Opus** can be added as a premium absolute-calibration judge via subagents (isolated context), but for this relative comparison the independent Ollama panel is sufficient and zero main-context. The deterministic per-dimension report is the judge-free, fully reproducible *floor*; the LLM judge is the primary holistic view.
- **Judges**: `gpt-oss:120b`, `glm-5.2`, `qwen3.5:397b`, `kimi-k2.7-code`, `deepseek-v3.2` — a diverse panel of large frontier models (gpt-oss, GLM, Qwen, Kimi, DeepSeek). Independence is preserved by **self-family exclusion**: a judge never scores its own family (e.g. GLM never judges a GLM candidate), so GLM / Qwen / DeepSeek can serve as judges for the *other* candidates while no model grades itself. Panel over 90 stored responses.

