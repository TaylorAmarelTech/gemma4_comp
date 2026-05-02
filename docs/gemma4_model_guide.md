# Gemma 4 model variants — picker guide

> Which Gemma 4 variant should you load? Depends on hardware,
> use-case, and whether you care more about latency or response
> quality. This doc tabulates the trade-offs and gives you the
> single-line answer for the common cases.

## TL;DR

| You're... | Pick |
|---|---|
| Evaluating Duecare on a laptop | `gemma4:e2b` (default) |
| NGO Mac mini with 16 GB RAM | `gemma4:e2b` |
| NGO Mac mini with 32 GB RAM, ≥ 5 caseworkers | `gemma4:e4b` |
| Cloud Run / Render free tier | `gemma3:1b` (fastest cold start) |
| GPU pod (T4 / L4 / A10) for production | `gemma4:e4b` |
| Old phone (4 GB RAM) | `gemma3:1b` |
| Modern Android (8 GB+ RAM) | `gemma4:e2b` (the v0.7 default) |
| Workstation with H100 / A100 | `gemma4:31b` |

## All Gemma 4 variants we support

| Variant | Params | Quant | On-disk | Min RAM | RPS / vCPU | Latency p95 (E2B chat ≈ 200 tok) | License |
|---|---:|---|---:|---:|---:|---:|---|
| `gemma4:e2b` | 2 B | INT8 | 1.5 GB | 8 GB | 0.5 | 4-8 s (CPU) / 0.5-1 s (T4) | Apache 2.0 |
| `gemma4:e2b-int4` | 2 B | INT4 | 750 MB | 4 GB | 0.7 | 3-6 s (CPU) / 0.3-0.7 s (T4) | Apache 2.0 |
| `gemma4:e4b` | 4 B | INT8 | 3.5 GB | 16 GB | 0.25 | 8-16 s (CPU) / 1-2 s (T4) | Apache 2.0 |
| `gemma4:e4b-int4` | 4 B | INT4 | 2.0 GB | 8 GB | 0.4 | 6-12 s (CPU) / 0.7-1.5 s (T4) | Apache 2.0 |
| `gemma4:31b` | 31 B | Q4_0 | 18 GB | 32 GB | n/a (GPU only) | 1-3 s (A100) | Apache 2.0 |
| `gemma3:1b` | 1 B | INT4 | 600 MB | 4 GB | 1.2 | 1-3 s (CPU) | Apache 2.0 |
| `gemma2:2b` | 2 B | INT4 | 1.4 GB | 4 GB | 0.5 | 4-8 s (CPU) | Gemma TOU (gated) |

> Numbers measured with `tests/load/k6_chat.js` against Ollama
> on the same host. Real RPS depends on your prompt + max-tokens
> + hardware; treat ±50%.

## Compatibility map

| Where it runs | Variants supported |
|---|---|
| Ollama (CPU) | all of the above |
| Ollama (NVIDIA GPU) | all of the above |
| Ollama (Apple Silicon Metal) | all of the above |
| MediaPipe LiteRT-LM (Android) | `gemma4:e2b-int4`, `gemma4:e2b` (INT8), `gemma4:e4b-int4`, `gemma4:e4b` (INT8), `gemma3:1b`, `gemma2:2b` |
| llama.cpp / GGUF | `gemma4:e2b`, `gemma4:e4b`, `gemma4:31b` (Q4_0/Q8_0/F16) |
| HuggingFace Transformers | all (some need PEFT / transformers HEAD) |
| HuggingFace Inference Endpoint | `gemma4:e2b`, `gemma4:e4b` (paid endpoints) |

The Android app's [`ModelManager`](https://github.com/TaylorAmarelTech/duecare-journey-android/blob/main/app/src/main/java/com/duecare/journey/inference/ModelManager.kt) ships all six MediaPipe variants
selectable from Settings, each with multiple mirror-fallback URLs.

## When Gemma 4 features become load-bearing

Gemma 4 has three features the harness leans on:

1. **Native function calling.** The `Coordinator` agent
   (`packages/duecare-llm-agents/src/duecare/agents/coordinator/`)
   uses Gemma 4's function-calling protocol to dispatch among the
   GREP / RAG / Tools / Persona layers. Earlier Gemma generations
   couldn't reliably emit valid JSON tool-call payloads at this
   scale; v0.6+ assumes Gemma 4. To use Gemma 2 / 3 instead, the
   coordinator falls back to a regex-based "tool intent" parser
   with measurably lower precision.

2. **Multimodal input.** The `Scout` agent reads contract / receipt
   photos via Gemma 4's image-encoder path. Gemma 2 doesn't do this
   at all; PaliGemma 2 does but adds a second model load. v0.6+
   keeps Scout as a single-model path on Gemma 4.

3. **Native long context.** Gemma 4's 128k token context window
   lets the journey-aware prompt include the worker's full journal
   (median 5-15k tokens) without truncation. Gemma 2's 8k window
   forced ad-hoc summarization that lost evidence.

For these reasons the **default everywhere is now Gemma 4 E2B** —
Gemma 2 / 3 are kept as fallback paths but lose features.

## Picking a variant in practice

### As an NGO director with a Mac mini

```bash
# Mac mini M2 8 GB — Gemma 4 E2B fits with headroom
DUECARE_OLLAMA_MODEL=gemma4:e2b docker compose up -d

# Mac mini M2 32 GB or M2 Pro — go E4B for noticeably better answers
DUECARE_OLLAMA_MODEL=gemma4:e4b docker compose up -d
```

### As an enterprise platform on cloud GPUs

```bash
# Single-tenant T4 / L4 — E4B is sweet-spot
helm install duecare ./infra/helm/duecare \
  --set chat.env.DUECARE_OLLAMA_MODEL=gemma4:e4b \
  --set chat.nodeSelector."cloud\.google\.com/gke-accelerator"=nvidia-tesla-t4

# Multi-tenant A100 pool — 31B for premium tier, E4B for standard
# (configure per-tenant routing via feature_flags.py)
```

### As an Android app worker

The app's Settings → On-device model lets the worker pick from six
variants. Default is E2B INT8; the app's mirror-fallback list tries
`litert-community/gemma-4-E2B-it-litert-lm` then `litert-community/gemma-4-E2B-it`
then a `github.com/TaylorAmarelTech/duecare-journey-android/releases/download/models-v1/`
mirror.

### Switching at runtime

The default `docker-compose.yml` reads `DUECARE_OLLAMA_MODEL` from
`.env`. To switch:

```bash
# Edit .env or set inline
DUECARE_OLLAMA_MODEL=gemma4:e4b docker compose up -d ollama
docker compose exec ollama ollama pull gemma4:e4b
docker compose restart chat
```

The chat tier sees the new model on the next request — no rebuild.

## Future variants

- **Gemma 4 Multilingual** (Q3 2026 expected) — drop-in replacement
  for E4B with extended language coverage. Will be added to the
  picker once published.
- **Gemma 4 Instruct DPO** — internal Duecare fine-tune at
  `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-DPO-v0.1.0`
  pending the bench-and-tune Kaggle T4×2 run. Not yet shipping.

When new variants land, this doc updates + `kaggle/_INDEX.md` + the
Android app's `ModelManager.kt` get the new entries together.
