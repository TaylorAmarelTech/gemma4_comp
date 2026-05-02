# Duecare service-level objectives (SLOs)

> SLOs are commitments to operators and to the rubric. Every metric
> here is observable in Grafana and alerted on in Prometheus.
> See `infra/observability/prometheus/rules.yml` for the alert wiring.

## What an SLO is here

An **SLO** is a target the platform commits to over a 30-day window.
A **SLI** is the underlying measurement. **Burn rate** is how fast
the error budget is consuming.

If we miss the SLO over the window, the on-call team owes a written
explanation + an action plan.

## Headline SLOs (chat playground — Topology C)

| SLO | Target | SLI | Source metric |
|---|---|---|---|
| **Chat completion success rate** | ≥ 99.5% | `1 - (5xx / total)` | `duecare_chat_requests_total{status}` |
| **Chat p95 latency (E2B model)** | < 8 s | p95 over 5m | `duecare_chat_request_duration_seconds_bucket` |
| **Chat p99 latency (E2B model)** | < 20 s | p99 over 5m | same |
| **Cold-start time** (first request after pod start) | < 90 s | per-pod first-request duration | `duecare_first_request_seconds` (custom) |
| **Audit log completeness** | 100% | requests with full provenance / total requests | logged at INFO via `duecare.observability` |

For the larger E4B model, double the latency numbers (p95 < 16s,
p99 < 40s). For the smaller Gemma 3 1B, halve them (p95 < 4s).

## Per-tenant SLOs (multi-tenant deployments)

| SLO | Default target | Override per-tenant |
|---|---|---|
| **Token budget** | 1M tokens / day | `duecare_tenant_token_budget_daily{tenant}` |
| **Request budget** | 10k requests / day | `duecare_tenant_request_budget_daily{tenant}` |
| **Concurrency cap** | 10 in-flight requests | `duecare_tenant_concurrency_cap{tenant}` |

Each is enforced at the request middleware. When a tenant exceeds
their budget, return HTTP 429 with `Retry-After` and a body that
points to their account dashboard.

## Error budget policy

The 0.5% error budget over 30 days is **14.4 minutes of complete
downtime** (or equivalent in degraded availability).

- 25% of budget burned in 1 hour → **fast-burn alert (P1)**
- 50% of budget burned in 6 hours → **slow-burn alert (P1)**
- 100% of budget burned → **freeze deploys until cleared**

The freeze means: no non-critical-fix deploys until the next 30-day
window starts AND a written remediation plan exists.

## SLI / SLO measurement window

- **5-minute window** for fast-burn detection
- **1-hour window** for slow-burn
- **30-day rolling window** for the headline number

## What's *not* covered by these SLOs

- **First-launch model download** (Topology D / on-device only).
  This is a one-time cost paid by the worker; not a service SLO.
- **Cloud Gemma routing latency** (Topology E). The latency depends
  on the worker's chosen cloud endpoint, not on Duecare. We monitor
  the timeout rate but don't commit a latency SLO for cloud routing.
- **Internet-search lookup latency** (`duecare-llm-research-tools`).
  Tavily / Brave / Serper / DuckDuckGo SLAs apply. We monitor and
  alert on > 30s lookup time but don't promise < N s.

## Reviewing SLOs

Every quarter:

1. Pull the 90-day actuals from Grafana.
2. Compare to target. If actual >> target (we're crushing it),
   tighten the SLO. If actual ≈ target, leave it. If actual << target,
   loosen it OR fix the underlying issue.
3. Update this doc with the new target + reasoning.
4. Update `infra/observability/prometheus/rules.yml` to match.

The next review is **2026-08-01**.
