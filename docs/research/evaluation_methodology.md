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
| **LLM judge** | Strong model(s) scoring per dimension against a **192-dimension** rubric (`harness_lift_dimensions.json`); a diverse panel cross-checks robustness | **Headline** (holistic) | No — quasi-deterministic (temp 0); read as a **relative** paired delta |
| **`grade_response_universal`** | DueCare's rule-based grader, **75 dimensions** (~32 applicable per prompt via applicability gating; 77 cells incl. 2 derived) | **Conservative, reproducible floor** + per-dimension diagnostic | **Yes — deterministic** (same input → same output) |

The **headline lift (+1.73/10) is the LLM judge's** — it reads the whole reply the way a person
would. The deterministic grader is the **conservative floor**: free, exactly reproducible, immune to
LLM-judge pathologies, and used for the per-dimension breakdown. We report **both** and treat neither
as a proxy for the other (see the divergence below). *Dimension-count note, because three numbers
circulate: the deterministic grader has **75** rubric dimensions (77 cells incl. 2 derived; ~32
applicable per prompt); the per-dimension **LLM-judge rubric has 192**; the FDR analysis tests the
**69** deterministic dimensions that reached ≥10 paired observations — a data-driven subset, not the
rubric size.*

**The two graders are not interchangeable — and we say so.** On the high-variance 1000-prompt
gemma4:31b run, the deterministic grader and the LLM judge **agree on direction** (both find a
positive average lift: deterministic **+0.18**, judge **+1.73**) and trend together in aggregate (the
top deterministic-lift bin gets the highest judge-lift), but their **per-prompt correlation is weak**
(Pearson r ≈ 0.18). The deterministic grader is a strict surface-pattern/citation matcher with a
small dynamic range on strong models, so it reports a **small, conservative** lift; the LLM judge
weighs safety holistically, so it reports a **larger** one. Consequences, stated plainly: the large
single-number lift (e.g. **+1.73**) is the **LLM-judge** view; the deterministic grader is a
conservative reproducible floor plus the per-dimension diagnostic; and neither is treated as a proxy
for the other. Full analysis: `convergent_validity.md`. On already-strong frontier models the
deterministic all-dimension *mean* is near-flat (a ceiling effect — the harness improves far more
dimensions than it regresses, but the mean washes out); see `comparative_results.md`.

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
   per-pair length increase (r = 0.27). (The +1.75 is the n=146 ablation subset's mean, not the
   n=911 headline +1.73.) *Open item:* this controls for length but not citation density — see §5.
   → `length_bias_ablation.md`.
2. **Judge non-determinism.** Temp 0 is quasi-deterministic, not exact. Mitigations: the
   LLM-judge is read **relatively** (paired delta); and a **multi-judge panel** measures inter-judge
   agreement on the lift. → `frontier_panel_perdim.md` (current 5-judge diverse panel;
   `frontier_panel_judges.md` is the earlier 3-judge run).
3. **Self-enhancement / non-independence.** A judge must not grade its own family. We use a **diverse
   panel of large frontier judges** — `gpt-oss:120b`, `glm-5.2`, `qwen3.5:397b`, `kimi-k2.7-code`,
   `deepseek-v3.2` — and preserve independence by **self-family exclusion**: a judge never scores a
   response from its own family (e.g. GLM never judges a GLM candidate; `multi_judge.model_family` +
   `run_panel(exclude_self_family=True)`). This lets strong models that are *also* candidates serve as
   judges for the *other* candidates without self-enhancement bias, rather than restricting the panel
   to a fixed non-candidate trio.
4. **Construct validity / rubric circularity** (the strongest critique). The harness injects "name
   the indicators, cite the ILO convention, give the hotline," and the deterministic grader
   **keyword-matches that exact vocabulary** — so a gain on `ilo_indicator_naming` is, mechanically,
   partly tautological. We do not hand-wave this. *Three lines of defense, the third decisive:*
   (a) the dimensions are grounded in external frameworks (ILO indicators, C029/C181/C188/C189,
   Palermo, ICRMW, national statutes), not invented to flatter the harness;
   (b) the harness **regresses** some dimensions, which a uniform teach-to-the-rubric inflater would
   not (weak on its own — could be the same instruction crowding out other content);
   (c) **the harness lifts dimensions it never injects.** Splitting the LLM-judge dimensions into
   *directly-injected* vs *incidental* (response qualities the preamble never mentions): **21 of 21
   incidental dimensions improve** (mean **+1.47**) — empathy-without-judgment (+2.18), plain-language
   rights, safety-first ordering, victim-blaming avoidance, even **PII minimization** (+0.25) — none
   of which the preamble asks for. The most circularity-resistant evidence is the egregious set: the
   baseline wrote a fee-concealment contract and the harnessed arm refused (a swing on
   *harm-enablement*, a behavioural dimension no keyword coaches). The effect is generalized safety
   behaviour, not echoed tokens. → `robustness_checks.md` §3. (A blind grader without the ILO
   checklist would close this fully — see §6.)
5. **Ceiling effects.** Strong models already satisfy easy dimensions, so a naive all-dimension mean
   is uninformative; we report **per-dimension** lift and improve/neutral/regress counts instead.
6. **"Any preamble helps" confound** (would *any* official-sounding safety reminder produce the lift?).
   *Controlled.* A **negative-control placebo arm** prepends generic "read carefully, be thorough, be
   ethical" boilerplate that is **length-matched per prompt** to the real grounding but carries zero
   domain knowledge. The diagnostic contrast is **harnessed − placebo**: the lift that remains after
   subtracting the generic-preamble effect, attributable to the harness's knowledge (fired rules +
   citations + ILO-reasoning) because that is the only thing the harnessed arm has that the placebo
   does not. → `negative_control.md`.
7. **Context leakage in the LLM judge** (the judge favouring an arm for reasons other than answer
   quality). *Guarded.* Each judge call sees **only** the original prompt + one response — never the
   arm label, never the grounding preamble (grading the harness's own injected citations would be
   circular), never the other arm's response; calls are stateless (no cross-response accumulation).
   Verified at the data level (**0 preamble leaks** across stored harnessed rows — the harnessed arm's
   `prompt_text` is the original worker message) and locked at the code level by
   `tests/test_context_hygiene.py`.
8. **Non-answers scored as bad answers** (a refusal or a format failure is not a low-quality answer).
   *Separated.* Format failures (empty / reasoning-trace / too-short) are flagged and **excluded** from
   quality scoring; **refusals are reported separately, not excluded** — refusing a recruiter-side
   exploitation request is the *desired* behaviour (rewarded by the grader's harm-enablement /
   grounded-refusal dimensions), and the per-dimension grader already scores good-vs-bad refusal per
   prompt. → `refusal_analysis.md`.
9. **Prompt non-independence / clustering.** Prompts are template-generated (ID-prefix families) and
   each is answered by several models, so they are not i.i.d. draws. *Measured.* For the **headline**
   single-model 1000-prompt run, the intra-cluster correlation of the lift is ≈0 (ICC 0.004) →
   design effect **1.06**, so the +1.73 CI is essentially unchanged (±0.17→±0.18). For the **pooled
   multi-model** deterministic run the design effect is ~**1.6** (clustered by model). Consequence,
   stated plainly: the **pooled per-dimension FDR counts ("22 improve / 6 regress") and pooled z-tests
   are anticonservative** (they treat (prompt×model) pairs as independent) and are reported as
   **exploratory**; the defensible inferential claims are the **per-model** paired tests (one delta
   per prompt) and the cluster-robust headline CI. → `robustness_checks.md` §2.
10. **Egregious failures concentrate in mid-size models (a deployment feature, stated honestly).**
    All 27 baseline replies scoring ≥7/10 on active harm are `gemma4:31b`; the strong frontier models
    rarely produced egregious baselines. So two claims are kept **separate**: (i) on a small local
    model the harness prevents concrete, severe harms (strong, behavioural) — which is *the point*,
    since the deployment thesis is on-device local Gemma for NGOs who cannot use frontier APIs; and
    (ii) on strong frontier models the harness shifts rubric/LLM-judge scores upward (real but smaller
    and more contestable). We never merge these into one number. → `egregious_responses.md`.
11. **The placebo control is on the deterministic grader only.** The negative control's
    harnessed−placebo on the rigid grader is **marginal and not significant** (+0.08, p=0.064) — the
    grader is too ceiling-bound to separate the arms. The conclusive "any preamble" test — placebo
    vs harnessed on the **LLM judge**, where the +1.73 lives — is **not yet run** and is the single
    highest-value missing experiment. Stated as an open item, not a closed one. → `negative_control.md`.
12. **Shared LLM-judge bias.** Self-family exclusion stops a model grading itself, but **all** judges
    are instruction-tuned LLMs that may share a preference for citation-dense, structured, refusal-
    flavoured text — exactly what the harness adds. Inter-judge agreement on the *lift* shows the
    result is not one judge's artifact, but **cannot rule out a bias common to all LLM judges**; only
    human-expert ratings (§6) can. The panel is also all-open-model (no GPT/Claude/Gemini).
13. **Response-driven applicability.** Applicability is decided per response, so the richer harnessed
    reply activates ~3–4 more dimensions; averaging each arm over its own set is not a clean paired
    comparison. *Checked:* restricting to the dimensions scored in **both** arms (intersection) the
    deterministic lift is **+0.19 vs +0.006** — the confound *under*-credits the harness, it does not
    manufacture the lift; the LLM-judge headline (one holistic score) is unaffected. → `robustness_checks.md` §1.
14. **Small samples carry several claims.** The per-model panel is **n=9 prompts/model**; the Opus
    cross-check is **n=24–28**; the length ablation is **n=146**; the "+1.09 across 11 models" is
    **n=4 prompts each**. These are directional, not definitive; at those n the paired z-test is mildly
    anticonservative (a t-reference would widen the small-n p's), the Krippendorff α (0.605) is
    unstable, and for one model (qwen3.5) the judges disagree on the lift by >3 points — so
    "judge-robust" holds for 4/5 models, not universally. Treat small-n tables as exploratory and read
    the n at point of use.

## 5. Limitations (honest — these bound the claims)

- **Synthetic prompts.** Composite/synthetic scenarios (no real PII). They are grounded in the
  benchmark's exploitation taxonomy but are not a sample of real worker messages; distributional
  validity is assumed, not measured.
- **Our own rubric.** The 75 deterministic dimensions (and the 192-dimension LLM-judge rubric) are
  DueCare's. They are externally grounded but have **not** been validated for inter-annotator
  agreement by independent experts.
- **The length ablation controlled for length, not citation density.** The OLS shows the lift is not
  *length*, but the sharper form of the style critique — "the judge rewards citation-dense / legal-
  jargon style" — is not the same hypothesis and was not separately partialled out. A
  citation-density covariate (and scaling the ablation past n=146) is an open item.
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

> "On *N* synthetic, composite trafficking-safety prompts, prepending the DueCare grounding preamble
> raised an independent **LLM-judge** panel's paired score by *L*/10 (length-robust by OLS,
> judge-robust across a self-family-excluded panel, cluster-robust on the single-model run); the
> conservative deterministic 75-dimension grader improved *K* of the 69 tested dimensions
> (exploratory — pooled per-dimension p's are not clustering-corrected). The largest, most concrete
> gains are on a mid-size local model where baseline replies were sometimes actively harmful. Not
> validated against human anti-trafficking experts; not measured on real worker messages or
> deployment outcomes."

State the grader, the paired design, the controls, the small-/clustered-n caveats, and the
human-validation caveat every time. Never report an LLM-judge absolute score as a calibrated safety
measure, and never merge the "small local model rescued from harm" claim with the "frontier models
shifted upward" claim into a single number.
