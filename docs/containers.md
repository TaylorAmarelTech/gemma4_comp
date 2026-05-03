# Container guide

Duecare ships **three container surfaces**, each for a different
audience. Pick one — they don't conflict.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. Production            2. Development           3. Topology   │
│     image + compose          dev compose              examples   │
│                                                                  │
│     ./Dockerfile             ./Dockerfile.dev        ./examples/ │
│     ./docker-compose.yml     ./docker-compose.dev    deployment/ │
│                              .yml                                │
│                                                                  │
│     Used by:                 Used by:                Used by:    │
│     - Cloud Run / EKS        - core developers       - operators │
│     - Render / Fly           - PR contributors         picking a │
│     - Lightsail VPS          - on-host iteration       topology  │
│     - the topology                                               │
│       examples (which                                            │
│       reuse this image)                                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Surface 1 — production image + compose

The repo root ships a **multi-stage, multi-arch Dockerfile** that
builds all 17 wheels and produces a slim runtime image.

```bash
# Build (single arch, for local testing)
docker build -t duecare-llm:latest .

# Build (multi-arch, push to a registry)
docker buildx build --platform linux/amd64,linux/arm64 \
    --tag ghcr.io/tayloramareltech/duecare-llm:latest --push .

# Run via compose (chat + classifier + Ollama)
cp .env.example .env             # optional — sensible defaults work
docker compose up -d
```

Then:
- chat playground: http://localhost:8080
- classifier: http://localhost:8081
- Ollama: http://localhost:11434

The image is also published by CI to
`ghcr.io/tayloramareltech/duecare-llm:latest` (multi-arch, signed
with cosign). All cloud-deployment configs in `infra/` pull from
there — there's exactly one canonical image.

**Default model:** `gemma4:e2b` (Apache 2.0, ~1.5 GB INT8). Override
via `DUECARE_OLLAMA_MODEL=gemma4:e4b` in `.env` for higher quality,
or `gemma3:1b` for faster cold starts.

## Surface 2 — development compose (hot reload)

`Dockerfile.dev` + `docker-compose.dev.yml` bind-mount the repo into
the container so source changes reload the chat server without a
rebuild. Includes ruff / mypy / pytest in the image.

```bash
docker compose -f docker-compose.dev.yml up                # foreground
docker compose -f docker-compose.dev.yml exec dev bash     # shell
docker compose -f docker-compose.dev.yml exec dev pytest -x
docker compose -f docker-compose.dev.yml exec dev ruff check src/
```

Use this surface for:
- Day-to-day Python development on the harness / packages
- Running the full pytest suite without dirtying the host venv
- Iterating on the chat-playground UI while the model is loaded

**Don't use this for production** — it runs as root, includes dev
tools that bloat the image, and bind-mounts the repo (security risk
in a multi-tenant cluster).

## Surface 3 — topology examples (deployment cookbook)

`examples/deployment/` ships **runnable, narrated** examples for the
five deployment shapes documented in
[`docs/deployment_topologies.md`](./deployment_topologies.md):

- `local-all-in-one/` — single Docker Compose stack (Topology A)
- `local-cli/` — single Python CLI, no Docker (Topology A)
- `ngo-office-edge/` — Mac mini / NUC + mDNS (Topology B)
- `server-and-clients/` — cloud server + 8 client patterns (Topology C)
- `hybrid-edge-llm-cloud-rag/` — phone Gemma + cloud knowledge (Topology E)

Each example reuses the same `ghcr.io/tayloramareltech/duecare-llm`
image. They differ in compose topology, env vars, and accompanying
documentation — not in the underlying binary.

Use this surface for:
- Operators evaluating which topology fits their org
- Showing judges + auditors a concrete deployment matching the
  writeup's claims

## Surface 4 — Kubernetes via Helm

For production K8s clusters, use the Helm chart at
[`infra/helm/duecare/`](../infra/helm/duecare/):

```bash
helm install duecare ./infra/helm/duecare \
  --namespace duecare --create-namespace \
  -f my-values.yaml
```

The chart includes:
- Chat + classifier deployments
- Service + Ingress
- HPA (CPU + memory)
- PodDisruptionBudget (`maxUnavailable: 1`)
- NetworkPolicy (default-deny, opt-in)
- ServiceMonitor for Prometheus Operator

Values doc inline in
[`infra/helm/duecare/values.yaml`](../infra/helm/duecare/values.yaml).
Cloud-specific entry points in `infra/{aws,gcp,azure,eks,gke,aks}/`.

## Surface 5 — observability stack

Optional companion stack for monitoring:

```bash
cd infra/observability
docker compose up -d
```

Brings up Prometheus + Loki + OpenTelemetry Collector + Grafana
with auto-provisioned datasources + a "Duecare overview" dashboard.

Wire your Duecare server to it via:
```
DUECARE_METRICS_ENABLED=true
DUECARE_OTEL_ENDPOINT=http://otel-collector:4318
DUECARE_LOKI_ENDPOINT=http://loki:3100
```

See [`infra/observability/README.md`](../infra/observability/README.md).

## Comparison matrix

| Surface | Where used | Hot reload | Tools in image | Production-safe |
|---|---|:-:|:-:|:-:|
| 1. Production image + compose | cloud + topology examples | no | no | yes |
| 2. Dev compose | local development | yes | yes | no |
| 3. Topology examples | operator-facing | (compose-relative) | (image-relative) | yes |
| 4. Helm chart | production K8s | no | no | yes |
| 5. Observability stack | beside any of the above | n/a | n/a | yes (single-binary Loki for small scale; swap for managed Loki at large scale) |

## What's NOT shipped here

- **Helm umbrella chart** that combines `infra/helm/duecare/` + the
  observability stack. Use Helmfile or ArgoCD `Application`s to
  orchestrate.
- **A `Tiltfile` for the dev compose** — the `docker compose -f
  docker-compose.dev.yml` flow already gives sub-second iteration
  with bind-mounts. Tilt is overkill for a 3-container dev loop.
- **A devcontainer.json** — exists at `.devcontainer/` for
  Codespaces / VS Code Remote Containers, separate from this
  Docker Compose surface. The Android sibling repo
  ([`TaylorAmarelTech/duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android))
  has its own equivalent local-setup doc.

## Common operations

```bash
# Smoke test the production image
make docker-build && make docker-up
curl http://localhost:8080/healthz   # → "ok"
curl http://localhost:8080/metrics   # → Prometheus exposition

# Run the test suite inside the dev container
docker compose -f docker-compose.dev.yml run --rm dev pytest

# Tail logs
docker compose logs -f --tail=100

# Tear everything down + reclaim disk
docker compose down --volumes
docker compose -f docker-compose.dev.yml down --volumes
docker compose -f infra/observability/docker-compose.yml down --volumes
```
