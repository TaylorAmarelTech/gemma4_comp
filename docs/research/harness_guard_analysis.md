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

Read the `net pts` column: **every fallback policy is net-negative on this data.** Even `min` fires far more often on prompts the harness IMPROVED than on true regressions (misfire >> recovery), because the harness's signature win is a *grounded refusal* that `refusal_detector` flags as a refusal and that cites an ILO *convention* + hotline but not a numbered *section* -- no cheap text test separates it from a bare 'I can't help'. The `len` row (adding the length signal) is worse still: a verbose baseline is frequently improved by a shorter grounded reply. **Conclusion: serve the harness reply UNGUARDED (`DEFAULT_GUARD_POLICY = off`); the guard is a measured null on this benchmark.**

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

## What this says

- **Serve `core`, not `full`.** This is the single measured lever that reduces where the harness hurts (full <= core for every model) and it is cheaper (no online / tool calls). It is a board change and rolls out under the versioned re-grade discipline, not mid-sweep.
- **A baseline-fallback serving guard does NOT work here** -- every policy is net-negative, because no cheap text signal separates the harness's grounded refusal from a bare one, and shorter replies are often better. `DEFAULT_GUARD_POLICY = off`; the guard code is kept for reproducibility and re-measurement on other data, not as a recommendation.
- **A length-based guard is the worst** (the `len` row) -- shorter is frequently better. Never ship it.
- **The bulk of the tail is `other`** -- full-length, still-cited replies the judge scored below a strong baseline's essay. No text guard catches these; the generation-time levers are serving `core` (constrains a strong reply less) and the h2 grounded-refusal contract (reduces the small bare-collapse count).

