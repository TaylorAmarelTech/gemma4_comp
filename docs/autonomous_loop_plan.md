# Autonomous benchmark engine - plan & live status

> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY
> of Claude Code. It works a queue of (model, n[, full]) benchmark jobs through
> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data
> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +
> `reports/autonomous_engine_state.json`. Latest readiness: `reports/autonomous_engine_preflight.json`.
> A `full` job grades the whole ~76k-prompt registry.

- **Started** 2026-06-26T12:54:42Z - **updated** 2026-07-12T07:38:10Z - **ticks** 12
- **Progress** 12/41 jobs - current `gpt-oss:120b` n=10000 (full registry)

## Control
- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).
- **Status:** `scripts/autonomous_engine.ps1 -Status` reports state cursor/queue health, the current job, active runner cell counts, candidate-dimension sweep readiness, pause sentinel, lock liveness, whether the latest saved preflight blockers still match current state without calling Ollama, and whether that saved readiness was launch-scoped or state-only; missing, unreadable, or state-stale preflight reports are flagged as unmatched and include a pause-safe refresh command.
- **Preflight:** `scripts/autonomous_engine.ps1 -Preflight` checks sentinel, lock, state cursor/queue shape, full promptset, panel, dimension candidates, and Ollama before restart, fails closed on malformed state, malformed candidate-dimension JSONL, plus unreadable or stale review artifacts, then writes `reports/autonomous_engine_preflight.json`. Add `-IgnoreStopSentinel` to preview launch readiness while paused. `-NoOllamaCheck` writes a `state_only` diagnostic report and returns a non-launch exit code even when state checks pass; the wrapper preserves the Python exit code in `$LASTEXITCODE`, and `powershell -File` callers receive the same process exit code.
- **Startup gate:** normal wrapper launches preflight before detach while treating the pause sentinel as an ignored launch blocker; it removes the sentinel only after readiness passes. `-NoOllamaCheck` / `--no-ollama-check` is state-only for preflight diagnostics and is refused for normal startup execution (`-Run`, `-Once`, or direct Python loop mode). The Python engine also preflights before taking the lock or starting a tick. Emergency override is `--skip-startup-preflight`.
- **Watchdog:** `scripts/autonomous_engine.ps1 -Register` installs a pause-preserving Task Scheduler launcher (`-WatchdogRun`) that does not ignore or remove `reports/autonomous_engine.stop`; registration and later watchdog ticks do not resume paused judging.
- **Restart:** explicitly run `scripts/autonomous_engine.ps1 -Run`; the wrapper verifies launch readiness, then removes `reports/autonomous_engine.stop` and resumes from the state file + panel - no rework.
- **Launch:** `scripts/autonomous_engine.ps1 -Run` (loads .env, recovery venv, detaches).

## Current scope
- **Active runner:** `rich_harness_lift.py`; board rubric version: `v1`; opt-in rubric versions excluded: `v2`; rubric mixing allowed: `no`; board harness version: `h1`; opt-in harness versions excluded: `h2`; harness mixing allowed: `no`; candidate-dimension sweep active: `no`.
- **Active job estimate:** 10,000 target prompts; 30,000 response-generation cells; 90,000 component-judge cells; 30,000 pairwise-judge cells.
- **Candidate dimension sweep estimate:** 201 candidate dimensions; 201 still need curator review; 15,822,519 full-registry prompt-dimension cells if later promoted.
- **Dimension promotion gate:** build `reports/benchmark/research_spider_dimension_candidate_review_packet.json`, fill curator review fields, then validate it before rubric merge.
- **Dimension review artifacts:** gate `validated_zero_proposals`; accepted proposals 0; ready claims 0.
- **Mass-grading guard:** candidate-dimension row labels alone are not enough; the review gate must report promotion-ready proposals before any candidate-dimension sweep is ready.

## Job queue
| # | model | n | set | status |
|---:|---|---:|---|---|
| 1 | `gemma4:31b` | 1500 | full | done |
| 2 | `gpt-oss:120b` | 1500 | full | done |
| 3 | `glm-5.2` | 1500 | full | done |
| 4 | `deepseek-v4-pro` | 1500 | full | done |
| 5 | `glm-5.1` | 40 | curated | done |
| 6 | `deepseek-v3.2` | 40 | curated | done |
| 7 | `kimi-k2.6` | 40 | curated | done |
| 8 | `qwen3.5:397b` | 40 | curated | done |
| 9 | `minimax-m2.7` | 40 | curated | done |
| 10 | `minimax-m3` | 40 | curated | done |
| 11 | `qwen3-coder:480b` | 40 | curated | done |
| 12 | `gemma4:31b` | 10000 | full | done |
| 13 | `gpt-oss:120b` | 10000 | full | RUNNING |
| 14 | `glm-5.2` | 10000 | full | queued |
| 15 | `deepseek-v4-pro` | 10000 | full | queued |
| 16 | `mistral-large-3:675b` | 40 | curated | queued |
| 17 | `devstral-2:123b` | 40 | curated | queued |
| 18 | `nemotron-3-ultra` | 40 | curated | queued |
| 19 | `gemini-3-flash-preview` | 40 | curated | queued |
| 20 | `gemma3:27b` | 40 | curated | queued |
| 21 | `gpt-oss:20b` | 40 | curated | queued |
| 22 | `gemma3:12b` | 40 | curated | queued |
| 23 | `gemma4:31b` | 40000 | full | queued |
| 24 | `gpt-oss:120b` | 40000 | full | queued |
| 25 | `glm-5.2` | 40000 | full | queued |
| 26 | `deepseek-v4-pro` | 40000 | full | queued |
| 27 | `deepseek-v3.1:671b` | 40 | curated | queued |
| 28 | `deepseek-v4-flash` | 40 | curated | queued |
| 29 | `devstral-small-2:24b` | 40 | curated | queued |
| 30 | `nemotron-3-super` | 40 | curated | queued |
| 31 | `qwen3-coder-next` | 40 | curated | queued |
| 32 | `glm-5` | 40 | curated | queued |
| 33 | `glm-4.7` | 40 | curated | queued |
| 34 | `gemma4:31b` | all | full | queued |
| 35 | `gpt-oss:120b` | all | full | queued |
| 36 | `glm-5.2` | all | full | queued |
| 37 | `deepseek-v4-pro` | all | full | queued |
| 38 | `kimi-k2.5` | 40 | curated | queued |
| 39 | `minimax-m2.5` | 40 | curated | queued |
| 40 | `minimax-m2.1` | 40 | curated | queued |
| 41 | `ministral-3:14b` | 40 | curated | queued |

