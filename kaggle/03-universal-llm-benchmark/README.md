# DueCare Universal LLM Benchmark

<!-- duecare:lane-label -->
> **Serves lanes:** Researcher; Developer / integration partner.

Purpose: benchmark any chat-style model endpoint against DueCare prompts,
rubric dimensions, evidence cues, and harness expectations, then judge the
responses with Claude Opus when an Anthropic API key is available.

This kernel is an optional evaluation surface. The primary recording path is
still:

1. `01-duecare-exploration-workbench`
2. `02-live-demo`
3. `A-00-omni-experiment-workbench`

Use this kernel when you want to compare external APIs, local OpenAI-compatible
servers, hosted endpoints, or future Gemma variants without editing the main
workbench.

## What It Tests

- DueCare seed prompts from `configs/duecare/domains/*/seed_prompts.jsonl`
  when the repo or a repo dataset is attached.
- Built-in fallback trafficking prompts when the full repo is not attached.
- Rubric dimensions from the DueCare domain config when available.
- Harness inventory and package/test counts from the attached repo when
  available.
- Deterministic safety checks for refusal correctness, harmful operational
  guidance, legal grounding, privacy minimization, and evidence quality.
- Optional Claude Opus judging through Anthropic Messages API.

## Endpoint Modes

| Provider | Use |
|---|---|
| `openai_compatible` | OpenAI, vLLM, Ollama OpenAI server, LM Studio, Together, Fireworks, or any `/chat/completions` endpoint. |
| `anthropic_messages` | Anthropic-compatible Messages API targets. |
| `raw_http` | Arbitrary JSON POST endpoint with a `{{prompt}}` and `{{model}}` body template. |

## Required Secrets

- Target model key: configured by `target.api_key_env`.
- Claude Opus judge key: `ANTHROPIC_API_KEY`, or another env var configured by
  `judge.api_key_env`.

The default judge model is `claude-opus-4-7`, but the UI exposes
`judge.model` so it can be changed without editing code.

## Outputs

Each run writes:

- `results.json` - summary, config, and per-prompt scores.
- `calls.jsonl` - replayable target and judge call records.
- `summary.md` - human-readable report.

Files are written under:

```text
/kaggle/working/universal-benchmark/<run_id>/
```

## Run

Copy `kernel.py` into Kaggle, enable Internet, add any API keys as Kaggle
secrets/environment variables, and run the cell. The kernel starts a local
FastAPI app and attempts to print a Cloudflare quick-tunnel URL.
