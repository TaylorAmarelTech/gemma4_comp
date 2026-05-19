# DueCare Kaggle Community Benchmark

<!-- duecare:lane-label -->
> **Serves lanes:** Researcher; Developer / integration partner.

Purpose: publish DueCare as a Kaggle-native Community Benchmark that can run
through Kaggle's `kaggle_benchmarks` model proxy and use Kaggle-hosted model
quota/credits when available.

This is an optional benchmark-publishing surface. It complements, but does not
replace, the primary submission path:

1. `01-duecare-exploration-workbench`
2. `02-live-demo`
3. `A-00-omni-experiment-workbench`

It also complements `03-universal-llm-benchmark`, which is the BYO-endpoint
runner for OpenAI-compatible, Anthropic Messages, and raw HTTP targets. Use this
`04` kernel when the goal is a Kaggle Community Benchmark leaderboard.

## What It Does

- Defines DueCare safety rows as `@kbench.task` benchmark tasks.
- Uses `kbench.llm` or `kbench.llms[model_name]` instead of direct API calls.
- Loads prompt rows from `configs/duecare/domains/<domain>/seed_prompts.jsonl`
  when the repository is attached as a Kaggle dataset.
- Falls back to a compact built-in trafficking benchmark if the repo is not
  attached.
- Scores refusal correctness, harmful operational uplift, legal grounding,
  forced-labor indicators, privacy minimization, and evidence preservation.
- Optionally asks a Kaggle-hosted judge model to grade the response, then falls
  back to deterministic scoring if the judge is unavailable.
- Writes a replayable DueCare JSON report to
  `/kaggle/working/duecare-kbench/`.

## Kaggle Credits

This kernel is the path that can use Kaggle's AI model quota because it calls
models through `kaggle_benchmarks` (`kbench.llm` / `kbench.llms[...]`). The
`03-universal-llm-benchmark` kernel uses external HTTP endpoints and therefore
uses the configured endpoint's own billing or key.

## Environment Knobs

| Variable | Default | Purpose |
|---|---|---|
| `DUECARE_KBENCH_DOMAIN` | `trafficking` | Domain pack to load from `configs/duecare/domains/`. |
| `DUECARE_KBENCH_LIMIT` | `12` | Number of prompt rows to evaluate. |
| `DUECARE_KBENCH_MODEL` | empty | Optional Kaggle model name; empty uses `kbench.llm`. |
| `DUECARE_KBENCH_USE_JUDGE` | `0` | Set to `1` to ask a Kaggle-hosted judge model. |
| `DUECARE_KBENCH_JUDGE_MODEL` | `anthropic/claude-opus-4` | Preferred judge model name when available. |
| `DUECARE_REPO_ROOT` | empty | Explicit path to an attached DueCare repo dataset. |

## Run

Create a Kaggle Benchmark task notebook from
`https://www.kaggle.com/benchmarks/tasks/new`, attach this repository or paste
`kernel.py`, then run. The aggregate task is
`duecare_migrant_worker_safety_benchmark`; the row-level task is marked
`store_task=False` so the aggregate task is the publishable benchmark output.

## Publishing Checklist

1. Open Kaggle Community Benchmarks and create a new task notebook.
2. Paste this `kernel.py` or attach the repo dataset and import the file.
3. Add the DueCare repo as an input dataset if you want the full prompt corpus;
   otherwise the built-in fallback rows run.
4. Set `DUECARE_KBENCH_LIMIT=12` for a first smoke run; raise it only after the
   benchmark task succeeds.
5. Leave `DUECARE_KBENCH_MODEL` empty for Kaggle's default model proxy, or set
   it to the exact Kaggle model name shown in the Benchmark UI.
6. Keep `DUECARE_KBENCH_USE_JUDGE=0` for the first publishable run. Enable it
   only after confirming the preferred judge model is available in Kaggle.
7. Run the task. Confirm the output reports:
   - `uses_kaggle_benchmarks: true`
   - rows loaded from the intended domain
   - no operational-uplift assertion failures hidden by fallback logic
8. Download `/kaggle/working/duecare-kbench/<run_id>/results.json` and
   `summary.md` as the first reproducibility artifact.
9. Use Kaggle's "Evaluate More Models" control to populate the benchmark
   leaderboard.
10. Link the public benchmark URL from `README.md` only after the task page is
    public and at least one run artifact has been reviewed.
