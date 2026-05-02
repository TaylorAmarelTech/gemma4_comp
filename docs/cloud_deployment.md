# Cloud Deployment

How to run the Duecare chat playground + classifier on every major
cloud, ranked from cheapest/easiest to most-enterprise. Each section
gives the exact command(s) to deploy and where the artifact lives.

> **Common prerequisite:** the multi-arch Docker image is published
> to `ghcr.io/tayloramareltech/duecare-llm:latest` by the
> `.github/workflows/docker-publish.yml` workflow. Every cloud below
> pulls from there. To use a different registry, override
> `DUECARE_IMAGE` in the env file or override `image.repository` in
> the Helm values.

## Quickest paths (5 minutes or less)

| Platform | When to use | Cost | Setup time |
|---|---|---|---|
| [Hugging Face Spaces](#1-hugging-face-spaces-easiest) | Hackathon demos, public live URL, free tier | Free → $0.40/hr GPU | 5 min |
| [Render](#2-render-easy-managed) | Personal demos, NGO pilot with one container | Free → $7/mo | 5 min |
| [Fly.io](#3-flyio-cheap-global) | Low-cost global edge | Free trial → $5/mo | 10 min |
| [Railway](#4-railway-trivial-ci) | Indie / NGO pilot | $5/mo + usage | 5 min |

## Production / enterprise paths

| Platform | When to use | Cost (chat-only) | Setup time |
|---|---|---|---|
| [AWS EKS (Helm)](#5-aws-eks-helm) | Existing AWS shop | ~$75/mo control plane + workers | 30 min |
| [GCP GKE Autopilot (Helm)](#6-gcp-gke-autopilot-helm) | Cleanest managed K8s | ~$75/mo + per-pod | 25 min |
| [Azure AKS (Helm)](#7-azure-aks-helm) | Existing Azure shop | ~$75/mo | 30 min |
| [AWS Lightsail Container](#8-aws-lightsail-container-cheaper-than-eks) | Single-container production | $7/mo (Nano) | 10 min |
| [GCP Cloud Run](#9-gcp-cloud-run) | Burst traffic, scale-to-zero | $0 idle, ~$0.0001/req | 10 min |
| [Azure Container Apps](#10-azure-container-apps) | Same niche as Cloud Run on Azure | $0 idle | 15 min |
| [Hetzner / DigitalOcean / Linode](#11-cheap-vps-bare-docker-compose) | Budget pilot, full control | $5-10/mo | 20 min |

## Special-purpose

- [self-hosted Kubernetes](#12-self-hosted-kubernetes-k3sk3d) — k3s/k3d for an NGO with own server
- [air-gapped Kubernetes](#13-air-gapped-deployment) — for jurisdictions that prohibit cloud egress

---

## 1. Hugging Face Spaces (easiest)

Free, Docker-based, comes with a permanent public URL. The
`hf-space/` directory in this repo is a working scaffold.

```bash
# from repo root
huggingface-cli login          # paste a write-scope HF token

# create the Space (one-time)
curl -X POST "https://huggingface.co/api/repos/create" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"duecare-live-demo",
    "type":"space",
    "private":false,
    "sdk":"docker"
  }'

# push the hf-space/ contents
cd hf-space
git init
git remote add origin https://huggingface.co/spaces/<your-username>/duecare-live-demo
git add . && git commit -m "Initial deploy"
git push -u origin main

# in the Space settings (web UI):
#   Add secret: HF_TOKEN = your token (needed for gated Gemma access)
```

Demo URL appears at `https://huggingface.co/spaces/<your-username>/duecare-live-demo`
~10 min later (initial Docker build + Gemma weight pre-cache).

Hardware tiers: t4-small (free, 2 GPU-hr/day), t4-medium ($0.60/hr),
a10g-large ($3.15/hr). For the hackathon demo: t4-small + Gemma 4
E2B fits easily.

Full setup walkthrough: `hf-space/DEPLOYMENT.md`.

---

## 2. Render (easy, managed)

```yaml
# render.yaml at repo root — render auto-detects + deploys on git push
services:
  - type: web
    name: duecare-chat
    runtime: image
    image:
      url: ghcr.io/tayloramareltech/duecare-llm:latest
    plan: starter           # $7/mo, 512 MB RAM; bump to standard ($25/mo) for chat with Ollama
    region: oregon          # or singapore for SE Asia OFW audience
    autoDeploy: true
    envVars:
      - key: DUECARE_LOG_LEVEL
        value: info
      - key: OLLAMA_HOST
        value: http://ollama:11434
    healthCheckPath: /healthz
    disk:
      name: model-cache
      mountPath: /home/duecare/app/.cache
      sizeGB: 2

  - type: pserv             # private service for Ollama
    name: ollama
    runtime: image
    image:
      url: ollama/ollama:latest
    plan: standard          # 4 GB RAM, enough for gemma2:2b
    disk:
      name: ollama-models
      mountPath: /root/.ollama
      sizeGB: 20
```

```bash
# deploy
cp infra/render/render.yaml ./
git add render.yaml && git commit -m "Render config" && git push
# create the project at render.com pointing at the repo; it auto-applies
```

Free tier exists but spins down after 15 min of inactivity (cold
start ~30 sec on next request). Starter ($7/mo) keeps it warm.

---

## 3. Fly.io (cheap, global)

```toml
# fly.toml at repo root
app = "duecare-chat"
primary_region = "sin"      # Singapore — closest to PH/ID OFW audience

[build]
  image = "ghcr.io/tayloramareltech/duecare-llm:latest"

[env]
  DUECARE_LOG_LEVEL = "info"
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0          # scale to zero when idle
  processes = ["app"]

[[http_service.checks]]
  grace_period = "15s"
  interval = "30s"
  timeout = "5s"
  method = "GET"
  path = "/healthz"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

```bash
fly auth login
fly launch --no-deploy --copy-config       # creates the app
fly deploy
fly open                                    # opens the public URL
```

Free trial: 3 shared-cpu VMs, 256 MB RAM each. $5/mo gets you a
shared-cpu-1x with 512 MB. For Ollama colocation, add a second
machine with 4 GB.

---

## 4. Railway (trivial CI)

```bash
npm install -g @railway/cli
railway login
railway init --name duecare-chat
railway up                                  # deploys current directory + Dockerfile
railway domain                              # generates a public URL
```

Variables via the web UI: `DUECARE_LOG_LEVEL=info`,
`OLLAMA_HOST=http://${{Ollama.RAILWAY_PRIVATE_DOMAIN}}:11434`.

Add Ollama as a second service:

```bash
railway add --service ollama --image ollama/ollama:latest
```

$5/mo subscription + ~$5-15/mo usage at small NGO scale.

---

## 5. AWS EKS (Helm)

For when you already run on AWS or want full Kubernetes.

```bash
# one-time: cluster
eksctl create cluster \
    --name duecare \
    --region us-west-2 \
    --node-type t3.large \
    --nodes 2

# install duecare via the included Helm chart
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --set ingress.enabled=true \
    --set 'ingress.hosts[0].host=duecare.your-domain.com' \
    --set image.repository=ghcr.io/tayloramareltech/duecare-llm

# install AWS Load Balancer Controller for ingress (one-time)
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system --set clusterName=duecare
```

For GPU (Ollama on a g5.xlarge):

```bash
# add GPU node group
eksctl create nodegroup \
    --cluster duecare \
    --name gpu-pool \
    --node-type g5.xlarge \
    --nodes 1 \
    --managed

# in your values file:
# ollama:
#   nodeSelector:
#     node.kubernetes.io/instance-type: g5.xlarge
#   tolerations:
#     - key: nvidia.com/gpu
#       operator: Exists

helm upgrade duecare ./infra/helm/duecare -f my-aws-values.yaml
```

Cost: $74/mo control plane + $60/mo for two t3.large workers = ~$135/mo
minimum. Add ~$370/mo for one g5.xlarge GPU node.

---

## 6. GCP GKE Autopilot (Helm)

GKE Autopilot is the cleanest managed K8s — Google sizes the nodes
for you, you only pay for pod-resources.

```bash
gcloud container clusters create-auto duecare \
    --region us-central1 \
    --release-channel regular

gcloud container clusters get-credentials duecare --region us-central1

helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --set image.repository=ghcr.io/tayloramareltech/duecare-llm \
    --set service.type=LoadBalancer
```

Cost: $74/mo control plane + ~$0.05/pod-hour for resources used. At
the default Helm values (chat: 250m CPU + 512Mi RAM × 2 replicas,
classifier: same, Ollama: 1 CPU + 4Gi), expect ~$70-100/mo.

GPU: add `--workload-pool=$PROJECT_ID.svc.id.goog` and use Spot GPUs.

```bash
# values override for spot GPU
helm upgrade duecare ./infra/helm/duecare \
    --set 'ollama.nodeSelector.cloud\.google\.com/gke-accelerator=nvidia-tesla-t4' \
    --set 'ollama.nodeSelector.cloud\.google\.com/gke-spot=true'
```

---

## 7. Azure AKS (Helm)

```bash
az aks create \
    --resource-group duecare-rg \
    --name duecare \
    --node-count 2 \
    --node-vm-size Standard_B2ms \
    --enable-addons monitoring,http_application_routing

az aks get-credentials --resource-group duecare-rg --name duecare

helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --set ingress.enabled=true \
    --set ingress.className=addon-http-application-routing
```

Cost: free control plane + ~$60/mo for two B2ms workers.

---

## 8. AWS Lightsail Container (cheaper than EKS)

For single-container production without K8s overhead.

```bash
aws lightsail create-container-service \
    --service-name duecare \
    --power nano \
    --scale 1

# create deployment from the multi-arch image
aws lightsail create-container-service-deployment \
    --service-name duecare \
    --containers '{
      "chat": {
        "image": "ghcr.io/tayloramareltech/duecare-llm:latest",
        "environment": {"DUECARE_LOG_LEVEL": "info"},
        "ports": {"8080": "HTTP"}
      }
    }' \
    --public-endpoint '{
      "containerName": "chat",
      "containerPort": 8080,
      "healthCheck": {"path": "/healthz"}
    }'
```

$7/mo (Nano: 0.25 vCPU, 512 MB RAM, 50 GB transfer) → $40/mo (Large:
4 vCPU, 8 GB RAM). No GPU option — for inference, point at an
external Ollama (e.g., on a g5 EC2 instance).

---

## 9. GCP Cloud Run

Scale-to-zero serverless containers. Pays nothing when idle.

```bash
gcloud run deploy duecare-chat \
    --image ghcr.io/tayloramareltech/duecare-llm:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --cpu 1 \
    --memory 1Gi \
    --max-instances 10 \
    --min-instances 0 \
    --timeout 300 \
    --set-env-vars DUECARE_LOG_LEVEL=info,OLLAMA_HOST=http://ollama:11434
```

Cost at hackathon-demo scale (low QPS): $0/mo. Cost at NGO scale
(50 reqs/day): $0.50/mo. Cost at enterprise (1k reqs/day): ~$15/mo.
GPU: yes, via Cloud Run for Anthos w/ GKE backing.

---

## 10. Azure Container Apps

Same scale-to-zero niche as Cloud Run on Azure.

```bash
az containerapp env create \
    --name duecare-env \
    --resource-group duecare-rg \
    --location eastus

az containerapp create \
    --name duecare-chat \
    --resource-group duecare-rg \
    --environment duecare-env \
    --image ghcr.io/tayloramareltech/duecare-llm:latest \
    --target-port 8080 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 10 \
    --cpu 1 --memory 2Gi
```

Cost: $0 idle, ~$0.0001/vCPU-second + memory. At NGO scale: ~$5/mo.

---

## 11. Cheap VPS (bare docker-compose)

For an NGO that wants full control on a $5-10/mo box.

```bash
# on the VPS (Ubuntu 22.04):
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker

# clone + deploy
git clone https://github.com/TaylorAmarelTech/gemma4_comp
cd gemma4_comp
docker compose up -d
docker compose logs -f             # tail to confirm chat + classifier + ollama healthy

# expose via Caddy for free TLS
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile <<EOF
duecare.your-domain.com {
    reverse_proxy localhost:8080
}
api.your-domain.com {
    reverse_proxy localhost:8081
}
EOF
sudo systemctl reload caddy
```

Recommended boxes:
- Hetzner CCX13 (4 vCPU, 8 GB): €13/mo
- DigitalOcean Basic Droplet (2 vCPU, 4 GB): $24/mo
- Linode Shared 4 GB: $24/mo

For Gemma serving on this box, use `gemma2:2b` (fits in 3 GB RAM).
For larger models, add a separate GPU box and point `OLLAMA_HOST`
at it.

---

## 12. Self-hosted Kubernetes (k3s/k3d)

For an NGO with their own datacenter or for testing the Helm chart
locally.

```bash
# install k3s (single-node, ~30 sec)
curl -sfL https://get.k3s.io | sh -

# install duecare
sudo k3s kubectl apply -f infra/helm/duecare    # OR use helm:
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --kubeconfig /etc/rancher/k3s/k3s.yaml
```

For local dev (no cloud at all):

```bash
# k3d via docker-desktop
brew install k3d            # macOS; or: scoop install k3d on Windows
k3d cluster create duecare-local --port "8080:80@loadbalancer"
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --set service.type=LoadBalancer
# open http://localhost:8080
```

---

## 13. Air-gapped deployment

For NGO partners in jurisdictions that prohibit cloud egress (some
agency / regulator deployments).

```bash
# 1. on a connected machine, pre-pull all images:
docker pull ghcr.io/tayloramareltech/duecare-llm:latest
docker pull ollama/ollama:latest

# 2. save to tarballs
docker save -o duecare-llm.tar ghcr.io/tayloramareltech/duecare-llm:latest
docker save -o ollama.tar ollama/ollama:latest

# 3. transfer (USB stick, internal network, etc.) to the air-gapped box

# 4. on the air-gapped box:
docker load -i duecare-llm.tar
docker load -i ollama.tar

# 5. pre-pull the Ollama model on the connected machine, copy the
#    Ollama models dir to the air-gapped box

# 6. docker compose up -d
```

Helm path: `helm template ... > rendered.yaml` on connected machine,
transfer rendered manifest, `kubectl apply -f rendered.yaml` on
air-gapped cluster.

---

## Choose the right path

| Audience | Recommended path | Why |
|---|---|---|
| Hackathon judges | HF Spaces | Free, public URL, no ops |
| NGO pilot (1-10 users) | Render or Fly.io | $5-7/mo, managed, fast |
| NGO production (50-500 users) | Lightsail Container or Cloud Run | ~$10-30/mo, scale-to-zero or fixed |
| NGO production with GPU | GKE Autopilot + spot T4 | Best $/perf for occasional inference |
| Enterprise (existing AWS) | EKS Helm | Standard pattern, integrates with existing IAM/observability |
| Enterprise (existing GCP) | GKE Autopilot Helm | Cleanest managed K8s |
| Enterprise (existing Azure) | AKS Helm | Standard pattern |
| Self-hosted | docker-compose on Hetzner | Cheapest, full control |
| Air-gapped agency | k3s offline | Zero internet egress |

## Common environment variables

All deployments accept these:

| Var | Default | Meaning |
|---|---|---|
| `DUECARE_LOG_LEVEL` | `info` | `debug` / `info` / `warning` / `error` |
| `DUECARE_HOST` | `0.0.0.0` | Bind address |
| `DUECARE_PORT` | `8080` | Bind port |
| `OLLAMA_HOST` | (none) | URL of Ollama server (e.g., `http://ollama:11434`) |
| `DUECARE_OLLAMA_MODEL` | `gemma2:2b` | Model tag to use; bump to `gemma2:9b` if RAM permits |
| `HF_TOKEN` | (none) | Only needed for gated HF model downloads (transformers backend, not Ollama) |

## Common image tags

- `ghcr.io/tayloramareltech/duecare-llm:latest` — main branch tip
- `ghcr.io/tayloramareltech/duecare-llm:vX.Y.Z` — specific release
- `ghcr.io/tayloramareltech/duecare-llm:sha-<7chars>` — specific commit

All multi-arch (amd64 + arm64). Pulled from public GHCR — no auth
required.

## Cost summary (50 users/day, no GPU)

| Path | Monthly |
|---|---|
| HF Spaces (free tier) | $0 |
| Cloud Run / Container Apps (idle-heavy) | $0 |
| Render Starter | $7 |
| Fly.io shared-cpu-1x | $5 |
| Lightsail Nano | $7 |
| Railway | $10-20 |
| Hetzner CCX13 + Caddy | $14 |
| EKS minimum | $135 |
| GKE Autopilot | $75 |
| AKS minimum | $60 |

For an NGO pilot, **Render Starter or Fly.io** is the sweet spot. For
a production NGO deployment with structured monitoring / SSO /
compliance, **GKE Autopilot** is the cleanest. For Filipino /
Indonesian audience served from Singapore, **Fly.io's `sin` region**
is the best latency.
