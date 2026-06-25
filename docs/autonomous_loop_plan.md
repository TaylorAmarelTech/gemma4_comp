# Autonomous benchmark engine — plan & live status

> A durable, self-contained loop (`scripts/autonomous_engine.py`) that runs INDEPENDENTLY
> of Claude Code. It works a queue of (model, n) benchmark jobs through `rich_harness_lift.py`,
> regenerates the leaderboard, and commits+pushes the board (data only) on its own clock.
> Shared memory: `reports/rich_lift/panel.jsonl` + `reports/autonomous_engine_state.json`.

- **Started** 2026-06-25T19:15:20Z · **updated** 2026-06-25T23:24:49Z · **ticks** 3
- **Progress** 3/36 jobs · current `glm-5.1` n=40

## Control
- **Stop gracefully:** create `reports/autonomous_engine.stop` (checked each tick).
- **Restart:** resumes from the state file + panel — no rework.
- **Launch:** `scripts/autonomous_engine.ps1` (loads .env, recovery venv, detaches).

## Job queue
| # | model | n | status |
|---:|---|---:|---|
| 1 | `gpt-oss:120b` | 40 | done |
| 2 | `glm-5.2` | 40 | done |
| 3 | `deepseek-v4-pro` | 40 | done |
| 4 | `glm-5.1` | 40 | RUNNING |
| 5 | `deepseek-v3.2` | 40 | queued |
| 6 | `kimi-k2.6` | 40 | queued |
| 7 | `qwen3.5:397b` | 40 | queued |
| 8 | `minimax-m2.7` | 40 | queued |
| 9 | `minimax-m3` | 40 | queued |
| 10 | `qwen3-coder:480b` | 40 | queued |
| 11 | `mistral-large-3:675b` | 40 | queued |
| 12 | `devstral-2:123b` | 40 | queued |
| 13 | `nemotron-3-ultra` | 40 | queued |
| 14 | `gemini-3-flash-preview` | 40 | queued |
| 15 | `gemma3:27b` | 40 | queued |
| 16 | `gemma4:31b` | all 776 | queued |
| 17 | `glm-5.2` | all 776 | queued |
| 18 | `deepseek-v4-pro` | all 776 | queued |
| 19 | `kimi-k2.6` | all 776 | queued |
| 20 | `gpt-oss:20b` | 40 | queued |
| 21 | `gemma3:12b` | 40 | queued |
| 22 | `deepseek-v3.1:671b` | 40 | queued |
| 23 | `deepseek-v4-flash` | 40 | queued |
| 24 | `devstral-small-2:24b` | 40 | queued |
| 25 | `nemotron-3-super` | 40 | queued |
| 26 | `qwen3-coder-next` | 40 | queued |
| 27 | `glm-5` | 40 | queued |
| 28 | `glm-4.7` | 40 | queued |
| 29 | `kimi-k2.5` | 40 | queued |
| 30 | `minimax-m2.5` | 40 | queued |
| 31 | `minimax-m2.1` | 40 | queued |
| 32 | `ministral-3:14b` | 40 | queued |
| 33 | `gpt-oss:120b` | all 776 | queued |
| 34 | `qwen3.5:397b` | all 776 | queued |
| 35 | `qwen3-coder:480b` | all 776 | queued |
| 36 | `minimax-m3` | all 776 | queued |

