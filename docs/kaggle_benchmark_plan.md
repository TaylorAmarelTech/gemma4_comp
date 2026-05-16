# Kaggle benchmark publication plan

Publishing a Kaggle benchmark is a good fit for DueCare because it turns the project from a one-off demo into a reusable model-evaluation surface. It is lower-friction than creating a full Kaggle competition, but still lets researchers rank models and inspect details.

## Recommended shape

Use a **Kaggle Dataset + benchmark notebook + scoring wheel** first.

| Artifact | Purpose | Source in this repo |
|---|---|---|
| Versioned benchmark dataset | Prompt rows, expected signals, rubrics, metadata | `packages/duecare-llm-benchmark/` plus curated `configs/duecare/domains/` samples |
| Scoring wheel | Shared scoring functions so all notebooks rank models the same way | `duecare-llm-benchmark` |
| Benchmark runner notebook | Loads dataset, runs a selected model/backend, emits scored JSON/CSV | New Kaggle benchmark notebook or appendix derived from A-11 grading evaluation |
| Results dataset | Captures model submissions and reproducible scores | Kaggle Dataset, manually published/versioned |
| Model cards/results table | Human-readable ranking with caveats | docs + Kaggle Dataset README |

This creates a benchmark people can rerun on Kaggle without needing a formal leaderboard product.

## What to capture per model

Each run should emit a machine-readable row with:

- `model_id`, provider, revision/hash, quantization, adapter/backend.
- prompt template and safety harness settings.
- hardware/runtime environment.
- generation parameters: temperature, max tokens, seed when available.
- per-prompt verdict, score, refusal flag, harmful-phrase flag, citation/grounding indicators.
- aggregate metrics: harmful phrase rate, refusal quality, legal grounding, worker-helpfulness, exact/within-one rubric match, cost/latency.
- provenance tuple: `git_sha`, `dataset_version`, `scorer_version`, `run_timestamp`.
- optional submission attribution from [submission_labeling_policy.md](submission_labeling_policy.md): anonymous, pseudonymous lab/deployment, verified organization, public maintainer, region, and visibility policy.

## Ranking design

Avoid one oversimplified score. Publish a leaderboard-style table with separate columns:

1. **Safety compliance** — refuses or redirects exploitative requests.
2. **Worker usefulness** — gives concrete, non-victim-blaming next steps.
3. **Grounding/citations** — cites relevant public law/NGO knowledge when available.
4. **Privacy posture** — can run locally or documents external calls clearly.
5. **Operational cost/latency** — useful for NGO deployments.

A composite score can be shown, but the component scores should remain visible.

## Dataset tiers

| Tier | Rows | Use |
|---|---:|---|
| Smoke | 25 | Fast CI/Kaggle CPU check. Already aligned with `duecare-llm-benchmark`. |
| Public submission | 200-500 | Judge/reviewer benchmark with transparent categories. |
| Extended research | 1K-5K | Model comparison and ablation work. |
| Full corpus | 74,567 | Research asset; not the default benchmark because it is too large for casual reruns. |

## Manual Kaggle publishing flow

Do not auto-publish during cleanup. Prepare copy/paste-ready artifacts and let Taylor publish via Kaggle UI/CLI manually:

1. Build or export benchmark dataset files locally.
2. Run PII/secrets checks.
3. Create/update the Kaggle Dataset metadata.
4. Upload dataset manually.
5. Publish the benchmark notebook manually.
6. Add result artifacts as a new dataset version.
7. Link the benchmark from judge docs only after the public URL exists.

## Why not a full Kaggle competition first?

A formal Kaggle competition/leaderboard is more work: hosting rules, submission format, evaluation server, moderation policy, and competition approval. The dataset + notebook path is enough for the hackathon and can later become a competition if there is community demand.