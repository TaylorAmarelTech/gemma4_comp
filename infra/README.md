# Duecare Infra

Cloud deployment manifests + scripts for every major target.
Per-platform spec, no manual port-twiddling required. Full guide:
[`docs/cloud_deployment.md`](../docs/cloud_deployment.md).

## Layout

```
infra/
├── README.md           ← this file
├── helm/
│   └── duecare/        ← Kubernetes Helm chart (works on any K8s)
├── render/
│   └── render.yaml     ← Render.com Blueprint
├── fly/
│   └── fly.toml        ← Fly.io app spec
├── railway/
│   └── railway.json    ← Railway service config
├── aws/
│   └── lightsail-deploy.sh   ← AWS Lightsail Container (single-container, $7-40/mo)
├── eks/
│   └── eksctl-cluster.yaml   ← AWS EKS cluster spec (eksctl)
├── gcp/
│   └── cloudrun-deploy.sh    ← GCP Cloud Run (scale-to-zero)
├── gke/
│   └── gke-autopilot-deploy.sh   ← GCP GKE Autopilot (managed K8s)
├── azure/
│   └── containerapp-deploy.sh    ← Azure Container Apps (scale-to-zero)
└── aks/
    └── aks-deploy.sh             ← Azure AKS (managed K8s)
```

## Pick the right path

| Need | Use |
|---|---|
| Hackathon judges click a URL | [`hf-space/`](../hf-space/) (HF Spaces) |
| NGO pilot, $7/mo, managed | `infra/render/render.yaml` |
| Cheapest global edge | `infra/fly/fly.toml` |
| Scale-to-zero serverless on GCP | `infra/gcp/cloudrun-deploy.sh` |
| Scale-to-zero serverless on Azure | `infra/azure/containerapp-deploy.sh` |
| Single AWS container, no K8s | `infra/aws/lightsail-deploy.sh` |
| Existing AWS shop, want K8s | `infra/eks/eksctl-cluster.yaml` + `helm/duecare` |
| Cleanest managed K8s | `infra/gke/gke-autopilot-deploy.sh` |
| Existing Azure shop | `infra/aks/aks-deploy.sh` |
| Self-hosted on a $5 VPS | `docker-compose.yml` at repo root |
| Local Kubernetes testing | k3s/k3d + `helm/duecare` |
| Air-gapped / no cloud | `docker save` + manual transfer (see `docs/cloud_deployment.md` §13) |

## Common assumptions

- **Container image:** `ghcr.io/tayloramareltech/duecare-llm:latest`
  (multi-arch amd64 + arm64). Built + published by
  `.github/workflows/docker-publish.yml` on every tag + main commit.
- **Default port:** 8080 (chat playground), 8081 (classifier).
- **Healthcheck:** `GET /healthz` returns 200.
- **Stateless server:** all per-user customizations live in browser
  `localStorage` and ship per-message; no server-side database.

## Cost summary (50 users/day, no GPU)

See `docs/cloud_deployment.md` for the full table. TL;DR:

- Free → $7/mo: HF Spaces, Cloud Run idle, Render Free, Fly free trial
- $7-15/mo: Render Starter, Lightsail Nano, Fly shared-cpu
- $30-150/mo: Container Apps moderate use, Lightsail Large, AKS, GKE Autopilot
- $135+/mo: EKS minimum (control plane is $74 alone)

## Adding a new platform

1. Create `infra/<platform>/` directory.
2. Add either a one-shot deploy script (`*-deploy.sh`) or a config file
   (`<platform>.yaml`).
3. Add a row to `docs/cloud_deployment.md` ranking table.
4. Update this README's layout + pick-the-right-path tables.
