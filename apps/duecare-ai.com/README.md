# DueCare AI public hub

**Public coordination for safer DueCare deployments.**

This is the public website and coordination service for **duecare-ai.com**. It is intentionally lightweight and CPU-only: it does **not** load Gemma 4 directly. Kaggle/local/edge deployments run Gemma 4; this hub coordinates anonymized updates around it.

## Public URLs and responsibilities

| Surface | URL | Responsibility |
|---|---|---|
| Main server website / public hub | https://duecare-ai.com/ | Render-hosted FastAPI app from this folder. It serves the public product website, hub APIs, knowledge-pack metadata, anonymized signal intake, and consent-aware submission flows. |
| Read-only continuity preview | https://tayloramareltech.github.io/duecare-ai-site/ | Backend-free GitHub Pages export from the same templates. It preserves public pages and allowlisted snapshots while visibly disabling submissions, accounts, automation, and mutable APIs. It does not own production DNS while Render remains active. |
| GitHub source repo | https://github.com/TaylorAmarelTech/gemma4_comp | Monorepo source of truth for packages, Kaggle kernels, docs, validation scripts, GitHub Actions, and this Render app. |
| GitHub Pages docs | https://tayloramareltech.github.io/gemma4_comp/ | Static MkDocs site generated from `docs/`. It is for onboarding, install docs, architecture, reproducibility, and judge/reviewer documentation; it is not the API server. |

## Monorepo source of truth

Active website development now happens inside the main Gemma 4 / Duecare monorepo:

```text
gemma4_comp/apps/duecare-ai.com/
```

Render should be connected to the monorepo repository, not the earlier standalone website repo:

```text
Repo:           TaylorAmarelTech/gemma4_comp
Branch:         master
Root directory: apps/duecare-ai.com
Runtime:        Docker
Health check:   /api/health
```

The monorepo root `render.yaml` is the authoritative Render blueprint.

## What the hub does

- Accepts anonymized or aggregate safety-pattern signals.
- Rejects obvious raw PII in free-text summaries.
- Accepts client submissions with explicit visibility, attribution, label-source, and consent controls.
- Lists Duecare knowledge-pack metadata for RAG, GREP, contacts, rubrics, examples, tools, and jurisdictions.
- Accepts public-source crawler-style update proposals for curator review.
- Supports an operator-side local knowledge-base API for files that should stay tenant-local.
- Persists signals and proposals to a Render persistent disk using JSONL files.
- Serves human-readable documentation at `/docs` and interactive OpenAPI docs at `/api-docs`.

## Sensitive data handling

Do **not** use this service as a raw case-management system. Raw worker cases stay local with workers, NGOs, regulators, platforms, or trusted caseworkers unless explicit consent and anonymization gates are in place.

Canonical data rule:

> Raw worker chats, case files, IDs, contact details, and private documents stay on the worker device or trusted NGO hardware unless an authorized user explicitly creates a sanitized submission. Sensitive PII is anonymized by the local Gemma 4 workflow before anything is submitted to the public hub. The server runs a second PII detector that rejects raw-PII submissions before storage and redacts detector-class PII in admin/debug views.

Submission metadata is client-controlled. Anonymous submissions cannot include organization or submitter-attribution fields, and `local_only` objects are rejected because they should never leave the client. Automatic labels may be stored as suggestions with source and confidence metadata, but they do not silently upgrade an anonymous submission into an attributed one.

## API surface

```text
GET  /                         Public project homepage
GET  /components                Architecture component map
GET  /use-cases                 Deployment stories
GET  /training-data-flywheel    Harness-to-dataset and fine-tuning release path
GET  /project-status             Public continuity, release boundary, and maintainer handoff
GET  /grep-rules                Rule-category explainer
GET  /tools                     Draft-only tool catalog
GET  /context                   Context by corridor/jurisdiction
GET  /dashboard                 Operational live hub dashboard
GET  /api/health               Render health check + file-store check
GET  /healthz                  Health alias
GET  /api/hub/status           Service status, privacy mode, counters
GET  /api/hub/knowledge-packs  Knowledge-pack metadata
GET  /api/hub/trends           Aggregate trend counters
POST /api/hub/signals          Anonymized pattern signal intake
POST /api/hub/opencrawl/updates Public-source update proposal intake
GET  /api/hub/opencrawl/updates Curator review feed
POST /api/hub/client/submissions Sanitized client submission intake with label/consent envelope
POST /api/hub/client/retractions Retraction request intake
GET  /api/local-kb/entries     Operator-side local KB entries
POST /api/local-kb/entries     Operator-side local KB insert
DELETE /api/local-kb/entries/{entry_id} Operator-side local KB delete
GET  /api/admin/logs           Token-gated redacted operational logs
GET  /docs                     Human-readable project docs
GET  /api-docs                 Interactive OpenAPI docs
GET  /openapi.json             OpenAPI schema
```

## Local run

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## Test

```bash
python -m pytest -q
```

## Static continuity build

The separate `TaylorAmarelTech/duecare-ai-site` repository publishes a
read-only Pages preview without changing the Render service or `duecare-ai.com`
DNS. Build and validate the exact preview locally with:

```powershell
python scripts/export_static.py --out dist-fallback --fallback `
  --base-path /duecare-ai-site `
  --site-url https://tayloramareltech.github.io/duecare-ai-site `
  --omit-cname
python scripts/validate_static_fallback.py --site dist-fallback `
  --base-path /duecare-ai-site `
  --site-url https://tayloramareltech.github.io/duecare-ai-site
```

The fallback uses an isolated empty hub store, five checksum-bound public
snapshots, an early API-blocking script, disabled state-changing controls, and
a custom 404. See [DEPLOY_STATIC.md](DEPLOY_STATIC.md) for the domain-cutover
and rollback gate. The live Render build remains the only mutable/API surface.

## Local smoke test

After starting the app, verify the core public routes and API contracts:

```bash
python scripts/smoke_duecare_ai.py --base-url http://127.0.0.1:8000
```

The smoke script checks health, status, knowledge packs, trends, public pages, CORS preflight behavior, and negative privacy cases.

## Render deployment

Use Docker runtime with a 1 GB persistent disk:

```text
Service:       duecare-ai-hub
Runtime:       Docker
Repo:          TaylorAmarelTech/gemma4_comp
Branch:        master
Root dir:      apps/duecare-ai.com
Health check:  /api/health
Disk mount:    /app/.duecare
Domain:        duecare-ai.com and www.duecare-ai.com
```

The authoritative blueprint is the monorepo root [render.yaml](../../render.yaml).

Detailed setup docs:

- [Render deployment notes](docs/RENDER.md)
- [Domain and Cloudflare setup](docs/DOMAIN_SETUP.md)
- [Claude website setup prompt](docs/CLAUDE_WEBSITE_SETUP_PROMPT.md)

## Required environment variables

```text
DUECARE_ENV=production
DUECARE_PRIVACY_MODE=anonymized_signals_only_no_raw_pii
DUECARE_STORAGE=file
DUECARE_DATA_DIR=/app/.duecare
PORT=10000
DUECARE_CORS_ALLOW_ORIGINS=https://duecare-ai.com,https://www.duecare-ai.com
```

No API keys are required for the initial public hub.

## DNS checklist

1. Create the Render web service from this public GitHub repo.
2. Add custom domains in Render:
   - `duecare-ai.com`
   - `www.duecare-ai.com`
3. Add the DNS records Render provides at the domain registrar.
4. Wait for Render certificate issuance.
5. Smoke-test:
   - `https://duecare-ai.com/api/health`
   - `https://duecare-ai.com/api/hub/status`
   - `https://duecare-ai.com/api/hub/knowledge-packs`
   - `https://duecare-ai.com/docs`
   - `https://duecare-ai.com/api-docs`

## Relationship to the Gemma 4 submission

- Kaggle proves the Gemma 4 model + harness behavior.
- `duecare-ai.com` proves the public coordination layer.
- Local/mobile deployments keep sensitive cases private.
- The hub only exchanges anonymized patterns, public-source proposals, prompts, evaluation manifests, and vetted knowledge-pack metadata.
