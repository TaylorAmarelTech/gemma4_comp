# Render deployment notes for duecare-ai.com

This deployment copies the useful parts of the PathNav recipe while staying smaller and safer for the Duecare AI hackathon window.

## Architecture

```text
Render Web Service (Docker, FastAPI)
  /app
  ├── app/main.py
  ├── /app/.duecare  ← Render persistent disk
  └── JSONL file store

Talks to:
  ├── public browsers
  ├── partner systems posting anonymized signals
  ├── OpenClaw/OpenCrawl-style public-source crawlers
  └── curator workflows that review proposed pack changes
```

## Durable choices copied from PathNav

1. **File storage on a persistent disk, not a database.**
   The hub is a single-instance Render service with a mounted volume at `/app/.duecare`. It stores append-only JSONL files for anonymized signals and public-source update proposals.

2. **One process, no worker service yet.**
   This version has no recurring jobs. A future inline worker can run freshness checks for public contact URLs without adding another service.

3. **No model inference on Render.**
   Gemma 4 runs in Kaggle, local llama.cpp/Ollama, HF Spaces, edge boxes, or mobile. Render hosts only the coordination plane.

## Render settings

```text
Type:           Web Service
Runtime:        Docker
Region:         Oregon
Plan:           Starter for production
Repository:     TaylorAmarelTech/gemma4_comp
Branch:         master
Root directory: apps/duecare-ai.com
Dockerfile:     ./Dockerfile
Health check:   /api/health
Auto-deploy:    Yes, on push to master
Persistent disk:
  Mount path:   /app/.duecare
  Size:         1 GB
```

## Environment variables

```text
DUECARE_ENV=production
DUECARE_PRIVACY_MODE=anonymized_signals_only_no_raw_pii
DUECARE_STORAGE=file
DUECARE_DATA_DIR=/app/.duecare
PORT=10000
```

No Stripe, Resend, Sentry, PostHog, or AI-provider keys are needed for this first hub release.

## First deploy checklist

1. Create or update a Render Web Service from `TaylorAmarelTech/gemma4_comp`.
2. Use Docker runtime.
3. Set branch to `master`.
4. Set root directory to `apps/duecare-ai.com`.
5. Set Dockerfile path to `./Dockerfile`.
6. Add a persistent disk mounted at `/app/.duecare`.
7. Set health check path to `/api/health`.
8. Add custom domains:
   - `duecare-ai.com`
   - `www.duecare-ai.com`
9. Configure DNS using Render's records.
10. Confirm TLS certificate issuance.
11. Smoke-test the public endpoints.

## Smoke checks

```text
GET https://duecare-ai.com/api/health
GET https://duecare-ai.com/api/hub/status
GET https://duecare-ai.com/api/hub/knowledge-packs
GET https://duecare-ai.com/api/hub/trends
GET https://duecare-ai.com/docs
```

## What not to add before submission

- Raw case intake.
- Auto-sending emails or complaints.
- Twilio/Messenger/WhatsApp dependencies.
- GPU inference.
- Stripe or login flows.
- Multi-service worker topology.

Those can wait. The submission needs a visible, safe, working public coordination hub.
