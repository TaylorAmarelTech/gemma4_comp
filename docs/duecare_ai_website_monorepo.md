# duecare-ai.com in the gemma4_comp monorepo

The public website source of truth now lives in this repository at:

```text
apps/duecare-ai.com/
```

The earlier standalone website repository still exists for history, but active development should happen in the monorepo:

```text
https://github.com/TaylorAmarelTech/duecare-ai.com
```

## Why combine now

Combining a copy into the monorepo gives website work direct access to the same docs, architecture, package names, benchmark language, and submission context as the Kaggle/Gemma 4 codebase.

## Render monorepo deployment

The repository root includes the authoritative Render blueprint:

```text
render.yaml
```

It deploys only the website folder by using:

```text
rootDir: apps/duecare-ai.com
```

Target service settings:

```text
Repository:    TaylorAmarelTech/gemma4_comp
Branch:        master
Service:       duecare-ai-hub
Runtime:       Docker
Root Dir:      apps/duecare-ai.com
Dockerfile:    ./Dockerfile
Health check:  /api/health
Disk mount:    /app/.duecare
Domain:        duecare-ai.com and www.duecare-ai.com
```

## Important distinction

Render's `rootDir` makes Render build only the website folder. It does not hide the rest of a public GitHub repository. If this entire monorepo is public, the entire monorepo is visible.

## Cutover plan

In Render, update the existing `duecare-ai-hub` service or create a replacement service with these settings:

```text
Repo:            https://github.com/TaylorAmarelTech/gemma4_comp
Branch:          master
Root Directory:  apps/duecare-ai.com
Runtime:         Docker
Dockerfile Path: ./Dockerfile
Health Check:    /api/health
Auto Deploy:     Yes
```

Keep the same environment variables and disk:

```text
DUECARE_ENV=production
DUECARE_PRIVACY_MODE=anonymized_signals_only_no_raw_pii
DUECARE_STORAGE=file
DUECARE_DATA_DIR=/app/.duecare
PORT=10000

Disk name:       duecare-ai-data
Disk mount path: /app/.duecare
Disk size:       1 GB
```

After the monorepo service passes smoke tests, attach or move the domains:

```text
duecare-ai.com
www.duecare-ai.com
```

If Render does not allow changing the Git repository on the existing service, create a second Web Service from the monorepo, smoke-test its `*.onrender.com` URL, then remove the custom domains from the old service and attach them to the new service. Persistent disks are service-scoped, so export any JSONL files first if the old disk contains data worth preserving.

Do not put Cloudflare, Render, provider, or analytics API keys in repo files.

## Local test command

From the monorepo root:

```powershell
.venv/Scripts/python.exe -m pytest apps/duecare-ai.com/tests -q
```
