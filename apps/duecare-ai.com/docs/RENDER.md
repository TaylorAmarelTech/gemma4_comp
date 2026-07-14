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
   ├── public-source crawler jobs
  └── curator workflows that review proposed pack changes
```

## Server-automation backend fit

The lightweight PathNav-style backend pattern works for DueCare on Render because the
runtime assumptions match: one Docker web service, a persistent disk, a
public health endpoint, file-backed JSONL state, and optional server-side
automation inside the same FastAPI process. DueCare should not lift the full
71-route surface. It only needs the kit patterns that protect the public
coordination layer without accepting raw case content.

| Backend pattern | DueCare status on Render |
|---|---|
| Storage abstraction | Implemented as `FileHubStore` writing append-only JSONL under `DUECARE_DATA_DIR`; Render disk mounts at `/app/.duecare`. |
| Health probe | Implemented at `/api/health`; Render health check should point there. |
| Public coordination APIs | Implemented under `/api/hub/*` for anonymized signals, pack registry, public-source update proposals, and status. |
| Legacy aliases | Implemented for `/openclaw` and `/api/hub/openclaw/inbound-email`; new clients should use `/server-automation` and `/api/hub/automation/inbound-email`. |
| Server-side automation | Implemented inline via `automation.py`; it vets public-source submissions and rejects raw worker-case content before persistence. |
| Admin diagnostics | Implemented as token-gated `/admin` plus `/api/admin/logs`; all returned records are redacted. |
| Inline recurring worker | Deferred. Useful later for contact freshness checks and pack-health monitoring, but not needed for submission. |
| Peer federation | Deferred and disabled by design. Federation would add attack surface before there is a second trusted hub instance. |
| Auth/session stack | Deferred. The public hub is read-mostly; admin diagnostics use a deployment token rather than user accounts. |
| Redis / distributed queues | Deferred. Single-instance Render plus persistent disk is sufficient for the current demo and judge review. |

## Durable choices copied from PathNav

1. **File storage on a persistent disk, not a database.**
   The hub is a single-instance Render service with a mounted volume at `/app/.duecare`. It stores append-only JSONL files for anonymized signals and public-source update proposals.

2. **One process, no worker service yet.**
   This version has no recurring jobs. A future inline worker can run freshness checks for public contact URLs without adding another service. If added, keep the server-automation shape: one idempotent tick endpoint, a heartbeat endpoint, a persisted queue, and token-gated cron access.

3. **Inline server automation only for public-source triage.**
   The Render service can call a configured text model through `automation.py` to classify public-source update proposals. It must never run raw worker chats or case narratives through a hosted provider.

4. **No worker-facing model inference on Render.**
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
Auto-deploy:    After GitHub checks pass on master (`autoDeployTrigger: checksPass`)
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
DUECARE_ADMIN_TOKEN=<random hex 32, optional but required for /api/admin/logs>
PORT=10000
```

Optional server-automation keys use the `DUECARE_AUTOMATION_*` names. The legacy `OPENCLAW_*` names are still read for backward compatibility, but new Render services should prefer the `DUECARE_AUTOMATION_*` env vars.

No Stripe, Resend, PostHog, peer federation, or user-auth keys are needed for this first hub release. Sentry can be added later, but the no-PII logging rule still applies.

## First deploy checklist

1. Create or update the Render Blueprint from the authoritative root `render.yaml` in `TaylorAmarelTech/gemma4_comp`.
2. Use Docker runtime.
3. Set branch to `master`.
4. Set root directory to `apps/duecare-ai.com`.
5. Set Dockerfile path to `./Dockerfile`.
6. Add a persistent disk mounted at `/app/.duecare`.
7. Set health check path to `/api/health`.
8. Confirm auto-deploy waits for passing GitHub checks.
9. Add custom domains:
   - `duecare-ai.com`
   - `www.duecare-ai.com`
10. Configure DNS using Render's records.
11. Confirm TLS certificate issuance.
12. Smoke-test the public endpoints and confirm `git_commit` matches the deployed revision prefix.

## Smoke checks

```text
GET https://duecare-ai.com/api/health
GET https://duecare-ai.com/api/hub/status
GET https://duecare-ai.com/api/hub/knowledge-packs
GET https://duecare-ai.com/api/hub/packs
GET https://duecare-ai.com/api/hub/trends
GET https://duecare-ai.com/docs       # human-readable docs
GET https://duecare-ai.com/api-docs   # interactive OpenAPI docs
GET https://duecare-ai.com/admin   # page renders; logs require DUECARE_ADMIN_TOKEN
```

## What not to add before submission

- Raw case intake.
- Auto-sending emails or complaints.
- Twilio/Messenger/WhatsApp dependencies.
- GPU inference.
- Stripe or login flows.
- Multi-service worker topology.

Those can wait. The submission needs a visible, safe, working public coordination hub.
