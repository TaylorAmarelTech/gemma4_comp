# Autonomous benchmark engine - plan & paused status

> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY
> of Claude Code. It works a queue of (model, n[, full[, grader]]) benchmark jobs through
> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data
> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +
> `reports/rich_lift/panel_perdim.jsonl.components.sqlite3` + exact coverage manifest +
> `reports/autonomous_engine_state.json`. Latest readiness: `reports/autonomous_engine_preflight.json`.
> A required `full`/`perdim` job grades every prompt in the frozen generated registry and cannot
> advance or be skipped until every response, panel cell, and A-E output is complete.

- **Started** 2026-06-26T12:54:42Z - **updated** 2026-07-26T21:08:58Z - **ticks** 16
- **Progress** 12/49 jobs complete - paused before `gemma4:31b` n=all (full registry) grader=perdim
- **Pause sentinel:** `reports/autonomous_engine.stop` exists; the engine will not start a new tick until it is removed.

## Control
- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).
- **Status:** `scripts/autonomous_engine.ps1 -Status` reports state cursor/queue health, the current job, active runner cell counts, candidate-dimension sweep readiness, pause sentinel, lock liveness, whether the latest saved preflight blockers still match current state without calling Ollama, and whether that saved readiness was launch-scoped or state-only; missing, unreadable, or state-stale preflight reports are flagged as unmatched and include a pause-safe refresh command.
- **Preflight:** `scripts/autonomous_engine.ps1 -Preflight` checks sentinel, lock, state cursor/queue shape, full promptset, panel, dimension candidates, and Ollama before restart, fails closed on malformed state, malformed candidate-dimension JSONL, plus unreadable or stale review artifacts, then writes `reports/autonomous_engine_preflight.json`. Add `-IgnoreStopSentinel` to preview launch readiness while paused. `-NoOllamaCheck` writes a `state_only` diagnostic report and returns a non-launch exit code even when state checks pass; the wrapper preserves the Python exit code in `$LASTEXITCODE`, and `powershell -File` callers receive the same process exit code.
- **Startup gate:** normal wrapper launches preflight before detach while treating the pause sentinel as an ignored launch blocker; it removes the sentinel only after readiness passes. `-NoOllamaCheck` / `--no-ollama-check` is state-only for preflight diagnostics and is refused for normal startup execution (`-Run`, `-Once`, or direct Python loop mode). The Python engine also preflights before taking the lock or starting a tick. Emergency override is `--skip-startup-preflight`.
- **Watchdog:** `scripts/autonomous_engine.ps1 -Register` installs a pause-preserving Task Scheduler launcher (`-WatchdogRun`). While `reports/autonomous_engine.stop` exists, watchdog ticks exit successfully before preflight: they do not call Ollama, rewrite readiness evidence, remove the sentinel, or resume judging.
- **Stall manager:** `scripts/manage_flywheel.ps1` watches successful JSONL/SQLite progress plus the aggregate-only coverage heartbeat. Fresh failure telemetry proves the runner is alive during a provider outage and prevents a false destructive restart; `-CheckOnly` reports the decision without restarting.
- **Restart:** explicitly run `scripts/autonomous_engine.ps1 -Run`; the wrapper verifies launch readiness, then removes `reports/autonomous_engine.stop` and resumes from the state file + panel - no rework.
- **Code reload:** `scripts/autonomous_engine.ps1 -Restart` verifies the lock PID belongs to this repository's engine, stops only that process tree, and relaunches from JSONL/SQLite checkpoints.
- **Launch:** `scripts/autonomous_engine.ps1 -Run` (loads .env, recovery venv, detaches).
- **Primary-flywheel terminal:** after exact closure for Gemma 4, gpt-oss, GLM, and DeepSeek, the engine writes the pause sentinel and exits before legacy/breadth jobs; an explicit `-Run` opts into those later jobs.

## Current scope
- **Active runner:** `rich_harness_lift.py`; board rubric version: `v1`; opt-in rubric versions excluded: `v2`; rubric mixing allowed: `no`; board harness version: `h1`; opt-in harness versions excluded: `h2`; harness mixing allowed: `no`; grader: `perdim`; per-dimension evidence mixed into board: `no`; candidate-dimension sweep active: `no`.
- **Active job estimate:** 78,719 target prompts; 236,157 response-generation cells; 708,471 component-judge cells; 3,542,355 underlying component judge calls (5 per panel cell); 0 pairwise-judge cells.
- **Candidate dimension sweep estimate:** 201 candidate dimensions; 201 still need curator review; 15,822,519 full-registry prompt-dimension cells if later promoted.
- **Dimension promotion gate:** build `reports/benchmark/research_spider_dimension_candidate_review_packet.json`, fill curator review fields, then validate it before rubric merge.
- **Dimension review artifacts:** gate `validated_zero_proposals`; accepted proposals 0; ready claims 0.
- **Mass-grading guard:** candidate-dimension row labels alone are not enough; the review gate must report promotion-ready proposals before any candidate-dimension sweep is ready.

## Job queue
| # | model | n | set | grader | status |
|---:|---|---:|---|---|---|
| 1 | `gemma4:31b` | 1500 | full | batched | done |
| 2 | `gpt-oss:120b` | 1500 | full | batched | done |
| 3 | `glm-5.2` | 1500 | full | batched | done |
| 4 | `deepseek-v4-pro` | 1500 | full | batched | done |
| 5 | `glm-5.1` | 40 | curated | batched | done |
| 6 | `deepseek-v3.2` | 40 | curated | batched | done |
| 7 | `kimi-k2.6` | 40 | curated | batched | done |
| 8 | `qwen3.5:397b` | 40 | curated | batched | done |
| 9 | `minimax-m2.7` | 40 | curated | batched | done |
| 10 | `minimax-m3` | 40 | curated | batched | done |
| 11 | `qwen3-coder:480b` | 40 | curated | batched | done |
| 12 | `gemma4:31b` | 10000 | full | batched | done |
| 13 | `gemma4:31b` | all | full | perdim | paused |
| 14 | `gpt-oss:120b` | all | full | perdim | queued |
| 15 | `glm-5.2` | all | full | perdim | queued |
| 16 | `deepseek-v4-pro` | all | full | perdim | queued |
| 17 | `gemma4:31b` | all | full | batched | queued |
| 18 | `gpt-oss:120b` | all | full | batched | queued |
| 19 | `glm-5.2` | all | full | batched | queued |
| 20 | `deepseek-v4-pro` | all | full | batched | queued |
| 21 | `gpt-oss:120b` | 10000 | full | batched | queued |
| 22 | `glm-5.2` | 10000 | full | batched | queued |
| 23 | `deepseek-v4-pro` | 10000 | full | batched | queued |
| 24 | `mistral-large-3:675b` | 40 | curated | batched | queued |
| 25 | `devstral-2:123b` | 40 | curated | batched | queued |
| 26 | `nemotron-3-ultra` | 40 | curated | batched | queued |
| 27 | `gemini-3-flash-preview` | 40 | curated | batched | queued |
| 28 | `gemma3:27b` | 40 | curated | batched | queued |
| 29 | `gpt-oss:20b` | 40 | curated | batched | queued |
| 30 | `gemma3:12b` | 40 | curated | batched | queued |
| 31 | `gemma4:31b` | 40000 | full | batched | queued |
| 32 | `gpt-oss:120b` | 40000 | full | batched | queued |
| 33 | `glm-5.2` | 40000 | full | batched | queued |
| 34 | `deepseek-v4-pro` | 40000 | full | batched | queued |
| 35 | `deepseek-v3.1:671b` | 40 | curated | batched | queued |
| 36 | `deepseek-v4-flash` | 40 | curated | batched | queued |
| 37 | `devstral-small-2:24b` | 40 | curated | batched | queued |
| 38 | `nemotron-3-super` | 40 | curated | batched | queued |
| 39 | `qwen3-coder-next` | 40 | curated | batched | queued |
| 40 | `glm-5` | 40 | curated | batched | queued |
| 41 | `glm-4.7` | 40 | curated | batched | queued |
| 42 | `gemma4:31b` | all | full | batched | queued |
| 43 | `gpt-oss:120b` | all | full | batched | queued |
| 44 | `glm-5.2` | all | full | batched | queued |
| 45 | `deepseek-v4-pro` | all | full | batched | queued |
| 46 | `kimi-k2.5` | 40 | curated | batched | queued |
| 47 | `minimax-m2.5` | 40 | curated | batched | queued |
| 48 | `minimax-m2.1` | 40 | curated | batched | queued |
| 49 | `ministral-3:14b` | 40 | curated | batched | queued |

