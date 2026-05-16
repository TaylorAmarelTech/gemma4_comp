# DueCare deployment surfaces

This folder contains deployment examples for the active DueCare submission surfaces. Treat these as runnable starting points or integration adapters, not as proof that every roadmap surface is production-certified.

## Validated local/private compose path

The current private deployment path is the root-level `docker-compose.enterprise.yml` stack:

```powershell
copy .env.enterprise.example .env.enterprise
# edit .env.enterprise and replace every placeholder secret

docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml config
docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml up --build -d
```

Validated checks as of 2026-05-10:

```powershell
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml config
docker compose --env-file .env.enterprise.example -f docker-compose.enterprise.yml --profile monitoring config
```

The stack runs the checked-in `duecare serve` FastAPI surface behind Nginx and uses `/healthz` for health checks.

## Files

| Path | Purpose | Status |
|---|---|---|
| `docker/api.Dockerfile` | Builds the DueCare API/server image from local workspace packages. | Compose-config validated |
| `nginx/nginx.enterprise.conf` | Local HTTP reverse proxy with security headers and TLS guidance. | Compose-config validated |
| `monitoring/prometheus.yml` | Optional Prometheus scrape config. | YAML validated |
| `monitoring/alert-rules.yml` | Starter API-down alert. | YAML validated |
| `monitoring/grafana/` | Optional Grafana datasource/dashboard provisioning. | YAML/JSON validated |
| `browser_extension/` | Browser-extension integration surface. | Keep as integration/demo surface unless freshly validated |
| `telegram_bot/`, `discord_bot/` | Messaging-channel adapters. | Keep as integration/demo surfaces unless freshly validated |

The older generic `hf_spaces/` notes were moved to `_archive/cleanup-2026-05-10/deployment_hf_spaces/`. Active Hugging Face Space bundles remain at the repo root:

- `hf_space/` — Harness Chat Space.
- `hf-space/` — Live Demo Space.

## Secrets and privacy

Never commit `.env.enterprise`. The trackable file is `.env.enterprise.example` only.

Raw worker chats, IDs, contact details, and private documents stay inside the local/private deployment unless the operator explicitly creates an authorized sanitized export.

## Hardware guidance

| Mode | Minimum | Recommended | Notes |
|---|---:|---:|---|
| CLI/server smoke test | Python 3.11+, 4 GB RAM | Python 3.11/3.12, 8 GB RAM | Uses lightweight local checks and bundled examples. |
| Local private compose | Docker, 8 GB RAM, 10 GB disk | 16 GB RAM, 20+ GB disk | Add model cache/storage separately if running local inference. |
| GPU local inference | NVIDIA GPU optional | 16+ GB VRAM for larger models | Depends on chosen backend and quantization. |
| Mobile LiteRT | Roadmap unless linked to a validated sibling build | Device-specific | Do not claim runnable from this repo without a validated artifact. |

## Roadmap boundaries

Kubernetes/Helm, SSO/SAML, browser extension, mobile LiteRT, and messaging-channel deployments may exist as examples or roadmap material. Before presenting any of them as submission-ready, run a fresh validation and document the exact command/result.

For non-Docker launch options such as `pipx`, offline wheelhouses, EC2 AMIs, and marketplace images, see `docs/launch_packaging_options.md`.
