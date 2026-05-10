# Duecare AI public hub

**Centralized knowledge. Decentralized privacy.**

This is the public website and coordination service for **duecare-ai.com**. It is intentionally lightweight and CPU-only: it does **not** load Gemma 4 directly. Kaggle/local/edge deployments run Gemma 4; this hub coordinates anonymized updates around it.

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
- Lists Duecare knowledge-pack metadata for RAG, GREP, contacts, rubrics, examples, tools, and jurisdictions.
- Accepts public-source crawler-style update proposals for curator review.
- Persists signals and proposals to a Render persistent disk using JSONL files.
- Exposes public OpenAPI docs at `/docs`.

## Safety boundary

Do **not** use this service as a raw case-management system. Raw worker cases stay local with workers, NGOs, regulators, platforms, or trusted caseworkers unless explicit consent and anonymization gates are in place.

Canonical rule:

> Duecare drafts; the user or trusted caseworker decides. Privacy is non-negotiable.

## API surface

```text
GET  /                         Public project homepage
GET  /components                Architecture component map
GET  /use-cases                 Deployment stories
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
GET  /docs                     OpenAPI docs
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

## Relationship to the Gemma 4 submission

- Kaggle proves the Gemma 4 model + harness behavior.
- `duecare-ai.com` proves the public coordination layer.
- Local/mobile deployments keep sensitive cases private.
- The hub only exchanges anonymized patterns, public-source proposals, prompts, evaluation manifests, and vetted knowledge-pack metadata.
