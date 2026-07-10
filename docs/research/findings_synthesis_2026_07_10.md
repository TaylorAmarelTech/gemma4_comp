# DueCare findings synthesis — the honest, publish-ready version (2026-07-10)

This consolidates the rigor work into the claim we can actually defend, the evidence for it, and — given
equal weight — the evidence against it. It was written after an internal adversarial peer-review pass and a
web-verified legal audit, and it deliberately states the magnitude caveats those passes surfaced. It does
not supersede the earlier per-topic reports; it is the honest headline over them.

## The claim we can defend (and the ones we cannot)

**Defensible:** a domain safety harness (deterministic GREP indicator rules + RAG legal grounding + an
ILO-reasoning preamble) measurably improves the **rubric-scored trafficking-safety *quality*** of a Gemma 4
model's replies on tested prompts, and improves it beyond a length-matched generic preamble. The *direction*
is robust across judges, judge families, framings, and a placebo control.

**Not yet defensible** (do not claim): that DueCare *detects trafficking accurately in the world*, that the
model became *more capable*, that the improvement is a *safety outcome* rather than a rubric score, or that
the headline magnitude (+40) is the real effect size. Those are proxy/construct claims and are labelled as
such throughout.

## 1. The harness lift — direction robust, magnitude proxy-inflated

On a 0-100 rubric, paired per prompt, judged by three cross-family Ollama models, the harness lifts
`gemma4:31b` by **~+40** (harness_core). That number is real *as a rubric score* but must carry three
caveats a reviewer will otherwise supply:

- **Construct overlap (near-circularity).** ~60 of the 100 rubric points reward exactly what the harness
  injects — naming the indicator (GREP), citing the specific law (RAG), giving the concrete resource (tools).
  The judge is partly graded against content the harness pasted into context.
- **LLM-judge proxy, not an outcome.** The judge-independent deterministic grader is **null** for the
  headline model over a placebo (harnessed - placebo ~= -0.05, p~=0.35). The entire +40 lives in the LLM
  judge; it is a *rubric-scored quality* proxy, not a measured safety outcome.
- **Magnitude is specificity-inflated.** Per-dimension re-grading shows the lift is ~+34 under
  specificity-anchored judge framings but only **~+12-14 under worker-utility and faithfulness lenses**. The
  honest headline is therefore the **diverse-lens ~+12-14**, with +40 presented only as the
  specificity-anchored rubric maximum.

**The load-bearing number to publish is ~+12-14, framed as "rubric-scored quality on tested prompts."**

## 2. Why the effect is not a pure artifact — the controls

The work earns the *direction* claim because it ran the controls a reviewer would demand:

- **Length-matched placebo.** A generic "be careful, be thorough" preamble of the same length lifts far
  less; the harness adds **~+3.3 beyond placebo** on an LLM judge — so it is the domain *knowledge*, not the
  mere presence of a preamble.
- **Incidental dimensions.** The harness also lifts ~21/21 dimensions it does *not* inject (empathy,
  plain-language, safety-first ordering), which a pure key-paste artifact would not.
- **Citation plausibility.** Harnessed citations are ~100% in-range and ~0.1% hallucinated — not gross
  citation theatre.
- **Cross-family judging + reliability.** Three vendor-distinct judges agree (high alpha), and the pooled
  multi-model run is clustering-corrected (ICC ~= 0.006).

Honest limits on these controls: the placebo run is small (n~=74, one judge, one model), and the 1,595-prompt
board is *not* itself cluster-corrected on a heavily templated prompt set — quote the effective-N-adjusted CI.

## 3. The overfitting evidence — real, with stated instability

- **Fabrication canary:** judges (especially a "faithfulness" framing) score a reply citing an *invented*
  statute far below a grounded one — genuine and useful. But it is n=5, single-judge, uses *cartoonish*
  fakes (not the realistic "real convention, wrong article" error), and its committed numbers were measured
  on grounded "gold" replies that a later legal audit found *overbroad* — so they are marked pending
  re-measurement. It proves gross-fabrication detection, **not** subtle-legal-error or legal-*correctness*
  detection.
- **Framing sensitivity:** the specificity-minus-diverse gap is sign-stable but point-*unstable* (n=5 gave
  +1.6, n=10 gave +6.5), single-judge, and one lens (deduction) was a mis-calibrated -21 outlier that was
  reworded after being seen to misbehave (a HARKing risk, flagged in our own register). Report the direction;
  exclude the deduction lens before quoting any ratio.

## 4. The residual gap — the most publishable-against weakness

Every control validates the **presence and plausibility** of injected specifics; **none validates legal
correctness or scenario relevance.** The project's own "gold" replies were found legally overbroad (C181/C29)
by the web-verified audit — the exact failure a specificity rubric rewards. This session closed part of that
gap by building a **vetted legal-claim library** (section 5) and correcting the overbroad claims, but the
end-to-end experiment — grading *actual* harness outputs for legal correctness, blinded to arm — is still
owed and is the claim that would most strengthen (or puncture) the "cites the specific law" lift.

## 5. The legal-claim layer — what was built to close the gap

A vetted `configs/duecare/legal_claims.json` (**57 EvidenceClaim records as of 2026-07-10** — the library grows
via a gated append-only enrichment loop, so treat every count here as as-of, not fixed; run
`python scripts/legal_claims.py` for the live count and weight split) as a verification+freshness overlay:
each claim carries a source URL, jurisdiction, **applicability + exceptions**, binding status, effective/
verified dates, volatility, and a recheck date. An adversarial web-audit verified the original core (no
fabricated citations), corrected the errors it found (a settled case wrongly shown as pending, a wrong reform
date, a misattributed statute, an over-absolute superlative, a mislabelled federal/state id). As of this
writing **29 claims are human-verified at verification_weight 0.9**; the other **28 are auto-vetted at 0.6**
(guardrails + a multi-prompt convergence vote), pending human verification to raise them — so the
machine-vetted-only fraction is currently ~49% and a reviewer should read it as provisional, not settled. A
deterministic `legal_reasoning.py` turns the library into auditable legal walkthroughs (facts -> indicators ->
applicable law *with exceptions* -> Palermo element analysis -> uncertainty -> **never a criminal finding**),
and a CoT training generator uses those walkthroughs as reasoning-chain targets, gated by a reasoning
contract — measured finding: the structural contract catches 7/8 "wrong-thinking" modes, the 8th
(overbroad-no-exception) needing the semantic faithfulness layer.

## 6. Robustness + red-team — screens with honest scope

- **Noise robustness** (the most rigorous artifact): GREP is word-level robust (`drop_stopwords`=1.0, a clean
  overfit test) but character-level brittle (typo/split/separator-injection); the obvious pre-GREP normalizer
  fix was tested and **honestly rejected** (net-negative — it mangles legitimate "C-181"/"18-hour" tokens).
  Scope: this is a GREP-layer *detection* screen, not end-to-end answer robustness.
- **Indirect prompt-injection** detector + probe set (the tool reads worker-pasted content).
- **Red-team response taxonomy**: 9 behavioural classes (`refusal_then_comply`, `comply_then_caveat`,
  `hedged_comply`, `partial_comply`, `refusal_then_hedge`, `safe_redirect`, ...) with **context-dependent
  severity weights**, feeding a weighted adversarial red-rate and a benign over-refusal severity, reported
  *separately*. Honest scope: it is an *unvalidated heuristic screen* — it has no precision/recall against a
  labelled set yet and is English-only; it is instrumentation to route replies to a judge, not itself a
  result.

## 7. Limitations register (what a reviewer should hold us to)

1. The headline is an LLM-judge, rubric-scored proxy — the deterministic floor is null over placebo for the
   headline model. Publish direction + diverse-lens magnitude, not +40.
2. No legal-*correctness* validation of actual harness outputs yet (only plausibility).
3. Overfitting quantifications are small-N, single-judge, point-unstable; one lens was post-hoc reworded.
4. The red-team classifier and the noise probes are layer/pattern screens, not end-to-end or validated evals.
5. The prompt set is heavily templated; use effective-N CIs.
6. Auto-vetted legal claims (4 remaining) are machine-vetted at 0.6, not human-verified.

## 8. Owed experiments (the publish-strengthening queue)

- Lift-under-noise on *generated* answers (baseline vs harnessed on noised prompts), not just GREP fire.
- Claim-level **legal-correctness** grading of real outputs, blinded to arm.
- The classifier's own precision/recall vs a labelled adversarial/benign sample; non-English markers.
- Larger-N, multi-judge, cluster-corrected re-grade of the diverse-lens headline.
- Re-measure the fabrication canary with subtle-error arms and the corrected grounded replies.

## Bottom line

The honest, defensible contribution is: **externalising domain detection, legal grounding, policy, and
auditing into a harness measurably improves the rubric-scored trafficking-safety quality of a small local
model's replies on tested prompts (~+12-14 on the diverse-lens metric), the effect survives a placebo and
cross-family judging, and the residual construct-validity and legal-correctness gaps are stated openly.**
That is a stronger and more publishable claim than "DueCare detects trafficking," and it is the one the
evidence supports.
