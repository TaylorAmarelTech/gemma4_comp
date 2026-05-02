# Observability stack

One-command Prometheus + Grafana + OpenTelemetry Collector + Loki for
local + small-deployment Duecare monitoring. Mirrors what you'd run in
a kube-prometheus-stack + Loki + OTel-operator setup.

## Quick start

```bash
cd infra/observability
docker compose up -d
```

Wait ~30 seconds for everything to come healthy, then open:

| URL | What |
|---|---|
| http://localhost:3000 | Grafana (login: admin / admin) |
| http://localhost:9090 | Prometheus |
| http://localhost:3100 | Loki (query via Grafana) |
| http://localhost:4318 | OTLP HTTP receiver |
| http://localhost:4317 | OTLP gRPC receiver |

The "Duecare overview" dashboard is auto-provisioned and visible
under **Dashboards → Duecare**. It shows RPS, p50/p95/p99 latency,
error rate, tokens-per-tenant, GREP rule hits, ILO indicator
coverage, top corridors queried, and a Loki log stream of recent
errors.

## Wire your Duecare server to it

Set these env vars on the Duecare chat / classifier server:

```bash
DUECARE_METRICS_ENABLED=true
DUECARE_METRICS_PATH=/metrics
DUECARE_OTEL_ENDPOINT=http://otel-collector:4318
DUECARE_LOKI_ENDPOINT=http://loki:3100
DUECARE_ENV=local                # tags every metric/trace/log with this value
```

If your Duecare stack is on a different docker-compose network than
this observability stack, attach them at the network layer:

```bash
docker network connect duecare-observability duecare-chat
docker network connect duecare-observability duecare-classifier
docker network connect duecare-observability duecare-ollama
```

## Files

- `docker-compose.yml` — the full stack (Prometheus, Loki, OTel, Grafana)
- `prometheus/prometheus.yml` — scrape config; add new targets here
- `prometheus/rules.yml` — SLO-anchored alert rules
- `otel/otel-collector.yaml` — receivers + processors + exporters; the
  `attributes/scrub` processor hashes `prompt` / `response` / `user_id`
  attributes so raw user content doesn't reach the trace store
- `loki/loki-config.yaml` — single-binary Loki, 30-day retention
- `grafana/provisioning/datasources/datasources.yaml` — auto-wires
  Prometheus + Loki as datasources
- `grafana/provisioning/dashboards/dashboards.yaml` — auto-imports
  the JSON dashboards from `grafana/dashboards/`
- `grafana/dashboards/duecare-overview.json` — the headline dashboard

## Ports — override via .env

| Var | Default |
|---|---:|
| `PROMETHEUS_PORT` | 9090 |
| `LOKI_PORT` | 3100 |
| `OTEL_GRPC_PORT` | 4317 |
| `OTEL_HTTP_PORT` | 4318 |
| `GRAFANA_PORT` | 3000 |

## Production migration

For production, swap this docker-compose stack for a managed
equivalent:

| Component | Self-hosted | Managed alternatives |
|---|---|---|
| Prometheus | kube-prometheus-stack | Grafana Cloud Prometheus, Amazon Managed Prometheus, GCP Managed Prometheus |
| Loki | Loki Helm chart | Grafana Cloud Logs, Datadog, Splunk |
| OTel Collector | otel-operator | Grafana Cloud OTLP, Datadog Agent, Honeycomb |
| Grafana | Grafana Helm chart | Grafana Cloud, AWS-managed Grafana |

The `ServiceMonitor` template in `infra/helm/duecare/templates/`
is configured for the kube-prometheus-stack; the same OTLP env vars
work against any provider's OTLP endpoint. Switching providers is
typically a single env-var change + a credentials secret.

## Disable

```bash
docker compose down              # stop, keep data
docker compose down --volumes    # stop + drop dashboards + history
```
