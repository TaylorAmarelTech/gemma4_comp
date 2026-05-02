---
title: Duecare Live Demo
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8080
pinned: true
license: mit
short_description: Migrant-worker safety harness wrapping Gemma 4
suggested_storage: small
suggested_hardware: t4-small
preload_from_hub:
  - google/gemma-4-e4b-it
hf_oauth: false
---

# Duecare — Live Demo on HF Spaces

The user-facing live URL judges click. Migrant-worker safety harness
wrapping Gemma 4 (Persona / GREP / RAG / Tools), permanent-URL
edition.

> Built with Google's Gemma 4 (base model:
> [google/gemma-4-e4b-it](https://huggingface.co/google/gemma-4-e4b-it)).
> Used in accordance with the
> [Gemma Terms of Use](https://ai.google.dev/gemma/terms).

## What this Space replaces

The same demo also runs on Kaggle as
[`taylorsamarel/duecare-live-demo`](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)
behind a transient cloudflared quick-tunnel that disappears when the
Kaggle session times out. **This Space is the permanent URL** judges
can bookmark.

## How to deploy

```bash
# 1. Clone this directory + create a private HF Space
huggingface-cli login   # need write scope

# 2. Create the Space (one-time)
hf-space-cli create taylorscottamarel/duecare-live-demo \
  --type docker --hardware t4-small --private

# 3. Push
git remote add hf https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo
git push hf main

# 4. Set HF_TOKEN secret in the Space settings (write scope)

# 5. Wait for build (~10 min: pip install + Chromium + Gemma cache)

# Demo URL appears at:
# https://huggingface.co/spaces/taylorscottamarel/duecare-live-demo
```

## Hardware

- **t4-small** (free tier eligible) — fits Gemma 4 E4B at 4-bit
- **t4-medium** — required for 26B-A4B
- **a10g-large** — required for 31B (recommended for the polished demo)

Bump via the Space's Settings → Hardware.

## What's inside

```
hf-space/
├── README.md           ← this file (also the Space README)
├── Dockerfile          ← multi-stage: install + cache Gemma + run
├── space.yml           ← HF Space metadata
├── start.sh            ← entry script (uvicorn the chat app on port 8080)
└── DEPLOYMENT.md       ← runbook for the user
```

## Cost estimate

- t4-small: free for the first 2 GPU-hours/day, then $0.40/GPU-hour
- t4-medium: $0.60/hour
- a10g-large: $3.15/hour

For the hackathon demo period (assume ~50 hours of judge usage over 7 days):
- t4-small: ~$0 if usage stays under daily quota, else ~$20 total
- a10g-large: ~$155 total

Recommendation: **start with t4-small + E4B** for the hackathon
window; bump to a10g for any post-judging promotion.

## Differences vs the Kaggle live-demo notebook

| Feature | Kaggle | HF Space |
|---|---|---|
| Public URL | transient cloudflared `*.trycloudflare.com` | permanent `huggingface.co/spaces/<owner>/duecare-live-demo` |
| Cold start | every notebook session (~30 sec on E4B, ~3 min on 31B) | once at deploy; warm 24/7 if hardware is on |
| Persistent storage | none (notebook artifacts lost between runs) | Spaces persistent disk (audit log + history) |
| Cost | free | free tier or $0.40-$3.15/hr depending on tier |
| Credits attribution | Kaggle handle visible | HF handle visible |
| Cloudflared dependency | yes (auto-download every cold start) | no (HF handles HTTPS termination) |
| Suitable for the rubric video | yes (cloudflared works during recording) | better (no risk of session expiry mid-shot) |

For the hackathon submission writeup link to **both** URLs.

## Privacy posture (unchanged from local)

- All inference is in-process (no telemetry, no model-call logging)
- `HF_TOKEN` is the only secret needed (for Gemma 4 model download)
- BYOK keys (Tavily/Brave/Serper for the agentic appendix) live ONLY
  in the user's browser localStorage; never persisted server-side
- The audit log records only sha256(query) for outbound web research
  calls (not plaintext queries)

The Space is **public read** but the underlying chat does **not**
log per-user content beyond the agentic-research audit hashes.
