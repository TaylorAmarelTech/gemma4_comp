# Topology C — server + thin clients (the hosted-SaaS shape)

One Duecare server in the cloud. Many thin clients (Android, web,
Telegram, Messenger, WhatsApp, CLI, custom apps) all talk to the same
backend.

```
                ┌───────────────── cloud server ─────────────────┐
                │                                                │
                │   FastAPI + GREP + RAG + tools + research      │
                │   + Gemma 4 (Ollama or vLLM)                   │
                │   + evidence-db (Postgres)                     │
                │                                                │
                │   POST /chat                                   │
                │   POST /research                               │
                │   POST /pipeline                               │
                │   POST /classify                               │
                │   GET  /docs                                   │
                └────────────────────────────────────────────────┘
                          ↑
        ┌──────┬──────┬───┴─────┬──────┬──────┬──────┐
        │      │      │         │      │      │      │
   Android  React  WhatsApp  Telegram  iOS    CLI    NGO
   app     widget   bot       bot                    website
```

## Step 1 — Deploy the server

You already have a Duecare server. Pick one of:

| Quickest | Production-ready |
|---|---|
| [Hugging Face Spaces](#hf-spaces-5-min) | [Render](#render-15-min) |
| [Railway](#railway-5-min) | [Cloud Run / EKS / GKE](#enterprise-clouds-15-30-min) |
| [Fly.io](#flyio-10-min) | [Self-hosted Docker on a VPS](#vps-30-min) |

Full cookbook for all 13 platforms: [`docs/cloud_deployment.md`](../../../docs/cloud_deployment.md).

### HF Spaces (5 min)

```bash
huggingface-cli login

curl -X POST https://huggingface.co/api/repos/create \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-duecare-server","type":"space","private":false,"sdk":"docker"}'

cd hf-space/
git remote add space https://huggingface.co/spaces/$HF_USER/my-duecare-server
git push space main
```

Your server URL: `https://$HF_USER-my-duecare-server.hf.space`.

### Render (15 min)

```bash
# infra/render/render.yaml is ready to use
git push origin main
# then in the Render dashboard: New → Blueprint → point at this repo
```

Your server URL: `https://duecare-llm.onrender.com`.

### Railway (5 min)

```bash
railway login
railway init
railway up
```

### Fly.io (10 min)

```bash
flyctl launch --name duecare --copy-config infra/fly/fly.toml
flyctl deploy
```

### Enterprise clouds (15-30 min)

- Cloud Run: `infra/gcp/cloudrun-deploy.sh`
- GKE Autopilot: `infra/gke/gke-autopilot-deploy.sh`
- EKS (Helm): `infra/eks/eksctl-cluster.yaml` + `infra/helm/duecare/`
- AKS: `infra/aks/aks-deploy.sh`
- Azure Container Apps: `infra/azure/containerapp-deploy.sh`

### VPS (30 min)

Any $5/mo VPS with Docker:

```bash
# On the VPS:
docker run -d --restart unless-stopped --name duecare \
  -p 80:8000 \
  -e DUECARE_BACKEND=ollama \
  -e OLLAMA_HOST=http://localhost:11434 \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  ghcr.io/tayloramareltech/duecare-llm:latest
```

(Run Ollama on the same VPS, or use a managed inference endpoint like
Together AI / OpenRouter / Hugging Face Inference Endpoint.)

## Step 2 — Point your clients at it

Once the server is live at, say, `https://duecare.your-ngo.org`:

### Client A — Android (Duecare Journey app)

Settings → Cloud model:
- Format: **OpenAI-compatible**
- Endpoint URL: `https://duecare.your-ngo.org`
- Model name: `gemma4:e2b`
- API key: (your auth token, if you put auth in front of `/chat`)

Sample env file: [`./android-config-example.env`](./android-config-example.env)

### Client B — React widget on an NGO website

```html
<div id="duecare"></div>
<script type="module">
  import {DuecareChat} from
    "https://cdn.jsdelivr.net/npm/@tayloramareltech/duecare-react/dist/index.js";
  ReactDOM.render(
    <DuecareChat apiUrl="https://duecare.your-ngo.org" />,
    document.getElementById("duecare")
  );
</script>
```

Full example: [`examples/embedding/react-component/`](../../embedding/react-component/).

### Client C — Vanilla JS widget (any HTML page)

```html
<script src="https://duecare.your-ngo.org/widget.js"></script>
<script>
  Duecare.mount(document.getElementById("chat"), {
    apiUrl: "https://duecare.your-ngo.org",
    persona: "ngo-frontline"
  });
</script>
```

Full example: [`examples/embedding/web-widget/`](../../embedding/web-widget/).

### Client D — Telegram bot

```bash
cd examples/embedding/telegram-bot
cp .env.example .env
# DUECARE_API_URL=https://duecare.your-ngo.org
# TELEGRAM_BOT_TOKEN=...
python bot.py
```

Full example: [`examples/embedding/telegram-bot/`](../../embedding/telegram-bot/).

### Client E — Facebook Messenger (NGO Page)

```bash
cd examples/embedding/messenger-bot
cp .env.example .env
# DUECARE_API_URL=https://duecare.your-ngo.org
# PAGE_ACCESS_TOKEN=...
# VERIFY_TOKEN=...
python bot.py
```

Full example: [`examples/embedding/messenger-bot/`](../../embedding/messenger-bot/).

### Client F — WhatsApp Business (Cloud API)

```bash
cd examples/embedding/whatsapp-cloud-api
cp .env.example .env
# DUECARE_API_URL=https://duecare.your-ngo.org
# WHATSAPP_ACCESS_TOKEN=...
python bot.py
```

Full example: [`examples/embedding/whatsapp-cloud-api/`](../../embedding/whatsapp-cloud-api/).

### Client G — CLI

```bash
# Use the local-cli example but point Ollama-compatible env at your server
OLLAMA_HOST=https://duecare.your-ngo.org \
OLLAMA_MODEL=gemma4:e2b \
python ../local-cli/duecare_cli.py
```

### Client H — curl (any language, any device)

```bash
curl -s -X POST https://duecare.your-ngo.org/chat \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer YOUR_TOKEN' \
  -d '{"message": "Is this fee legal?", "corridor": "PH-HK"}'
```

OpenAPI schema: `https://duecare.your-ngo.org/docs`. Generate
typed clients via `openapi-generator`:

```bash
openapi-generator generate \
  -i https://duecare.your-ngo.org/openapi.json \
  -g python -o ./duecare-client-py
```

## Step 3 — Production hardening

### Auth proxy

The bare server has no auth. In front of it, add:

- **HF Spaces**: configure HF Spaces secrets for an HMAC validator
- **Render / Cloud Run / VPS**: put Cloudflare Access or oauth2-proxy
  in front of `https://duecare.your-ngo.org`
- **Custom**: add a basic-auth middleware to `duecare.server.app`

### Rate limiting

Default request budget per IP is 30/min. Override via the env var
`DUECARE_RATE_LIMIT_PER_MIN=N`. For high-traffic public sites, put a
Cloudflare or AWS WAF rule in front of `/chat`.

### Audit logging

`DUECARE_AUDIT_LOG_PATH=/var/log/duecare/audit.jsonl` — every request,
every model call, every tool invocation written as one JSON line per
event. Plug into your existing SIEM / Grafana / Datadog stack.

### Multi-region

The Duecare image is multi-arch (amd64 + arm64). For low-latency
global serving, deploy to:

- **Fly.io** with `flyctl regions add ord lhr nrt sin` (auto-routes
  by lat/long)
- **Cloud Run multi-region** with HTTPS load balancer
- **CloudFront / Fastly** as a thin geo-cache in front of one origin

## When to NOT use Topology C

- **Strict no-egress requirement** — use [Topology D](https://github.com/TaylorAmarelTech/duecare-journey-android)
  (on-device only) or [Topology B](../ngo-office-edge/) (LAN only).
- **Single user** — overkill; use [Topology A](../local-all-in-one/).
- **NGO with one office** — [Topology B](../ngo-office-edge/) costs
  less and has stronger privacy.
- **Worker who wants Gemma local but needs current legal info** —
  [Topology E](../hybrid-edge-llm-cloud-rag/) (hybrid).

## Going further

- Full cloud cookbook: [`docs/cloud_deployment.md`](../../../docs/cloud_deployment.md)
- Embedding patterns: [`docs/embedding_guide.md`](../../../docs/embedding_guide.md)
- All deployment topologies: [`docs/deployment_topologies.md`](../../../docs/deployment_topologies.md)
