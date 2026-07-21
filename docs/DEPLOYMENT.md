# DueCare deployment guide

Copy-paste instructions for running DueCare yourself: on a laptop with
Docker, on a Kubernetes cluster, or on managed hosting. Everything here
maps to files that already exist in this repository -- no extra glue.

## Two servers, pick what you need

DueCare ships two runnable server images. They are different surfaces;
know which one you want.

| Server | Image source | Port | Health | Entry point | What it is |
|---|---|---|---|---|---|
| **Interactive workbench + classifier** | root `Dockerfile` -> `duecare-llm:latest` | 8080 (classifier 8081) | `/healthz` | `python -m duecare.chat.run_server` | The reviewer workbench / chat kernel: chat, bulk file review, extraction, search, knowledge tools. Talks to a local Gemma via Ollama. |
| **AI hub (central knowledge server + website)** | `apps/duecare-ai.com/Dockerfile` -> `duecare-ai-hub` | 10000 | `/api/health` | `uvicorn app.main:app` | The public site at duecare-ai.com and the central server that **receives knowledge submissions** (`POST /api/submit/knowledge`) and serves vetted packs. File storage, no model required. |

The Kubernetes manifests and `render.yaml` below deploy the **hub**. The
Docker Compose files below run the **workbench** locally.

---

## Local: run the workbench with Docker Compose

The fastest way to see DueCare running against a local Gemma 4. Requires
Docker (and Docker Compose v2). First boot pulls the `gemma4:e2b` Ollama
model (~1.5 GB).

```bash
# From the repo root:
docker compose up            # chat 8080 + classifier 8081 + ollama 11434
docker compose up -d         # detached
docker compose logs -f       # tail logs
docker compose down -v       # stop and drop volumes (clears the model cache)
```

Then open:

- Workbench chat: <http://localhost:8080>
- Classifier API: <http://localhost:8081> (`POST /api/classifier/evaluate`)
- Health check: <http://localhost:8080/healthz>

Pick a different model by setting `DUECARE_OLLAMA_MODEL` in a repo-root
`.env` (`gemma4:e2b` default ~1.5 GB, `gemma4:e4b` ~3.5 GB for 16 GB+ RAM,
`gemma3:1b` fastest). GPU acceleration: uncomment the NVIDIA `deploy`
block under the `ollama` service in `docker-compose.yml`.

### Compose modes

| Mode | Command | Front door | Notes |
|---|---|---|---|
| **Default** | `docker compose up` | 8080 | Workbench + classifier + Ollama. |
| **Dev (hot reload)** | `docker compose -f docker-compose.dev.yml up` | 8080 | Bind-mounts the repo; source changes reload. `exec dev pytest -x` to run tests in-container. |
| **Enterprise (private stack)** | see below | 8088 | FastAPI behind Nginx + PostgreSQL + Redis, optional Prometheus/Grafana. |
| **Auth overlay** | `docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d` | 4180 | Puts oauth2-proxy (any OIDC provider) in front; the chat port stops binding to the host. |

**Enterprise stack** is tied to files in this repo (`deployment/docker/api.Dockerfile`,
`deployment/nginx/`, `deployment/monitoring/`):

```bash
copy .env.enterprise.example .env.enterprise
# edit .env.enterprise and replace every placeholder secret

docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml config          # validate
docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml up --build -d    # run
# optional monitoring (Prometheus + Grafana):
docker compose --env-file .env.enterprise -f docker-compose.enterprise.yml --profile monitoring up --build -d
```

Never commit `.env.enterprise`. The only tracked file is
`.env.enterprise.example`. Raw worker chats, IDs, contact details, and
private documents stay inside this private stack unless an operator makes
an authorized sanitized export.

---

## The hub: run the central knowledge server

The hub (`apps/duecare-ai.com`) is the public website and the server that
receives knowledge submissions. It is a plain FastAPI file-store app --
no model, no database.

Run it standalone with Docker:

```bash
docker build -t duecare-ai-hub:latest apps/duecare-ai.com
docker run --rm -p 10000:10000 \
  -e DUECARE_ENV=production \
  -e DUECARE_STORAGE=file \
  -e DUECARE_DATA_DIR=/app/.duecare \
  -e PORT=10000 \
  -v duecare_hub_data:/app/.duecare \
  duecare-ai-hub:latest

curl -fsS http://127.0.0.1:10000/api/health
# -> {"status":"ok","service":"duecare-ai-hub","storage":"file", ...}
```

### Hub environment variables

| Variable | Default (Dockerfile / render.yaml) | Purpose |
|---|---|---|
| `PORT` | `10000` | Port uvicorn binds. |
| `DUECARE_DATA_DIR` | `/app/.duecare` | Root of the file store (mount a volume here to persist). |
| `DUECARE_STORAGE` | `file` | Storage backend (file store). |
| `DUECARE_ENV` | `production` | Environment label. |
| `DUECARE_PRIVACY_MODE` | `anonymized_signals_only_no_raw_pii` | Privacy posture label surfaced by the API. |
| `DUECARE_ADMIN_TOKEN` / `DUECARE_HUB_ADMIN_TOKEN` | (unset) | Optional curator/admin token for privileged hub actions. |
| `DUECARE_PEERS` | (built-in peers only) | Federation allowlist: `name=https://host` entries, comma-separated. Also the outbound allowlist for sync/submit. |
| `DUECARE_NODE_ID` | `kernel-01` | Node identity stamped into knowledge `provenance.created_by`. |

`HF_TOKEN` is **not** used by the hub -- it only applies to deployments
that load a Hugging Face model (the workbench with a HF backend, or the
Kaggle kernels). The hub is file storage only.

---

## Cluster: Kubernetes

Real, validated manifests for the hub live in
[`deployment/k8s/`](../deployment/k8s/): a Deployment (readiness +
liveness on `/api/health`, container port 10000), a ClusterIP Service, an
Ingress (host + TLS placeholders), and a ConfigMap for the `DUECARE_*`
env.

```bash
# Build + push the image, edit the placeholders, then:
kubectl apply -f deployment/k8s/
kubectl rollout status deployment/duecare-ai-hub
```

Full walkthrough (placeholders, PVC for durable storage, secrets):
[`deployment/k8s/README.md`](../deployment/k8s/README.md).

---

## Managed: Render

`render.yaml` at the repo root deploys the hub image on Render as
`duecare-ai-hub`: Docker runtime, `rootDir: apps/duecare-ai.com`,
health check `/api/health`, a 1 GB persistent disk mounted at
`/app/.duecare`, and the `DUECARE_*` env already wired. Connect the repo
in Render and it deploys on green checks.

---

## Health checks at a glance

| Server | URL | Expected |
|---|---|---|
| Workbench / classifier | `http://<host>:8080/healthz` | `{"status":"ok", ...}` |
| Enterprise (via Nginx) | `http://<host>:8088/healthz` | proxied to the API `/healthz` |
| Hub | `http://<host>:10000/api/health` | `{"status":"ok","service":"duecare-ai-hub", ...}` |

---

## Contribute knowledge to a running hub

Once a hub is up, contribute detection rules, grounding docs, and facts
to it with the worked example in
[`examples/contribute_knowledge/`](../examples/contribute_knowledge/):
build a KnowledgeObject v1.0 envelope, validate it, and
`POST /api/submit/knowledge`. The hub validates the shape, re-gates for
PII, deduplicates, and stages the item for curator review.

```bash
cd examples/contribute_knowledge
python submit_knowledge.py --dry-run                       # validate only
DUECARE_HUB_URL=http://127.0.0.1:10000 python submit_knowledge.py   # send to a local hub
```

---

## Related deployment docs

- Deployment topologies + hardware sizing: [`docs/deployment_topologies.md`](deployment_topologies.md)
- Runnable topology examples: [`examples/deployment/`](../examples/deployment/)
- Cloud cookbook (multiple platforms): [`docs/cloud_deployment.md`](cloud_deployment.md)
- Application deployment modes (platform / worker / NGO): [`docs/deployment_modes.md`](deployment_modes.md)
- Enterprise concerns (SSO, audit, RBAC): [`docs/deployment_enterprise.md`](deployment_enterprise.md)
- Embedding DueCare in your own app: [`docs/embedding_guide.md`](embedding_guide.md)
- Non-Docker packaging (pipx, wheelhouse, AMIs): [`docs/launch_packaging_options.md`](launch_packaging_options.md)