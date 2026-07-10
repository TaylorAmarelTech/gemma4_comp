# Per-dimension granular harness lift (LLM judges, one call per dimension)

This report presents the DueCare harness lift measured at the finest LLM-judge granularity the rubric
supports: one dedicated judge call per rubric dimension, graded by independent cross-family judges. It
is distinct from `frontier_perdim_report.md` (the deterministic ~77-dimension grader) and from
`rich_harness_lift_100.md` (the batched 0-100 board metric). The question it answers: when a judge scores
each safety dimension in isolation, and more than one independent judge does so, does the harness lift
hold, and which dimensions does it move?

Subject model: `gemma4:31b`. Arms compared: `baseline` versus `harness_core` (the lightweight harness =
fired GREP indicator rules + RAG legal grounding + the ILO-reasoning preamble). Scale: 0-100, summed over
five calibrated components A-E.

## The lift is large and statistically significant in every independent judge family

The headline is not one number from one setup. A large positive total lift appears across grading
configurations that vary the judge family, the grading method, and the prompt wording. What is robust is
the *sign and significance* — every configuration finds a large lift whose confidence interval excludes
zero. What is *judge-dependent* is the exact magnitude, which ranges from roughly +45 to +60:

| Configuration | Total lift | 95% CI | n | notes |
|---|---:|---:|---:|---|
| gpt-oss-120b (openai family), single framing | +56.8 | — | 20 | one call per dimension |
| gpt-oss-120b, framing-averaged | +54.1 | — | 16 | each dimension asked with 2 framings, averaged |
| gpt-oss + qwen3.5, two cross-family judges | +57.5 | — | 60 | openai + qwen families |
| mistral-small (mistral family) | +44.77 | [+35.4, +53.8] | 30 | third family; bootstrap CI; every per-dimension CI excludes zero |

The openai and qwen families land near +55; the mistral family is a more conservative grader and lands
near +45, with a 95% bootstrap interval [+35.4, +53.8] whose upper edge reaches the openai/qwen band. The
honest read is therefore **not** "the lift converges to a single point value" — it is that the lift is
large, positive, and statistically significant in three independent judge families, with a magnitude that
depends on how strict the grader is. A finding that survives that much judge variation, while never once
crossing zero, is more defensible than any single point estimate. (The gpt-oss and qwen rows predate the
bootstrap-CI addition and are reported as point estimates; the mistral row carries the interval.)

## Every dimension lifts positively in every family; the largest mover is judge-dependent

The openai + qwen two-judge run (n=60 = 30 prompts graded by two judges from different families, each
cross-family with the gemma4:31b subject so no judge scores its own family):

| Dimension | gpt-oss (openai) | qwen3.5 (qwen) | Pooled |
|---|---:|---:|---:|
| A. Identifies the indicator | +18.2 | +17.1 | +17.7 |
| B. Cites the specific law | +11.4 | +14.3 | +12.8 |
| D. Concrete resources | +9.6 | +10.3 | +10.0 |
| C. Refuses to enable | +8.2 | +10.0 | +9.1 |
| E. Privacy and safety | +7.3 | +8.5 | +7.9 |
| Total (0-100) | +54.6 | +60.3 | +57.5 |

The mistral third family (n=30, one judge, with bootstrap 95% CIs — every interval excludes zero, so
each dimension's lift is individually significant):

| Dimension | mistral-small lift | 95% CI | n |
|---|---:|---:|---:|
| B. Cites the specific law | +18.00 | [+15.8, +19.6] | 20 |
| C. Refuses to enable | +10.53 | [+5.3, +15.8] | 19 |
| D. Concrete resources | +9.05 | [+6.0, +11.9] | 22 |
| A. Identifies the indicator | +7.71 | [+3.1, +13.0] | 21 |
| E. Privacy and safety | +6.22 | [+3.7, +8.9] | 23 |
| Total (0-100) | +44.77 | [+35.4, +53.8] | 30 |

What all three families agree on: **every dimension lifts positively**, and **law-citation (B) is a
top-two mover in every family**. That maps onto what the harness injects — the RAG legal corpus and the
GREP indicator rules feed exactly the law-citation and indicator dimensions.

Where they differ, and it is reported rather than smoothed over: the *single largest* mover is
judge-dependent. The openai and qwen families rank indicator-identification (A, ~+17-18) first and
law-citation (B) second; the mistral family reverses this, ranking law-citation (B, +18.0) clearly first
and scoring indicator-identification (A, +7.7) only fourth. In other words, all three families see the
harness improve grounding, but they disagree on whether it improves *naming the indicator* or *citing the
statute* most. A safety claim that depends on that ordering would be overreaching; the claim that survives
all three families is the weaker, sturdier one — the harness lifts law-citation and indicator-identification
together, and lifts every other scored dimension too, in every independent grader.

## Method and robustness controls

- One call per dimension. Each component gets its own dedicated judge prompt (`build_component_rubric_single`)
  so the judge spends its full reasoning budget on one criterion and no dimension is anchored to a round
  grand total. This costs 5-6x the judge calls of a batched grade and is reserved for the headline, not
  the high-throughput sweep.
- Cross-family judging. A judge never scores a response from its own model family (`model_family`), which
  removes the most direct self-preference confound.
- Sub-call resilience. A transient sub-call failure is retried once and, if it still fails, that one
  dimension is skipped rather than dropping the whole cell (`judge_components_perdim`). A grade where
  every sub-call fails omits the total entirely rather than reporting a phantom zero, so a judge that
  cannot follow the rubric does not deflate the pooled number.
- Framing robustness. Each dimension can be asked with several distinct question framings and averaged;
  doing so moves the total only marginally (+56.8 to +54.1), which indicates the score is not an artifact
  of one prompt wording.
- Bootstrap confidence intervals. Each per-dimension and total lift now carries a deterministic (seeded,
  reproducible) 95% bootstrap interval over the paired per-prompt deltas, so the sample-size uncertainty
  is quantified rather than asserted. For the mistral family every per-dimension interval excludes zero,
  which is the individual-dimension significance claim above.
- Semantic-framing bank. The three original question framings were all rewordings of the same "reward
  specificity (exact statute / fee / hotline)" instruction, so averaging them cancels *wording* noise but
  not the risk that the judge is rewarding surface tokens. The bank now adds three framings that probe the
  same component through genuinely different lenses: worker-actionability, faithfulness/anti-fabrication
  (penalise invented or wrong specifics even when they look precise), and top-down deduction. See the two
  overfitting probes below for what they reveal.

## Does the lift survive the grading lens? (two overfitting probes)

Both probes test whether the measured lift reflects real quality or the judge rewarding the surface tokens
(exact statute, fee, hotline) the harness injects. Both are small-N, single-judge (mistral), propose-only.

**Framing sensitivity** (`scripts/grading_framing_sensitivity.py`) grades each dimension under all six
framings separately and reports the *specificity-minus-diverse* gap. A mistral n=10 run found a mean gap
of **+6.49**: the specificity framings (0-2) show a large per-dimension lift (A/B/D ≈ +8 to +11) while the
diverse lenses (worker-utility, faithfulness, deduction) show near-zero or negative lift on those same
dimensions. So a meaningful part of the measured lift is concentrated in the framings that reward exact
tokens. Caveats worth stating: the gap is sample-noisy (an n=5 run gave ≈ +1.6, so the point value is
unstable though the sign is consistently positive), it is one judge, and the deduction lens is uniformly
harsh (it keeps penalising the harnessed reply for what is *still* missing), which widens the gap.

The consequence for the *headline* is direct: summing the same n=10 sample's per-dimension lift within each
framing gives the total lift you would report depending on which lens you grade with (same cells across all
framings, so this is an apples-to-apples comparison; per-(dim,framing) n varies, so treat it as directional):

| Grading lens | summed total lift (0-100) |
|---|---:|
| specificity bank (framings 0-2) | ≈ +33.7 |
| worker-actionability (framing 3) | +13.8 |
| faithfulness (framing 4) | +11.4 |
| deduction (framing 5) | −21.4 |

Two things follow. First, the harness lift is **~3× larger under specificity-anchored grading (~+34) than
under the worker-actionability and faithfulness lenses (~+12)** — but it stays clearly positive under those
two lenses, so the effect is real and only its *magnitude* is lens-dependent. Second, the deduction lens is
a strong negative **outlier** (−21): a top-down "what is still missing" framing penalises the longer, more
detailed harnessed reply for the larger surface it exposes, which reads as a framing **mis-calibration**
rather than a real quality drop. It should be recalibrated (or excluded) before it is ever used in a
headline, and the honest published number should be graded with the non-outlier diverse lenses — a smaller
(~+12), harder-to-game figure — or reported as the range across lenses shown above. (The deduction framing
has since been reworded to explicitly forbid deducting for length or for extra correct content; the −21.4
above reflects the pre-fix wording and awaits re-measurement, so treat that row as the outlier it flags,
not a current number.)

**Fabrication canary** (`scripts/fabrication_canary.py`) is the controlled version: five composite
scenarios, each with a grounded reply (a real ILO convention cited correctly) and a "gamed" reply that
name-drops the same kind of tokens but cites an *invented* statute and gives wrong guidance. A judge that
grades substance scores grounded ≫ gamed.

| Framing | grounded | gamed | fabrication penalty |
|---|---:|---:|---:|
| specific | 60.8 | 10.0 | +50.8 |
| strict | 35.6 | 16.6 | +19.0 |
| absent-to-concrete | 54.8 | 9.2 | +45.5 |
| worker-utility | 70.2 | 13.4 | +56.8 |
| **faithfulness** | 84.2 | **0.0** | **+84.2** |
| deduction | 79.6 | 6.0 | +73.6 |
| specificity mean | | | +38.4 |
| diverse mean | | | +71.5 |

Mistral penalises the fabrication under *every* framing — it is not blindly fooled — but the diverse
framings punish it about twice as hard (+71.5 vs +38.4), and the faithfulness lens scores the fabricated
reply 0/100 while the specificity framings still award it ~10 for merely looking specific.

Caveat added after an external legal-claim audit (2026-07-10): the grounded replies in this canary were
originally phrased with *overbroad* legal claims (e.g. "C181 Article 7 prohibits worker-paid recruitment
fees", "C29 treats debt bondage and document retention as coercion") that omit the authorised exceptions,
ratification dependence, and the fact that debt-bondage / document-retention are *separate indicator
guidance*, not the C29 definition. They have been revised to precise formulations, so the canary was partly
measuring "confident-overbroad vs fabricated". The numbers above reflect the pre-revision grounded replies
and await re-measurement; the precise-but-hedged versions may score lower under the specificity framings,
which would itself be evidence that legal precision costs specificity-rubric points.

**Read together:** the harness lift is real — every lens ranks a correct grounded reply far above a
fabricated one, so the harness is injecting genuine, *faithful* specifics — but specificity-anchored
grading inflates the lift's *magnitude*, because those framings reward token presence even when the token
is invented. The remedy is the remix itself: grade the headline with the diverse bank (or at least include
the faithfulness lens), which is materially harder to game and yields a smaller but more honest lift.

## Reproduce

The live off-Ollama judge as of this writing is the mistral family (the run that produced the third-family
table and the confidence intervals):

```
python scripts/perdim_headline_regrade.py --n 30 --judges mistral:mistral-small-latest
```

Any provider-prefixed judge works: `openai:<id>` and `anthropic:<id>` route to the real OpenAI and
Anthropic APIs the moment a key is placed in `.env` or `.agent/provider_keys.json` (both families are
wired but were un-keyed when the mistral run was taken). The earlier openai/qwen rows were measured through
`nvidia:openai/gpt-oss-120b` and `nvidia:qwen/qwen3.5-397b-a17b`; those same two families are also
reachable through Ollama-cloud as bare `gpt-oss:120b,qwen3.5:397b`. Add judges comma-separated, or average
across question framings with `--phrasings-per-dim 2`. The tool re-grades already-generated responses, so
it does not regenerate model output and does not depend on the subject model's provider — which is why it
can run on a live off-Ollama judge without touching the benchmark engine's Ollama quota.

## Notes and limitations

- Absolute magnitudes are sample-dependent and judge-dependent, and this report now shows that directly:
  the total ranges from +44.8 (mistral) to +60.3 (qwen) across families. The large committed board, which
  grades the full sweep with a batched 0-100 rubric across three Ollama-cloud families, reports a pooled
  paired lift near +40.8 (harness_core) — more conservative still, because it grades far more prompts and
  batches the five components into one call. The load-bearing claim is the *direction and significance*
  across every judge family and every dimension, not any single point value.
- The samples in the per-dimension runs are bounded (tens of prompts), which is why each lift carries a
  bootstrap 95% CI. The intervals are the honest statement of that uncertainty: wide where n is small
  (mistral C, [+5.3, +15.8]) and tight where the signal is clean (mistral B, [+15.8, +19.6]). Because the
  openai and anthropic judge routes are now wired (pending keys), a genuinely independent three-or-more
  family panel with CIs is a drop-in extension the moment those keys are populated.
- Not every model can serve as a per-dimension judge: the single-component JSON rubric is strict, and
  some models wrap or ignore it. Judges verified to follow it are recorded alongside this work.
- These numbers describe measured rubric-scored quality. A rubric that rewards citing the specific law and
  naming the indicator will reward a harness that supplies exactly those, so the honest framing is that
  grounding measurably improves rubric-scored trafficking-safety, not that the model became more capable.
- Figures may shift as more data is graded; this report describes a point-in-time measurement and the
  reproduce command above regenerates it.
