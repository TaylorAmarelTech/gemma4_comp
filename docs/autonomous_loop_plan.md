# Autonomous benchmark engine — plan & live status

> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY
> of Claude Code. It works a queue of (model, n[, full]) benchmark jobs through
> `rich_harness_lift.py`, regenerates the leaderboard, and commits+pushes the board (data
> only) on its own clock. Shared memory: `reports/rich_lift/panel.jsonl` +
> `reports/autonomous_engine_state.json`. A `full` job grades the whole ~76k-prompt registry.

- **Started** 2026-06-26T03:38:56Z · **updated** 2026-06-26T06:30:17Z · **ticks** 2
- **Progress** 2/49 jobs · current `glm-5.2` n=300 (full registry)

## Control
- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).
- **Restart:** resumes from the state file + panel — no rework.
- **Launch:** `scripts/autonomous_engine.ps1` (loads .env, recovery venv, detaches).

## Job queue
| # | model | n | set | status |
|---:|---|---:|---|---|
| 1 | `gemma4:31b` | 300 | full | done |
| 2 | `gpt-oss:120b` | 300 | full | done |
| 3 | `glm-5.2` | 300 | full | RUNNING |
| 4 | `deepseek-v4-pro` | 300 | full | queued |
| 5 | `glm-5.1` | 40 | curated | queued |
| 6 | `deepseek-v3.2` | 40 | curated | queued |
| 7 | `kimi-k2.6` | 40 | curated | queued |
| 8 | `qwen3.5:397b` | 40 | curated | queued |
| 9 | `minimax-m2.7` | 40 | curated | queued |
| 10 | `gemma4:31b` | 1500 | full | queued |
| 11 | `gpt-oss:120b` | 1500 | full | queued |
| 12 | `glm-5.2` | 1500 | full | queued |
| 13 | `deepseek-v4-pro` | 1500 | full | queued |
| 14 | `minimax-m3` | 40 | curated | queued |
| 15 | `qwen3-coder:480b` | 40 | curated | queued |
| 16 | `mistral-large-3:675b` | 40 | curated | queued |
| 17 | `devstral-2:123b` | 40 | curated | queued |
| 18 | `nemotron-3-ultra` | 40 | curated | queued |
| 19 | `gemma4:31b` | 5000 | full | queued |
| 20 | `gpt-oss:120b` | 5000 | full | queued |
| 21 | `glm-5.2` | 5000 | full | queued |
| 22 | `deepseek-v4-pro` | 5000 | full | queued |
| 23 | `gemini-3-flash-preview` | 40 | curated | queued |
| 24 | `gemma3:27b` | 40 | curated | queued |
| 25 | `gpt-oss:20b` | 40 | curated | queued |
| 26 | `gemma3:12b` | 40 | curated | queued |
| 27 | `deepseek-v3.1:671b` | 40 | curated | queued |
| 28 | `gemma4:31b` | 15000 | full | queued |
| 29 | `gpt-oss:120b` | 15000 | full | queued |
| 30 | `glm-5.2` | 15000 | full | queued |
| 31 | `deepseek-v4-pro` | 15000 | full | queued |
| 32 | `deepseek-v4-flash` | 40 | curated | queued |
| 33 | `devstral-small-2:24b` | 40 | curated | queued |
| 34 | `nemotron-3-super` | 40 | curated | queued |
| 35 | `qwen3-coder-next` | 40 | curated | queued |
| 36 | `glm-5` | 40 | curated | queued |
| 37 | `gemma4:31b` | 40000 | full | queued |
| 38 | `gpt-oss:120b` | 40000 | full | queued |
| 39 | `glm-5.2` | 40000 | full | queued |
| 40 | `deepseek-v4-pro` | 40000 | full | queued |
| 41 | `glm-4.7` | 40 | curated | queued |
| 42 | `kimi-k2.5` | 40 | curated | queued |
| 43 | `minimax-m2.5` | 40 | curated | queued |
| 44 | `minimax-m2.1` | 40 | curated | queued |
| 45 | `ministral-3:14b` | 40 | curated | queued |
| 46 | `gemma4:31b` | all | full | queued |
| 47 | `gpt-oss:120b` | all | full | queued |
| 48 | `glm-5.2` | all | full | queued |
| 49 | `deepseek-v4-pro` | all | full | queued |

