# DueCare v4 Benchmark â€” Run Instructions

Live notebook: <https://www.kaggle.com/code/taylorsamarel/new-benchmark-task-0a35d>

## Pre-flight checklist

1. **Confirm the model picker is set to Gemini 3.5.**
   The Kaggle Benchmarks UI has a model selector at the top of the
   notebook. `kbench.llm` resolves to whatever is selected when you
   click Run All. If it shows `gemini-3-flash-preview` (or any other
   model), change it.

2. **Run menu â†’ Factory Reset.**
   Kaggle Benchmarks caches results keyed on (task name, evaluation
   data hash). The build script now suffixes the task name with the
   current GitHub HEAD short SHA so a code-change push always misses
   the cache â€” but the in-memory cache from an earlier Run All in the
   same session can still return stale results. Factory Reset wipes
   it.

3. **Click Run All** (top toolbar or `Ctrl+F9`).

## Expected output

The notebook prints diagnostic markers as it runs. Look for these in
order:

1. `duecare loaded: 74 dimensions; rubric version v3.16-...` â€”
   confirms the rubric JSON fetch from GitHub succeeded.
2. `cluster sizes: legal_grounding_precision=20, ...` â€” confirms
   the 74 dims map to the 6 reporting clusters.
3. `[v4 evaluate] candidate kbench.llm -> model_id='google/gemini-3-5'` â€”
   confirms the candidate model bound correctly. If this prints
   anything other than `gemini-3-5`, stop the run and re-check the
   model picker.
4. `[v4 evaluate] judge kbench.judge_llm -> ...` â€” confirms the judge
   model.
5. `[Parallel(n_jobs=4)]: Done 27 out of 27 | elapsed: 5-15 min` â€”
   the actual eval sweep (1,998 judge calls). If this finishes in
   under a minute, results are cached â€” Factory Reset and retry.
6. `[v4 evaluate] captured N run records` â€” should be 27. If 0, the
   stale-cache guard in the summary cell will raise `SystemExit` with
   a recovery message.
7. **Per-row + per-cluster + per-dim summary** scorecards.
8. `wrote per-dim artifact: /kaggle/working/v4_per_dim_results.json` â€”
   the publishable scorecard JSON. Download it from the Output tab of
   the Kaggle notebook.
9. `%choose duecare_migrant_worker_safety_benchmark_<SHA>` registers
   the task with Kaggle Benchmarks. Click **Save Task** in the UI to
   commit it to the leaderboard.

## If something goes wrong

| Symptom | Probable cause | Fix |
|---|---|---|
| `Cannot find command 'git'` | Old pip install cell using `pip install git+...` | Fixed â€” the notebook now fetches the two JSON files via `urllib.request.urlopen`. |
| `TypeError: 'OpenAI' object is not callable` | `kbench.llm('google/gemini-3-5')` â€” treating the handle as a factory | Fixed â€” uses `llm=[kbench.llm]` and tells the user to pick the model in the UI picker. |
| `KeyError: "None of ['run_id'] are in the columns"` | `results.as_dataframe()` crashes when any assertion failed (normal here) | Fixed â€” wrapped in try/except so the summary cell runs anyway. |
| Eval finishes in 11s with 0 runs | Stale kbench cache returning empty Runs | Stale-cache guard raises `SystemExit` with recovery message. Factory Reset + Run All. |
| Summary table is empty / 0 rows visible | Iterator exhausted by an earlier `len(list(results))` | Fixed â€” `RUN_RECORDS = list(getattr(results, "runs", results))` materializes once. |

## Re-running with a different model

Restart the kernel (Run â†’ Restart Kernel), change the model in the
Kaggle Benchmarks picker, click Run All. Each successful run adds
that model to the leaderboard for the task name.

## Regenerating the notebook from source

```bash
python scripts/build_full_rubric_task_notebook.py
python scripts/validate_v4_benchmark_notebook.py  # smoke-test before push
kaggle kernels push -p kaggle/_archive/notebooks/04-task-notebook-fresh
```

The build script picks the current git HEAD short SHA so the task
name (and therefore the kbench cache key) updates automatically.
