# Benchmark data audit (SQLite index over the run checkpoints)

> Ingests `reports/rich_lift/{panel,results}.jsonl` into `reports/rich_lift/benchmark.db` and audits integrity. Regenerate with `python scripts/benchmark_db.py`. Counts only; no prompt or response text.

**40,814 responses** and **29,393 judge rows** (0.72 judges per response on average -- self-family exclusion keeps this below the 3-judge panel size).

## Integrity checks

- [ok] **Duplicate judge rows (same model/prompt/arm/judge): 0**
- [ok] **Duplicate responses (same model/prompt/arm): 0**
- [ok] **Scored cells with no stored response (orphan panel): 0**
- [!!] **Responses never scored (orphan results): 28,840**
- [ok] **Scores out of 0-100 range: 0**
- [ok] **Components out of their max range: 0**
- [!!] **Empty responses: 1**
- [ok] **Responses with an unknown arm: 0**

## Coverage

- Prompts with all 3 arms generated: **13,601**; partial (missing an arm): **7**.

- Judges per graded cell: 1 judge(s): 1, 2 judge(s): 6,527, 3 judge(s): 5,446.

## Responses per model

| Model | responses |
|---|---:|
| `gemma4:31b` | 34,053 |
| `gpt-oss:120b` | 4,614 |
| `glm-5.2` | 1,234 |
| `deepseek-v4-pro` | 547 |
| `glm-5.1` | 120 |
| `qwen3.5:397b` | 120 |
| `minimax-m2.7` | 117 |
| `gpt-oss:20b` | 9 |

Per arm: `harness_full` 13,606, `harness_core` 13,606, `baseline` 13,602.  
Per judge: `deepseek-v4-pro` 11,423, `glm-5.2` 10,620, `gpt-oss:120b` 7,350.

