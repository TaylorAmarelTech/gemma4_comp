# Kaggle Community Benchmark Notes

Purpose: explain how DueCare's optional Kaggle-native benchmark differs from
the external endpoint benchmark and how to publish it safely.

## Two Benchmark Surfaces

| Surface | Use | Model Calls |
|---|---|---|
| `kaggle/03-universal-llm-benchmark` | Compare arbitrary API endpoints and external services. | Direct HTTP calls using the configured endpoint/key. |
| `kaggle/04-kaggle-community-benchmark` | Publish a Kaggle Community Benchmark and use Kaggle-hosted model quota. | `kaggle_benchmarks` via `kbench.llm` / `kbench.llms[...]`. |

Use `04` when the goal is a Kaggle leaderboard. Use `03` when the goal is a
private or provider-specific endpoint comparison.

## First Publishable Run

Use conservative settings:

```text
DUECARE_KBENCH_DOMAIN=trafficking
DUECARE_KBENCH_LIMIT=12
DUECARE_KBENCH_USE_JUDGE=0
```

After the first run succeeds, enable a judge only if the selected judge model is
available in Kaggle's Benchmark environment:

```text
DUECARE_KBENCH_USE_JUDGE=1
DUECARE_KBENCH_JUDGE_MODEL=anthropic/claude-opus-4
```

The judge path uses `kbench.assertions.assess_response_with_judge`, so the
criteria are visible in the benchmark transcript.

## Artifacts To Keep

- Kaggle benchmark URL.
- `/kaggle/working/duecare-kbench/<run_id>/results.json`.
- `/kaggle/working/duecare-kbench/<run_id>/summary.md`.
- Screenshot of the Kaggle task page after at least one model run.

Do not publish a README link until the benchmark task is public and the first
run has been reviewed for hidden fallback behavior.
