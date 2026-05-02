# Topology A — single-component local

Everything Duecare in one Docker Compose stack. Gemma 4 + GREP + RAG +
tools + internet search, served at `http://localhost`.

```
┌───────────────── docker-compose ──────────────────┐
│                                                   │
│  [ ollama ]  ←  [ duecare ]  ←  [ caddy ]         │
│  gemma4:e2b     FastAPI         reverse proxy     │
│                 + GREP                            │
│                 + RAG                             │
│                 + tools                           │
│                 + research-tools (internet)       │
│                                                   │
└───────────────────────────────────────────────────┘
                       ↑
              http://localhost
```

## Prerequisites

- Docker + Docker Compose v2
- ~10 GB free disk (Gemma 4 E2B INT8 weights + container layers)
- 8 GB RAM minimum, 16 GB recommended

## Run

```bash
cp .env.example .env
# (optional) edit .env to add an internet-search API key

docker compose up
```

Wait ~5 minutes on first run while Ollama pulls Gemma 4 (~1.5 GB).
Subsequent runs are seconds.

Open: **http://localhost**

OpenAPI docs: **http://localhost/docs**

## Try it

```bash
# Plain chat (no journal context)
curl -s -X POST http://localhost/chat \
  -H 'content-type: application/json' \
  -d '{"message": "Is a 50,000 PHP training fee legal for a domestic worker going to Hong Kong?"}'

# Web research (uses Tavily / Brave / Serper if configured, else DuckDuckGo)
curl -s -X POST http://localhost/research \
  -H 'content-type: application/json' \
  -d '{"query": "POEA Memorandum Circular training fee 2025"}'

# Pipeline visualization (which GREP rules + RAG docs + tools matched?)
curl -s -X POST http://localhost/pipeline \
  -H 'content-type: application/json' \
  -d '{"message": "My recruiter takes my passport for safekeeping"}'
```

## Stop

```bash
docker compose down                # keep data
docker compose down --volumes      # also delete journal + model cache
```

## What's in each container

- **`ollama`** — pulls + serves Gemma 4. Runs on CPU by default; if you
  have an NVIDIA GPU + `nvidia-container-toolkit` installed, uncomment
  the `deploy.resources` block in `docker-compose.yml`.
- **`duecare`** — the same FastAPI image we publish to `ghcr.io`.
  Loads the GREP rule pack, the RAG corpus, the tool registry, and the
  research-tools (Tavily / Brave / Serper / DuckDuckGo / Wikipedia).
- **`caddy`** — TLS-ready reverse proxy. Currently configured for
  `http://localhost`. Edit `Caddyfile` to point at a real hostname
  and Caddy will fetch a Let's Encrypt cert automatically.

## Switching models

In `.env`:

```bash
OLLAMA_MODEL=gemma4:e4b   # higher quality, 3.5 GB
# or
OLLAMA_MODEL=gemma3:1b    # fastest, 600 MB
```

Then `docker compose up` again. Ollama will pull the new variant on
first request.

## Adding internet search

By default the harness uses DuckDuckGo HTML scraping (no key, free,
but rate-limited and unstable). For a reliable production setup pick
one of:

| Provider | Free tier | Where to sign up |
|---|---|---|
| **Tavily** (recommended) | 1,000 queries/mo | https://app.tavily.com/sign-in |
| **Brave Search** | 2,000 queries/mo | https://api.search.brave.com/app/keys |
| **Serper** | 2,500 free trial then $5/mo | https://serper.dev |

Drop the key into `.env` and restart. The duecare container picks it
up from env vars.

## Connecting the Android app to this stack

The Duecare Journey Android app v0.6.0+ can route to this stack
instead of using on-device Gemma:

1. Find your machine's LAN IP (e.g. `192.168.1.50`).
2. In the app: **Settings → Cloud model**
3. Format: **Ollama**
4. Endpoint URL: `http://192.168.1.50:11434` (Ollama port — bypasses
   the Duecare harness; for full harness use `http://192.168.1.50/`
   and set format to OpenAI-compatible)
5. Model name: `gemma4:e2b`
6. Save.

The app's chat surface now POSTs to your laptop's stack instead of
running on the phone.

## Privacy posture

Everything runs locally. No telemetry. No outbound traffic except:

- The one-time Ollama model pull from `ollama.com`
- Internet search lookups (only if a worker actually invokes them)

Stop the containers and your data is gone (unless you persist via
volumes — which by default are kept across restarts).

## Going to production

This compose file is suitable for a single laptop / desktop / NAS.
For multi-user production, see:

- [Topology B (NGO-office edge)](../ngo-office-edge/) — same
  stack on a Mac mini / NUC with mDNS.
- [Topology C (cloud server + thin clients)](../server-and-clients/) —
  same image deployed to Render / Cloud Run / EKS.
