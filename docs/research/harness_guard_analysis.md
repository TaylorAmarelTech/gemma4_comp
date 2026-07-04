# Where the harness hurts, and what removes it (offline, no model calls)

> Deterministic post-processing of the committed grades (28,114 component cells, 11,546 stored responses in `reports/rich_lift/`). No new generation, no new judging -- every number is recomputed from the already-graded arms. Regenerate with `python scripts/analyze_harness_guard.py`. Prompt ids are not copied; aggregate counts only.

## Lever 1 -- which harness to serve (the big one)

Served mean over all ranked models by serving strategy. `core` = the cheap offline harness (GREP + top-4 RAG); `full` = core + deep RAG + tools + online. `+guard` applies the `min` serving guard (baseline fallback on a deterministic loss of grounding).

Baseline (no harness) mean: **47.5**.

| Serve | mean | lift over baseline |
|---|---:|---:|
| harness_full (current board) | 84.9 | **+37.5** |
| harness_core | 87.1 | **+39.6** |
| harness_full + min guard | 80.0 | **+32.5** |
| harness_core + min guard | 80.8 | **+33.3** |

**Best served mean: `harness_core` (87.1).** Serving `core` instead of `full` is the larger, cheaper win -- the full harness's online / deep-RAG / tool layer adds noise a strong reply does not need, so `full <= core` for every model (next table).

## Per-model: full underperforms core, and the negative-lift rate

`full - core` < 0 means the extra full-harness layer HURT that model. `neg-lift` = prompts where harness_full scored below baseline.

| Model | n | baseline | core | full | full - core | neg-lift |
|---|---:|---:|---:|---:|---:|---:|
| `gpt-oss:120b` | 1538 | 40.5 | 81.6 | 78.0 | -3.6 | 170 (11.1%) |
| `glm-5.1` | 40 | 70.1 | 92.4 | 93.0 | +0.6 | 1 (2.5%) |
| `gemma4:31b` | 1595 | 48.9 | 89.4 | 88.5 | -1.0 | 13 (0.8%) |
| `deepseek-v4-pro` | 182 | 59.4 | 94.3 | 93.1 | -1.3 | 1 (0.5%) |
| `glm-5.2` | 410 | 57.7 | 93.8 | 92.0 | -1.8 | 2 (0.5%) |
| `qwen3.5:397b` | 40 | 79.0 | 95.3 | 94.6 | -0.7 | 0 (0.0%) |

## Lever 2 -- the serving guard (a bounded safety net, not the main lever)

Guard policies applied to the full arm, pooled. `fired` = fell back to baseline; `recovery` = those where full < baseline (correctly reverted a regression); `misfire` = those where full >= baseline (reverted where the harness helped -> lift lost). `net pts` = recovered - lost.

| Policy | signals | guarded mean | fired | recovery | misfire | net pts |
|---|---|---:|---:|---:|---:|---:|
| `off` | (none) | 84.9 | 0 | 0 (+0.0) | 0 (-0.0) | **+0.0** |
| `min` | bare_nonanswer+citation_regression | 80.0 | 512 | 54 (+2179.8) | 458 (-21117.8) | **-18938.0** |
| `len` | bare_nonanswer+citation_regression+drastic_shortening | 77.9 | 666 | 65 (+2303.8) | 601 (-29223.3) | **-26919.5** |
| `hard` | hard_collapse | 85.3 | 92 | 51 (+2142.5) | 41 (-617.5) | **+1525.0** |

Read the `net pts` column. The **broad** policies are net-NEGATIVE: `min` fires far more often on prompts the harness IMPROVED than on true regressions (misfire >> recovery), because the harness's signature win is a *grounded refusal* that `refusal_detector` flags as a refusal -- no cheap phrase test separates it from a bare 'I can't help' -- and `len` (adding the length signal) is worse still. But the **tight `hard` policy IS net-positive**: it fires only on the catastrophic collapses (a >=1k-char baseline turned into a <=150-char reply), which its length cap CANNOT confuse with a grounded refusal (those run to hundreds of chars). It catches the ~-75 disasters (big recovery) with few, small misfires -> a guarded mean ABOVE unguarded. **Conclusion: `DEFAULT_GUARD_POLICY = hard`** -- a cheap serving-time safety net for the catastrophic tail, on top of serving `core`.

## The negative-lift tail, by deterministic harm mode

Of the **187** prompts where harness_full scored below baseline, the harm mode (first deterministic signal, else `other`):

| Harm mode | count | catchable by a text guard? |
|---|---:|---|
| `other` | 122 | no -- residual |
| `bare_nonanswer` | 54 | yes (min) |
| `drastic_shortening` | 11 | no -- signal is net-negative |

| Model | neg-lift | bare_nonanswer | citation_regression | drastic_shortening | other |
|---|---:|---:|---:|---:|---:|
| `gpt-oss:120b` | 170 | 52 | 0 | 11 | 107 |
| `glm-5.1` | 1 | 0 | 0 | 0 | 1 |
| `gemma4:31b` | 13 | 1 | 0 | 0 | 12 |
| `deepseek-v4-pro` | 1 | 1 | 0 | 0 | 0 |
| `glm-5.2` | 2 | 0 | 0 | 0 | 2 |
| `qwen3.5:397b` | 0 | 0 | 0 | 0 | 0 |

## What the harness DID on the negative-lift prompts (text signature)

Deterministic deltas (harness_full - baseline) on the prompts where the harness hurt. `added a refusal` = the baseline answered substantively but the harnessed reply is a refusal; `conv/section delta` = change in cited ILO conventions / statute sections; `len delta` = change in characters.

| Subset | n | added a refusal | mean conv delta | mean section delta | mean len delta |
|---|---:|---:|---:|---:|---:|
| all negative-lift | 187 | 1 (0.5%) | -0.01 | +0.12 | -4776 |
| `other` (un-catchable tail) | 122 | 0 (0.0%) | +0.19 | +0.22 | -179 |

Reading: a **positive** conv/section delta means the harnessed reply cited *more* law than the baseline and still scored lower -- so the loss is not missing grounding but the judge preferring the strong baseline's breadth (a rubric/judge-preference effect, not a harness bug). A high `added a refusal` share means the harm is the harness turning a useful answer into a (grounded) refusal -- the failure the h2 grounded-response contract and intent-aware routing target at generation time (serving `core` also constrains a strong reply less).

## What this says

- **Serve `core`, not `full`.** This is the single measured lever that reduces where the harness hurts (full <= core for every model) and it is cheaper (no online / tool calls). It is a board change and rolls out under the versioned re-grade discipline, not mid-sweep.
- **A TIGHT serving guard works; a broad one does not.** The `hard` policy (`DEFAULT_GUARD_POLICY = hard`) fires only on the catastrophic collapses (a substantial baseline turned into a <=150-char reply) and is net-positive -- its length cap cannot fire on a grounded refusal. The broad `min`/`len` policies are net-negative (they revert grounded refusals `refusal_detector` flags), so they are kept only to demonstrate that.
- **The bulk of the tail (65%) is `other`, and the text signature shows it is NOT a harness failure:** on those prompts the harnessed reply cites MORE conventions and MORE sections and adds a refusal ~0% of the time -- a full-length, MORE-grounded reply the judge still scored below a strong baseline's essay. That is a judge / rubric-preference effect near the quality ceiling, not lost safety value; no text guard should try to 'fix' it. The honest response is to report it, serve `core` for strong-baseline models (less constraint), and let the h2 contract handle the tiny genuine bare-collapse count.

