---
title: Duecare Harness Chat
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: 21-dim safety harness for Gemma 4 + multi-lingual classifier
tags:
  - gemma-4
  - safety
  - trafficking
  - migrant-workers
  - llm-evaluator
  - hackathon
---

# Duecare — Stable demo URL

> The Gemma 4 safety harness, deployed as an HF Space. Same chat
> package as the Kaggle notebooks, but routed to **cloud Gemma**
> (Gemini API by default) so the Space runs CPU-only without GPU
> quota.

**Live URL:** https://taylorscottamarel-duecare.hf.space (after deploy)

## Why this Space exists

The Kaggle notebooks (`01-duecare-harness-chat`, `02-live-demo`,
appendix) are the primary submission deliverable; they showcase
the full on-device Gemma 4 inference path with the 5-layer harness.
However, Kaggle kernels are **session-bound** — the cloudflared URL
dies when the kernel stops.

This Space provides a **persistent demo URL** for reviewers to hit
anytime during the evaluation window. It runs:

- ✅ Same `duecare-llm-chat` package as the Kaggle kernel
- ✅ Same 21-dim grader, multi-lingual classifier, curator JSONs
- ✅ Same auto-grade chips, layer ablation, baseline gauge
- ❌ **Routes Gemma calls to a cloud provider** (Gemini API +
  optional OpenAI-compat fallback) instead of running Unsloth
  on-device — necessary for CPU-only Space tier.

For the full on-device inference experience (E4B / 31B / abliterated
variants), open the Kaggle notebook.

## Configuration

Environment variables (set via Space → Settings → Variables and Secrets):

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Routes Gemma calls to Gemini 1.5 Flash via Google AI Studio |
| `OPENAI_API_KEY` | No | Fallback provider (any OpenAI-compat endpoint) |
| `OPENAI_BASE_URL` | If using OPENAI_API_KEY | e.g. `https://openrouter.ai/api/v1` |
| `OPENAI_MODEL` | If using OPENAI_API_KEY | e.g. `google/gemma-2-9b-it:free` |
| `BRAVE_API_KEY` | No | Enables Online layer with Brave Search |
| `TAVILY_API_KEY` | No | Enables Online layer with Tavily |
| `DUECARE_GIT_SHA` | No | Pinned to commit SHA at build time |

**Get a Gemini API key:** https://aistudio.google.com/app/apikey
(free tier, 1500 req/day — plenty for demo traffic)

## What works in this Space

- ✅ Chat with all 5 harness toggles (Persona, GREP, RAG, Tools, Online)
- ✅ Auto-grade chips below every response (3 chips: score / indicators / citations)
- ✅ Layer-ablation runner (▸ Run ablation — 4 cards live)
- ✅ All 4 grade modes (Universal, Expert, Evaluator, Combined)
- ✅ Multi-lingual classifier (11 languages, click TL/AR/ES/etc. buttons)
- ✅ Examples library (413 prompts)
- ✅ Curator-block governance (`/api/governance`)
- ✅ One-call audit (`/api/version`)

## What doesn't work in this Space

- ❌ **GPU inference** — no Unsloth FastModel; the cloud provider
  handles inference. Use the Kaggle notebook for on-device E4B/31B.
- ❌ **Multimodal image upload** — Gemini API is text-only on the
  free tier (image upload would require paid tier or HF Inference).
- ❌ **Multiple concurrent users** — HF Space free tier handles
  ~5 RPS. For >50 users, the kernel is the better target.

## Layout

```
hf_space/
├── app.py              # FastAPI entry point — wires create_app() with cloud Gemma
├── Dockerfile          # CPU-only Python 3.11 container
├── requirements.txt    # Pin pip deps
├── README.md           # This file (rendered as the Space landing page)
├── duecare_demo_assets/ # Optional: showcase prompts pinned for the empty state
└── start.sh            # Container entrypoint
```

The chat package itself ships as a wheel from PyPI (`duecare-llm-chat==0.2.0`)
so this Space stays small (<10 MB layer beyond the base Python image).

## Deploy / update

This Space tracks the `master` branch of `gemma4_comp`. When the
chat package wheel is bumped, the Space rebuilds via webhook.

Manual rebuild:

```bash
cd hf_space
huggingface-cli upload taylorscottamarel/duecare . --repo-type=space
```

## See also

- **Source code:** [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp)
- **Full on-device demo:** [Kaggle: duecare-harness-chat](https://www.kaggle.com/code/taylorsamarel/duecare-harness-chat)
- **Architecture:** [docs/component_diagram.md](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/component_diagram.md)
- **Peer review walkthrough:** [docs/FOR_PEER_REVIEW.md](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/FOR_PEER_REVIEW.md)
