# DiffusionGemma as DueCare's fast screening tier

> Status: integration design + the parts that are live today. Written
> 2026-06-11, the day after Google released DiffusionGemma. Everything in
> the "Live today" table is wired and tested; everything in "Pending GPU
> verification" is explicitly NOT claimed as working.

## What DiffusionGemma is

Google released **DiffusionGemma** (`google/diffusiongemma-26B-A4B-it`) on
2026-06-10: a 26B Mixture-of-Experts **text-diffusion** model built on the
Gemma 4 26B-A4B backbone.

| Property | Value |
|---|---|
| Architecture | 26B MoE on the Gemma 4 26B-A4B backbone, 3.8B active params |
| Decoding | 256-token canvases denoised in parallel (block-autoregressive beyond 256) |
| Speed | up to **4x faster** generation; 1000+ tok/s on one H100, 700+ tok/s on an RTX 5090 |
| VRAM | fits in ~18 GB quantized (single 24 GB GPU, or 2x T4-class with a balanced device map) |
| Context | 262K tokens |
| Serving | vLLM native (`--diffusion-config '{"canvas_length": 256}'`), plus HF Transformers, SGLang, MLX, NeMo, Unsloth |
| License | Apache 2.0 |
| **Quality** | **below standard Gemma 4** — the speed is bought with a quality tradeoff |

The quality caveat is the load-bearing fact for this design. DiffusionGemma
is NOT a drop-in replacement for the Gemma 4 models DueCare answers with.
It is the right model for exactly one seat in the architecture: the seat
where throughput matters and the output only routes.

## Where it fits: the triage waterfall

Deployment mode 1 (platform safety) screens job ads and recruiter messages
at platform scale. The `triage` harness
(`packages/duecare-llm-chat/src/duecare/chat/harnesses/triage/`) implements
the waterfall:

```
GREP rules            deterministic, microseconds — flags known patterns
   -> fast model      one flag/clear JSON verdict per item   <- DiffusionGemma's seat
      -> deep model   full GREP/RAG/tools-grounded Gemma 4 analysis,
                      ONLY for escalated items
```

Why the quality tradeoff is acceptable HERE and nowhere else:

1. **The fast tier routes; it never answers.** A "clear" verdict means "no
   signal worth deep review", not "safe". No worker, caseworker, or
   moderator ever reads fast-tier text.
2. **Failure degrades to review, never to cleared.** A malformed JSON
   reply, a backend error, or low confidence all route the item to
   "review". A medium-severity GREP hit overrides even a confident
   fast-tier "clear" (deterministic evidence wins).
3. **The deep tier is unchanged.** Escalated items get the slower,
   stronger, grounded Gemma 4 treatment — the same primitives as the
   Kernel 01 comparison arm.

### Throughput arithmetic (estimate — measure before quoting)

A screening verdict is ~120-160 output tokens. At DiffusionGemma's
published 700-1000 tok/s, one GPU produces roughly **4.5-6.5 verdicts per
second**, on the order of **400-550K items/day** — with the deep model
spending time only on the few percent that escalate. For comparison, an
autoregressive model at ~175-250 tok/s on the same hardware screens ~4x
fewer. These are arithmetic projections from the published speeds, not
DueCare measurements; the `/api/triage/screen` response includes
`measured_items_per_min` precisely so real numbers replace this paragraph
after the first GPU run.

## Live today (wired + tested, no GPU required)

| Piece | Where | Proof |
|---|---|---|
| Triage harness (GREP -> fast -> deep, honest degradation) | `harnesses/triage/handler.py` | 19 tests in `packages/duecare-llm-chat/tests/test_triage.py` |
| OpenAI-compatible fast-tier transport (the protocol vLLM serves DiffusionGemma over) | `resolve_fast_backend()` env path | `test_resolve_fast_backend_prefers_env_endpoint` |
| In-process loaded-Gemma fallback for the fast tier | `resolve_fast_backend()` app.state path | `test_screen_endpoint_uses_loaded_gemma_as_fast_tier` |
| Per-stage timings + measured fast-tier throughput in every response | `screen_items()` summary | `test_grep_high_severity_flags_without_model_time` et al. |
| Harness contract + registry + ecosystem inventory | `harnesses/triage/__init__.py`, `PRIMARY_HARNESSES`, `docs/harness_ecosystem.md` | `test_harness_registered_as_primary` |

### Point DueCare at a DiffusionGemma endpoint

```bash
# 1) serve the model (any box with ~18 GB VRAM quantized)
vllm serve google/diffusiongemma-26B-A4B-it \
  --max-model-len 262144 \
  --diffusion-config '{"canvas_length": 256}'

# 2) tell the kernel where the fast tier lives
export DUECARE_FAST_MODEL_BASE_URL="http://localhost:8000/v1"
export DUECARE_FAST_MODEL_ID="google/diffusiongemma-26B-A4B-it"
# optional: DUECARE_FAST_MODEL_API_KEY for a tokened endpoint

# 3) screen a batch
curl -s -X POST localhost:8080/api/triage/screen -H 'Content-Type: application/json' -d '{
  "items": [
    {"id": "ad1", "text": "Great job in Dubai! Just pay the placement fee of 120,000 pesos."},
    {"id": "ad2", "text": "Hiring a barista, PHP 610/day, SSS + PhilHealth."}
  ]
}'
# GET /api/triage/status reports which tiers are configured.
```

Because the transport is plain OpenAI-compatible chat completions, the same
endpoint also plugs into `kaggle/03-universal-llm-benchmark` (arbitrary
endpoint comparison) and the harness-lift generation scripts with zero code
changes — only configuration.

## Pending GPU verification (explicitly not claimed)

- **In-process loading.** `Gemma4Runtime.load()` uses the Unsloth
  FastModel autoregressive path; DiffusionGemma needs diffusion sampling
  (bidirectional attention denoising), which Unsloth supports per the
  release notes but which we have NOT run. Until a Kaggle/local GPU run
  proves it, DiffusionGemma is endpoint-served only and is deliberately
  NOT in the kernel's `variants.py` picker (an unloadable picker entry
  would violate real-not-faked).
- **Actual screening quality.** The flag/clear accuracy of DiffusionGemma
  on DueCare's prompts is unmeasured. The calibration plan: run the
  fast-tier verdicts against the deep model's analysis on the same
  escalation set (the triage spec's `comparison` field describes this) and
  tune `clear_threshold` from the disagreement rate.
- **Measured throughput.** Replace the arithmetic above with
  `measured_items_per_min` from a real run.

## Why this is the right shape (and not a bigger one)

The alternative designs were considered and rejected for now:

- **DiffusionGemma as a chat/answering model** — rejected: quality below
  standard Gemma 4 on a surface where workers read the output is the wrong
  tradeoff, full stop.
- **A variants.py picker entry today** — rejected: the in-process load
  path is unverified; the picker must never offer a model the kernel
  cannot actually load.
- **Draft-then-polish (fast model drafts envelopes, Gemma 4 polishes)** —
  plausible second seat (the safe-text polish loop already does two-pass
  critique/rewrite), but it changes user-visible text quality, so it needs
  the calibration data first. Tracked as follow-up, not built.
