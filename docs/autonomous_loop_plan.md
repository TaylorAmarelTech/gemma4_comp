# Autonomous benchmark engine — plan & live status

> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY
> of Claude Code. It works a queue of (model, n[, full]) benchmark jobs through
> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data
> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +
> `reports/autonomous_engine_state.json`. A `full` job grades the whole ~76k-prompt registry.

- **Started** 2026-06-26T12:54:42Z · **updated** 2026-06-26T17:58:37Z · **ticks** 1
- **Progress** 1/41 jobs · current `gpt-oss:120b` n=1500 (full registry)

## Control
- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).
- **Restart:** resumes from the state file + panel — no rework.
- **Launch:** `scripts/autonomous_engine.ps1` (loads .env, recovery venv, detaches).

## Job queue
| # | model | n | set | status |
|---:|---|---:|---|---|
| 1 | `gemma4:31b` | 1500 | full | done |
| 2 | `gpt-oss:120b` | 1500 | full | RUNNING |
| 3 | `glm-5.2` | 1500 | full | queued |
| 4 | `deepseek-v4-pro` | 1500 | full | queued |
| 5 | `glm-5.1` | 40 | curated | queued |
| 6 | `deepseek-v3.2` | 40 | curated | queued |
| 7 | `kimi-k2.6` | 40 | curated | queued |
| 8 | `qwen3.5:397b` | 40 | curated | queued |
| 9 | `minimax-m2.7` | 40 | curated | queued |
| 10 | `minimax-m3` | 40 | curated | queued |
| 11 | `qwen3-coder:480b` | 40 | curated | queued |
| 12 | `gemma4:31b` | 10000 | full | queued |
| 13 | `gpt-oss:120b` | 10000 | full | queued |
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

