# DueCare Benchmark v5 — Run Instructions

## What this is

`task_notebook.ipynb` is the v5 redesign of the DueCare Kaggle Community
Benchmark task. It replaces v4's all-judge-call model with a **Tier 1
(deterministic) + Tier 2 (judge)** split and supports an optional
**two-arm structure** (raw vs DueCare-context-prefixed) for measuring
the empirical lift of the harness.

Source builder: `scripts/build_full_rubric_task_notebook_v5.py`.

## What v5 fixes (vs v4)

| Issue (v4) | v5 fix |
|---|---|
| 27 × 74 = 1,998 judge calls per arm = $9.14 of $10 daily quota | Tier 1 deterministic for 18 of 74 dims = **1,512 calls per arm = $7.56** |
| Per-dim 100% pass rate even when row failed (parser artifact) | Real verdicts captured from `assessment.results[0].passed` (Tier 2) and Tier 1 return value, with one assertion per dim carrying that verdict |
| `gemini-3-flash-preview` ran silently when writeup said "Gemini 3.5" | Notebook prints + warns if bound `kbench.llm` doesn't contain the configured `EXPECTED_CANDIDATE_MODEL_HINT` |
| Single-arm only — couldn't measure harness lift | `ARMS = ('raw',)` (default, 1-day fit) or `('raw','harnessed')` (2-day, measures delta) |

## Cost projection at a glance

| ARMS | Calls / day | Cost / day | Days to finish |
|---|---|---|---|
| `('raw',)` | 1,512 | ~$7.56 | 1 |
| `('raw','harnessed')` | 3,024 | ~$15.12 | 2 |

(at ~$0.005 per Gemini 3.5 Flash judge call; subject to Kaggle pricing changes)

## How to run

### Single-arm (raw) — 1 day

1. Open `task_notebook.ipynb` in Kaggle (publish via `kaggle kernels push`
   from this folder, or upload manually).
2. In the Kaggle Benchmarks UI **candidate model picker**, select
   `google/gemini-3.5-flash` (or another supported model — the
   notebook will print a WARN if the bound model doesn't contain
   the configured hint, but it does NOT abort).
3. Click **Run All**.
4. Expected wall-clock: ~10–20 minutes for 27 rows × 56 judge dims
   at `n_jobs=4`.
5. After the run completes, click **Save Task** to publish.

### Two-arm (raw + harnessed) — 2 days

The cleanest path is two single-arm runs, combined locally:

1. Day 1: leave `ARMS = ('raw',)` and run the raw arm only.
2. Day 2: change `ARMS = ('harnessed',)` and run the harnessed arm
   only.
3. Combine the per-dim verdicts from both runs locally by reading
   the two `v5_per_dim_results.json` artifacts and computing the
   delta off-Kaggle.

Running `ARMS = ('raw', 'harnessed')` in a single notebook will
exhaust the daily quota mid-run; you can resume the next day but
kbench caching of partial results is fragile.

## What gets published

The leaderboard publishes one entry per (task, candidate-model) pair.
Per-dim verdicts are surfaced via the assertion-expectation stream
(real verdicts, unlike v4). The summary cell also writes a
`v5_per_dim_results.json` artifact to `/kaggle/working/` containing:

- `row_arm_dim_verdict`: full per-row × per-arm × per-dim verdict map
- `per_dim_summary`: per-dim aggregate (pass count, total, percentage;
  delta when both arms present)
- `candidate_model_describe`: which model actually ran
- `task_name`, `duecare_commit_sha`, `rubric_version`

## Notes / gotchas

- **The candidate-model WARN is not an abort.** v5 prints a loud
  warning if the bound model doesn't match the configured hint but
  still runs the benchmark. Edit `EXPECTED_CANDIDATE_MODEL_HINT` in
  the builder to change the expectation.
- **Tier 1 checks are conservative.** They only return a verdict
  when the deterministic signal is unambiguous. Anything ambiguous
  falls through to Tier 2 judge grading. False-positive PASS rate
  on Tier 1 is the main risk; review individual dim regexes in
  `scripts/build_full_rubric_task_notebook_v5.py:TIER1_CHECKS` if
  you suspect a check is too permissive.
- **Hard-veto dims always go through the judge** regardless of any
  Tier 1 signal. There is no regex that reliably detects
  "implementation steps for wage garnishment refused"; that needs
  a judge.
- **v4 stays valid as historical evidence.** Don't delete
  `kaggle/04-task-notebook-fresh/` — it's the published artifact of
  the cost / parser issues that motivated v5.

## File layout

```
kaggle/04-task-notebook-v5/
├── task_notebook.ipynb          # 22-cell generated notebook
├── RUN_INSTRUCTIONS.md          # this file
└── kernel-metadata.json         # to be added when publishing
```

Regenerate the notebook after editing the builder:

```bash
python scripts/build_full_rubric_task_notebook_v5.py
```

This bumps the task name's `_<sha>` suffix to the current HEAD,
forcing kbench cache miss.
