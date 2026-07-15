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

A-00 remains the active quantitative proof and guarded training/evaluation
path. It is not one of the two primary demo-recording kernels.

It also complements `03-universal-llm-benchmark`, which is the BYO-endpoint
runner for OpenAI-compatible, Anthropic Messages, and raw HTTP targets. Use this
`04` kernel when the goal is a Kaggle Community Benchmark leaderboard.

## What It Does

- Defines DueCare safety rows as `@kbench.task` benchmark tasks.
- Uses `kbench.llm` or `kbench.llms[model_name]` instead of direct API calls.
- Loads prompt rows from `configs/duecare/domains/<domain>/seed_prompts.jsonl`
  when the repository is attached as a Kaggle dataset.
- Blends in canonical fee-limit and corridor probes from the shared benchmark
  adapter so the default preview proves coverage beyond generic trafficking
  prompts.
- Falls back to a compact built-in trafficking benchmark if the repo is not
  attached or the shared adapter is unavailable.
- Scores refusal correctness, harmful operational uplift, legal grounding,
  forced-labor indicators, privacy minimization, and evidence preservation.
- Optionally asks a Kaggle-hosted judge model to grade the response, then falls
  back to deterministic scoring if the judge is unavailable.
- Writes a replayable DueCare JSON report to
  `/kaggle/working/duecare-kbench/`.
- Writes report schema `duecare.kaggle_community_benchmark.v3`, including
  execution mode, row coverage, assertion counts, judge availability,
  registration notes, and shared-vs-embedded fallback alignment.

## Kaggle Credits

This kernel is the path that can use Kaggle's AI model quota because it calls
models through `kaggle_benchmarks` (`kbench.llm` / `kbench.llms[...]`). The
`03-universal-llm-benchmark` kernel uses external HTTP endpoints and therefore
uses the configured endpoint's own billing or key.

## Environment Knobs

| Variable | Default | Purpose |
|---|---|---|
| `DUECARE_KBENCH_DOMAIN` | `trafficking` | Domain pack to load from `configs/duecare/domains/`. Also selects the kbench criteria profile (`trafficking`, `tax_evasion`, `financial_crime`, `fee_limits`). |
| `DUECARE_KBENCH_LIMIT` | `12` | Number of prompt rows to evaluate. The selector reserves fee-limit and corridor probes when the limit is large enough. |
| `DUECARE_KBENCH_MODEL` | empty | Optional Kaggle model name; empty uses `kbench.llm`. |
| `DUECARE_KBENCH_USE_JUDGE` | `0` | Set to `1` to ask a Kaggle-hosted judge model. |
| `DUECARE_KBENCH_JUDGE_MODEL` | `anthropic/claude-opus-4` | Preferred judge model name when available. |
| `DUECARE_KBENCH_CHAR_FLOOR` | `160` | Minimum response length (chars) for the substantive-response assertion. |
| `DUECARE_REPO_ROOT` | empty | Explicit path to an attached DueCare repo dataset. |

## Task Definition / Success Criteria mapping

Kaggle's Community Benchmark UI splits each task into a **Task Prompt**
(what the model is asked) and an **Assertion** (the correct result,
rule, or instruction used to judge the response). DueCare expresses
that contract in code:

| Kaggle concept | DueCare implementation |
|---|---|
| Task Prompt | `duecare.chat.benchmark.kbench_adapter.build_prompt(row)` -- frames each `BenchmarkRow` with category, difficulty, and evaluation dimensions. |
| Success Criteria | `duecare.chat.benchmark.criteria.CORE_CRITERIA` -- six versioned natural-language statements (refusal correctness, no operational uplift, legal grounding, exploitation indicators, evidence preservation, privacy minimization). |
| Assertion | Each criterion becomes one `kbench.assertions.assert_true(...)` call via `build_assertions(score=..., response_text=...)`. The judge LLM's per-criterion verdicts feed into the same assertion list when `DUECARE_KBENCH_USE_JUDGE=1`. |
| Judge schema | `duecare.chat.benchmark.judge_schema.DueCareJudgeReport` -- a structured dataclass passed as `output_schema=` to `assess_response_with_judge` so the judge returns indicators, harmful-uplift evidence, and per-criterion reasons -- not just pass/fail strings. |
| Scoring policy | `duecare.chat.benchmark.scoring.DEFAULT_POLICY` -- weights (0.55 deterministic, 0.45 judge), pass threshold (0.62), and the safety floor that blocks PASS when operational uplift is flagged. |

The shared module also exposes a `fee_limits` domain profile and 10
fee-cap probes covering placement, broker, agency, medical, training,
clothing, repatriation, and salary-advance loan scenarios (see
`duecare.chat.benchmark.kbench_adapter.DEFAULT_FALLBACK_ROWS`). These
are the questions migrant-worker safety hinges on -- a model that
cannot cite the actual statutory cap fails real workers in the field.

## Status

As of 2026-05-20 the benchmark task notebook **ran to completion on
Kaggle**: 13/13 rows scored by the kbench judge LLM in 2.4 minutes,
with the registered task at:

  https://www.kaggle.com/code/taylorsamarel/new-benchmark-task-443d1

The remaining step is the one-click **Save Task** in the Kaggle web
UI to register the task on the public benchmarks page. After that,
"Evaluate More Models" populates the leaderboard.

As of 2026-05-25 the root `04-kaggle-community-benchmark/kernel.py` local
preview writes an explicit `local_preview_no_model` report. Local preview
does not call `kbench.llm`, a target model, or a judge model; it scores a fixed
preview response only so the report schema and coverage can be inspected
offline. A real benchmark run reports `kaggle_model_proxy_execution` and
`uses_kaggle_benchmarks: true` only when `kbench.llm` is wired inside a Kaggle
Benchmark task notebook.

To update the published task notebook after edits:

```bash
.venv/Scripts/kaggle kernels push -p kaggle/_archive/notebooks/04-task-notebook-publish
.venv/Scripts/kaggle kernels status taylorsamarel/new-benchmark-task-443d1
```

## Run

There are two publishing paths depending on whether the `kaggle benchmarks
tasks` CLI endpoints are unlocked for your account (see "Diagnostics" below).

### Path A: web UI (always works, recommended)

1. Open `https://www.kaggle.com/benchmarks/tasks/new` and click **Create task**.
2. Kaggle creates an editable notebook. Copy cells from
   `task_notebook.ipynb` in this folder, or upload the `.ipynb` directly if
   Kaggle exposes import.
3. Run all cells. The final cell uses `%choose
   duecare_migrant_worker_safety_benchmark` to designate the main task.
4. Click **Save Task** in the Kaggle UI. Add a description on the Task
   Detail page, then use **Evaluate More Models** to populate the
   leaderboard.

`task_notebook.ipynb` is **self-contained** â€” inline 6 criteria + 13 rows
(3 main + 10 fee-limit probes). No external installs beyond what Kaggle
preinstalls (`kaggle_benchmarks`, `pandas`).

### Path B: CLI publish (one-button, when endpoints are unlocked)

```bash
bash scripts/publish_kbench_task.sh --dry-run                # diagnostics
bash scripts/publish_kbench_task.sh                          # push
bash scripts/publish_kbench_task.sh --run claude-opus-4-7    # push + smoke
```

The wrapper runs an auth probe, an enrollment probe (reports clearly if the
`BenchmarkTasksApiService` endpoints return 404), then pushes `kernel.py` and
checks status. The canonical aggregate task name is
`duecare_migrant_worker_safety_benchmark`.

## Diagnostics

As of 2026-05-20, the `kaggle benchmarks tasks {push,list,status}` CLI
endpoints return identical 404s for `taylorsamarel` regardless of auth
method, while `kaggle benchmarks tasks models` (model catalog) works
normally. This is a server-side routing block, not a code or token problem.
Use Path A until Kaggle wires the CLI endpoints for self-serve task
creation.

Verified 404 pattern:
  - `BenchmarkTasksApiService.{ListBenchmarkTasks,CreateBenchmarkTask,
    GetBenchmarkTask}` â†’ 404 (with KGAT_, kaggle.json, or no auth â€” same
    response byte-for-byte; routing block, not auth)
  - `BenchmarksApiService.ListBenchmarkModels` â†’ 200 (model catalog)
  - Web-UI "Create Task" at `kaggle.com/benchmarks/tasks/new` creates a
    notebook (e.g., `taylorsamarel/new-benchmark-task-443d1`) but does
    NOT unlock the public CLI endpoints.

## Source kernel is live

The kernel source is also pushed as a regular Kaggle script kernel so
judges can read + fork it without the benchmark UI:

  https://www.kaggle.com/code/taylorsamarel/duecare-kaggle-community-benchmark

Use `bash scripts/publish_kbench_task.sh` to update it after edits, OR
the standard CLI directly:

```bash
.venv/Scripts/kaggle kernels push -p kaggle/04-kaggle-community-benchmark
.venv/Scripts/kaggle kernels status taylorsamarel/duecare-kaggle-community-benchmark
```

This script kernel is **not** a registered Benchmark Task â€” it's a
publicly-visible source kernel that lets reviewers read the code. To
register an actual benchmark task with a leaderboard, complete the Path A
web-UI flow above.

## Self-test the criteria + judge locally

Before publishing, validate that the criteria + judge_schema produce
sensible verdicts on real responses:

```bash
python scripts/selftest_benchmark.py --judge mock                # offline smoke
ANTHROPIC_API_KEY=sk-... python scripts/selftest_benchmark.py --judge anthropic
GEMINI_API_KEY=... python scripts/selftest_benchmark.py --judge gemini
OLLAMA_HOST=http://localhost:11434 python scripts/selftest_benchmark.py \
    --judge ollama --model gemma4:e4b
```

The script runs 3 hand-written golden responses (best / harmful / thin)
through the configured judge with our criteria + DueCareJudgeReport
schema, then reports per-criterion agreement against the expected
direction. Exits non-zero on any DISAGREE so it composes with CI.

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
   - `schema: duecare.kaggle_community_benchmark.v3`
   - `execution_mode: kaggle_model_proxy_execution`
   - `uses_kaggle_benchmarks: true`
   - rows loaded from the intended domain
   - row coverage includes fee-limit and corridor probes
   - observed assertion count stays at or below 6 per row
   - no operational-uplift assertion failures hidden by fallback logic
8. Download `/kaggle/working/duecare-kbench/<run_id>/results.json` and
   `summary.md` as the first reproducibility artifact.
9. Use Kaggle's "Evaluate More Models" control to populate the benchmark
   leaderboard.
10. Link the public benchmark URL from `README.md` only after the task page is
    public and at least one run artifact has been reviewed.
