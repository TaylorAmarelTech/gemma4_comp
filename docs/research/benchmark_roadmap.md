# DueCare harness-lift benchmark — research & publication roadmap

> Grounded in the current real state (2026-07-16). This is the benchmark/publication
> roadmap; operational engine state lives in the project bible. Every item below is
> scoped against real data (the 78,719-prompt registry, the recorded panel), not
> synthetic studies.

## Where we are (real, verified)

- **Headline:** `gemma4:31b` baseline 48.4 → harnessed 89.1 = **+40.7** over **7,953 paired
  registry prompts**, 3-judge panel, seeded bootstrap 95% CI [+40.2, +41.2], win rate 99.8%,
  and the lift holds within each judge (leave-one-judge-out envelope [+40.4, +40.9]).
- **Cross-model:** every one of 7 graded flagship/frontier models gains (+16 to +43 raw).
  The ceiling-adjusted **normalized-gain** ranking re-orders the board: `gpt-oss:120b` is #1
  on raw lift but last on normalized gain (most headroom, most regressions).
- **Judge agreement (honest):** WITHIN-arm ICC/Pearson (r≈0.72), not the inflated pooled
  r≈0.92 — judges agree strongly on baseline, only moderately on the richer harnessed replies.
- **Exhaustive sweep:** the per-dimension pass grades the full registry in seed-shuffled order,
  so any interim prefix is an unbiased random sample (interim goals reduce prompt COUNT, never
  grading resolution). Live dashboard: `scripts/perdim_interim_goals.py`.

## Next experiments (ranked by evidence value)

1. **Length-matched placebo 4th arm (highest ROI).** The standing confound is that the rubric
   preamble, not the injected knowledge, drives the lift. A placebo arm (same preamble, no
   real GREP/RAG/tool facts) isolates the knowledge effect. Prior recorded runs show ~+3.34
   beyond placebo; a full-registry placebo arm would make this decisive. `scripts/placebo_panel.py`
   exists — wire it as a 4th arm in the perdim sweep.
2. **Blinded human-expert validation.** The honest precondition for any peer-reviewed claim:
   the judges are LLMs, not anti-trafficking professionals. A small blinded expert re-scoring
   of a stratified sample (`scripts/build_human_validation_sample.py`) converts "judge-scored"
   into "expert-validated" on a subset.
3. **Multilingual lift.** The multilingual GREP layer (11 languages) is shipped but the lift is
   only measured in English. Grade a multilingual prompt subset to show the harness generalizes
   beyond English — closes a real P0 gap.
4. **Per-dimension calibration across models.** Which dimension (A–E) each model gains on, and
   where the harness cannot add capacity the base model lacks (small models ~0 on refusal).
5. **Over-refusal / benign-control cost.** The intent split measures whether the harness makes
   models over-refuse legitimate worker questions — the honest cost side of the ledger.

## Next publications (grounded, in flight or queued)

- **Where-the-harness-helps** — lift by difficulty/corridor/category (building).
- **Statistical-robustness** — LOJO envelope, bootstrap CIs, Cohen's d, sign test, forest plot (building).
- **Judge-reliability & calibration** — within-arm ICC, per-judge robustness, leniency.
- **Claim ladder** — what each result proves vs. does NOT (placebo, citation check, sample-size).
- **RuleCard weak-supervision label model** — 451 rules → 80 correlated-witness families →
  effective independent witnesses via the design-effect `m/(1+(m-1)ρ)`; a Snorkel-style label
  model over the deck.
- **Cross-model leaderboard dataset** — the enriched board (normalized gain + per-dimension +
  breakdowns) as a citable machine-readable artifact.

## Honest limitations (kept visible, never hidden)

- Judges are LLMs, not human experts → benchmark evidence, not field detection.
- Sample sizes vary hugely across models (7,953 to 37) → tiny-n lifts are flagged, not ranked.
- No merged weights, no demonstrated victim-identification or real-world detection lift.
- Rubric-preamble placebo confound stands until the placebo arm runs at scale.
