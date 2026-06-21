# DueCare evaluation methodology — graders, statistics, threats, and limitations

This is the methodology spine for every DueCare harness-lift / model-failure result. It states
how we measure, what we control for, and — honestly — what we do not yet establish. Written so a
reviewer or competition judge can assess the work's rigor in one place. Every claim links to the
artifact that produces it. (The separate single-arm domain-sense study has its own writeup in
`model_failure_study_methodology.md`; this document covers the paired harness-lift evaluation.)

## 1. The question and the design

**Question.** Does wrapping a model in the DueCare harness (GREP rules + retrieved context + an
evidence-first reasoning preamble; the model weights are unchanged) improve its trafficking-safety
responses — and where does it fail?

**Design.** Strictly **paired**: each prompt is answered by each model in two arms — **baseline**
(raw prompt) and **harnessed** (`build_harness_preamble` + prompt) — and both arms are graded
identically. The unit of effect is the **per-prompt delta** (harnessed − baseline), so any
grader bias that is constant across arms cancels. We report the delta, not absolute scores.

## 2. Two graders, deliberately

| Grader | What it is | Role | Reproducible? |
|---|---|---|---|
| **`grade_response_universal`** | DueCare's rule-based grader, 69 rubric dimensions, one score per applicable dimension | **Primary / headline** | **Yes — deterministic** (same input → same output) |
| **LLM-judge panel** | Strong models scoring a 0–10 rubric, several independent judges | Secondary holistic companion | No — quasi-deterministic (temp 0) |

The headline metric is the **deterministic** grader: it needs no model at judging time, is exactly
reproducible, and is not subject to LLM-judge pathologies. The LLM-judge view is a holistic
cross-check, reported **as relative** and with the controls below.

## 3. Statistical methods

- **Paired per-prompt deltas**; mean lift over prompts.
- **95% CI** by seeded percentile **bootstrap** (`scripts/lift_stats.py`).
- **Cohen's d (paired)** for effect size; **win rate** at a fixed delta threshold.
- **OLS** for the length-bias decomposition (`scripts/length_bias_ablation.py`).
- **Failure rate** := share of applicable dimension-cells scoring `< 5/10`, broken down by theme,
  exploitation category, and difficulty (`scripts/build_frontier_failure_report.py`).

## 4. Threats to validity, and what we did about each

1. **LLM-judge length bias** (judges reward longer answers; the harness lengthens answers).
   *Tested.* The judge does reward length (pooled r = 0.56), but an OLS attributes only **+0.63**
   of the raw **+1.75** lift to length and **+1.12 to the harness holding length constant**
   (t = 4.6); the lift also survives **length-matched** bands and is weakly correlated with the
   per-pair length increase (r = 0.27). → `length_bias_ablation.md`.
2. **Judge non-determinism.** Temp 0 is quasi-deterministic, not exact. Mitigations: the
   **deterministic grader is the headline**; the LLM-judge is read **relatively** (paired delta);
   and a **multi-judge panel** measures inter-judge agreement on the lift. → `frontier_panel_judges.md`.
3. **Self-enhancement / non-independence.** A judge must not grade its own family. The panel judges
   (`gpt-oss:120b`, `gpt-oss:20b`, `kimi-k2.7-code`) are all **outside** the glm/deepseek/qwen/gemma
   candidate families.
4. **Construct validity / rubric circularity.** The harness injects "name indicators, cite ILO
   conventions, give contacts," and the rubric rewards those — a real circularity. Our defense: the
   dimensions are grounded in external frameworks (ILO forced-labour indicators, ILO C029/C181/C188/
   C189, the Palermo Protocol, ICRMW, national statutes), not invented to flatter the harness; and
   the deterministic grader shows the harness **regresses** some dimensions, which a "teach-to-the-
   rubric" artifact would not. This is acknowledged, not resolved (see Limitations).
5. **Ceiling effects.** Strong models already satisfy easy dimensions, so a naive all-dimension mean
   is uninformative; we report **per-dimension** lift and improve/neutral/regress counts instead.

## 5. Limitations (honest — these bound the claims)

- **Synthetic prompts.** Composite/synthetic scenarios (no real PII). They are grounded in the
  benchmark's exploitation taxonomy but are not a sample of real worker messages; distributional
  validity is assumed, not measured.
- **Our own rubric.** The 69 dimensions are DueCare's. They are externally grounded but have **not**
  been validated for inter-annotator agreement by independent experts.
- **No human-expert ground truth yet.** The strongest missing piece. Neither grader has been
  correlated against ratings from anti-trafficking practitioners or labour lawyers. Until that
  exists, "improves safety" means "improves rubric-measured safety," not "improves expert-judged
  outcomes." A validation study is planned (§6).
- **Recognition + response quality, not deployment outcomes.** We measure what the model *says*, not
  what happens to a worker. No field/RCT evidence.
- **Judge coverage.** The LLM-judge panel uses open models on Ollama-cloud; closed frontier judges
  (GPT/Claude/Gemini) are not yet in the panel.

## 6. Planned human-expert validation (the next rigor step)

Draw a **stratified sample** across exploitation category × difficulty × arm; have ≥2 domain
experts independently rate each item on the same rubric; report **grader↔human correlation**
(Spearman) and **inter-expert agreement** (Krippendorff's α / Cohen's κ). A high correlation
converts the automated scores from "our rubric's opinion" to "a validated proxy for expert
judgment" — the single change that most raises the work's standing.

## 7. Reproducibility

Every number ties to `(git_sha, checkpoint)`. Generation + deterministic grading:
`scripts/harness_lift_local.py`; reports: `build_frontier_perdim_report.py`,
`build_frontier_failure_report.py`, `frontier_report.py`; ablation: `length_bias_ablation.py`;
panel: `multi_judge.py`. Checkpoints persist full responses under `reports/`, so any score is
re-derivable. The deterministic grader makes the headline bit-for-bit reproducible.

## 8. How to cite a result responsibly

> "On *N* synthetic trafficking-safety prompts graded by DueCare's deterministic 69-dimension
> rubric, the harness improved *K* of 69 dimensions (and regressed *J*); on an independent
> LLM-judge panel the paired lift was *L*/10, robust to length (OLS) and to judge choice (panel
> agreement). Not yet validated against human experts."

State the grader, the paired design, the controls, and the human-validation caveat every time.
Do not report an LLM-judge absolute score as a calibrated safety measure.
