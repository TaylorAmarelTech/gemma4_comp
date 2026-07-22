# Cross-model deterministic verification leaderboard

The model-free `duecare.kit.verify` checker, run on the generated (baseline,
harness_core) response pairs for every model in the response set. No judge model,
no network, no Ollama. This is the corroboration that does not depend on the
rate-limited judge panel, extended across providers.

## Read this first: coverage is uneven

Only `gemma4:31b` has responses generated for the full 78,719-prompt registry.
The other models were generated on much smaller slices (the numbers were being
built up when the judge quota froze the pipeline). So treat the per-model lift as
"positive and consistent across providers," not as a precise ranking. The `n`
column is the honest guard: trust the big-n rows, read the small-n rows as
directional.

| Model | n | coverage | baseline /5 | harnessed /5 | lift | score regressions |
|---|---|---|---|---|---|---|
| gemma4:31b | 78,719 | full registry | 3.966 | 4.828 | +0.861 | 2.79% |
| gpt-oss:120b | 1,748 | partial | 3.244 | 4.078 | +0.835 | 20.02% |
| glm-5.2 | 410 | partial | 4.180 | 4.900 | +0.720 | 3.17% |
| deepseek-v4-pro | 182 | partial | 3.962 | 4.885 | +0.923 | 1.65% |
| minimax-m2.7 | 37 | small | 2.703 | 4.432 | +1.730 | 5.41% |
| glm-5.1 | 40 | small | 4.025 | 4.750 | +0.725 | 10.00% |
| qwen3.5:397b | 40 | small | 4.400 | 4.825 | +0.425 | 7.50% |

(`gpt-oss:20b` had only 3 pairs and is omitted as too small to report.)

## What holds up

- **The harness helps every model with a real sample.** Deterministic lift runs
  from +0.42 (qwen3.5) to +1.73 (minimax, off a low 2.70 baseline). It is never
  negative. A checker that uses no model at all, across seven providers, agrees
  the harness improves the answer.
- **The biggest gains come off the weakest baselines.** minimax (2.70) and
  gpt-oss:120b (3.24) start lowest and move the most, which is what you would
  expect if the harness is supplying structure the base model lacks.

## What to be honest about

- **gpt-oss:120b regresses on 20% of prompts** even though its net lift is
  positive. That is far higher than gemma4:31b (2.79%) or deepseek (1.65%). The
  harness interacts less cleanly with that model, and it is the first place to
  look when the answer-first ordering fix lands.
- **Small-n rows are directional only.** minimax, glm-5.1, and qwen3.5 are 37-40
  prompts each. They point the right way, but do not over-read the exact number.

## Reconciliation

This is the deterministic (0-5, model-free) view. The judge panel reports the
0-100 view (+40.7 on gemma4:31b). Different instruments, same conclusion across
models: the harness helps. Regenerate with
`python scripts/deterministic_full_registry.py --model <name>` per model, or the
whole board from the response set in one pass.
