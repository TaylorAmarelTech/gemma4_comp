# Operations runbook

For operators running Duecare in production (NGO-deployed dashboard,
enterprise classifier API, multi-pod Helm install).

## Health + readiness

Both chat and classifier expose `/healthz` returning `{"ok": true,
"ts": <epoch>}` when the process is up. The Docker image and the
Helm chart use this endpoint for healthchecks + Kubernetes
liveness/readiness probes.

```bash
curl -fsS http://localhost:8080/healthz | jq
```

If `/healthz` returns 200 but `/api/chat/send` 503s, the harness
itself is fine — it's the Ollama (or transformers) backend that's
failing. Check the model server independently:

```bash
curl -fsS http://localhost:11434/api/tags | jq
```

## Scaling

### Vertical (single pod / container)

The chat playground is mostly CPU-bound on the prompt-assembly
side and bound by the model backend on inference. Default Helm
limits (`2000m` CPU / `2 Gi` RAM per chat pod) handle ~40
sequential requests/min with `gemma2:2b` on Ollama.

Bump per pod for heavier traffic:

```yaml
chat:
  resources:
    limits:
      cpu: 4000m
      memory: 4Gi
```

### Horizontal (more pods)

The chat playground is stateless — chat state is sent client-side
in every request (`messages`, `toggles`, custom rules), so any pod
can serve any request. Default HPA scales 2-10 pods at 70% CPU
target. Bump for production:

```yaml
chat:
  autoscaling:
    minReplicas: 5
    maxReplicas: 50
    targetCPUUtilizationPercentage: 60
```

Ollama is **stateful** (model files on disk) and runs as a
single-replica StatefulSet-like Deployment (with `Recreate`
strategy and a `ReadWriteOnce` PVC). To scale model-serving
throughput, either:

1. Run a larger model on a GPU node (single Ollama replica with
   GPU = much higher tok/sec than 5 CPU replicas).
2. Front Ollama with a request-queueing proxy (HAProxy, Envoy)
   if multiple Ollama replicas are needed; `ReadWriteMany` on
   the model PVC is required (NFS, EFS, etc.).
3. Migrate from Ollama to a horizontally-scalable inference
   server (vLLM, TGI) for production-scale.

Recommendation: for NGO-scale (≤500 cases/day), single GPU node
with `gemma2:9b` is sufficient. For enterprise (>10k req/day),
move to vLLM + TGI on a GPU pool.

## Observability

### Prometheus metrics

All FastAPI endpoints emit standard request/response metrics via
the OpenTelemetry middleware (when enabled). To wire up:

```python
# In your kernel or custom server entrypoint:
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)
```

Then `/metrics` (when the Prometheus exporter is configured)
exposes:

| Metric | Type | What it measures |
|---|---|---|
| `http_requests_total{path,method,status}` | counter | total requests |
| `http_request_duration_seconds` | histogram | end-to-end latency |
| `duecare_grep_hits_total{rule}` | counter | how often each GREP rule fires |
| `duecare_rag_retrievals_total` | counter | RAG queries |
| `duecare_tools_calls_total{tool}` | counter | per-tool invocations |
| `duecare_gemma_tokens_generated_total` | counter | model output volume |
| `duecare_grade_total{category,verdict}` | counter | rubric outcomes |

These metrics are not emitted by default — the chat package keeps
runtime dependencies tight. Enable via the optional
`duecare-llm-publishing[observability]` extra.

### Structured logs

`structlog` with the PII-stripping filter from
`duecare.observability.logging`. JSON output, one event per line.
To ship to a log aggregator (Loki, Splunk, ELK), use the standard
container log drivers — no app-level config needed.

```bash
docker compose logs -f chat | jq
```

### Tracing

OpenTelemetry traces with the same exporter setup as metrics. Each
chat request produces one parent span with child spans for each
harness layer (persona / grep / rag / tools / model). Useful for
diagnosing "why was that request slow?"

## Backup + restore

### What's stateful

- Ollama model cache (PVC at `/root/.ollama`) — large but fully
  re-derivable from `ollama pull`. Backups optional.
- The chat playground itself: stateless. No DB, no queue, no
  user accounts. Customizations live in the user's
  `localStorage` and ship per-message.
- The classifier dashboard's history queue lives in the user's
  browser `localStorage`. Server is stateless.
- Audit logs (when observability is enabled): rotated container
  logs. Ship to your aggregator; no special backup needed.

### What's NOT stateful

The Duecare chat / classifier server has zero server-side state
beyond the harness rules + corpus + tools. Restoring after a
disaster is "redeploy the image."

### What IS stateful (Android app, separate repo)

The Android app's SQLCipher journal is the only place worker data
lives. Backup posture is **disabled by default** — the
`data_extraction_rules.xml` excludes everything from cloud backup
and device transfer. The worker can opt-in to an end-to-end
encrypted export via the Complaint or Refund-Claim flows. There
is no central backup; that's a deliberate privacy choice.

## Upgrades

### Container

```bash
# pull the new tag
docker compose pull chat classifier
# rolling restart with zero downtime
docker compose up -d --no-deps --build chat classifier
```

### Helm

```bash
helm upgrade duecare ./infra/helm/duecare \
    --namespace duecare \
    --reuse-values \
    --set image.tag=v0.1.0
```

The Deployment `RollingUpdate` strategy (`maxUnavailable: 1, maxSurge: 1`)
keeps service during the upgrade.

### Schema migrations (Android only)

The Android app's Room DB versioning lives in the `JournalDatabase.kt`
`@Database(version = N)` annotation. `fallbackToDestructiveMigration`
is enabled in v0.x; v1 MVP adds real Migration paths so worker data
survives upgrades.

## Disaster recovery

Single component failure recovery:

| Failure | Recovery |
|---|---|
| Chat pod crash | Kubernetes restarts; HPA scales if needed |
| Classifier pod crash | Same |
| Ollama pod crash | Recreate; model cache PVC is reattached; pull job re-runs only if model is gone |
| Model corruption | `kubectl exec` into Ollama, `ollama rm <model>; ollama pull <model>` |
| GHCR / PyPI outage | Pin to a private registry mirror; pre-stage images in the cluster |
| HF Hub outage (Android model download) | App caches the model after first download; existing installs unaffected |

## Security

- All HTTP endpoints serve over TLS in production (the Helm chart's
  Ingress block handles cert-manager integration).
- The chat + classifier images run as non-root user (UID 1000) per
  the Dockerfile + Helm `securityContext`.
- No HF_TOKEN / API keys in the image — pass at runtime via
  Kubernetes Secret + the `secrets.hfToken` Helm value.
- Per the `feedback_no_ship_metaphor.md` posture, releases are
  cryptographically signed (Sigstore via the Docker publish
  workflow's `provenance: true` flag generates SLSA provenance
  attestation).
- Audit log records `sha256(query)` for outbound research calls
  in the agentic notebook only — never plaintext.

For the full security posture, see `SECURITY.md` at the repo root
and the privacy section of `docs/android_app_architecture.md`.

## Capacity planning rules of thumb

| Audience scale | Setup |
|---|---|
| 1 worker (personal use) | Path 1 (one-line install) or Path 2 (Docker Compose) on a laptop |
| 1 NGO, ≤50 users/day | Single Helm release, 2 chat pods, 1 Ollama with `gemma2:2b` on a single t3.large or equivalent |
| 1 NGO, ≤500 users/day | Helm release with 5-10 chat replicas (HPA auto-scales), 1 Ollama with `gemma2:9b` on a single GPU node (T4 or A10G) |
| Enterprise, ≤10k req/day | Same as NGO ≤500 + add the classifier as separate replicas, monitor HPA scaling decisions, add observability stack (Prometheus + Grafana) |
| Enterprise, >10k req/day | Replace Ollama with vLLM or TGI on a GPU pool; add Redis for response caching; add HAProxy / Envoy in front of the model server |
