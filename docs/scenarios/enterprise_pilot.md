# Enterprise pilot — adopting Duecare inside a platform org

> **Audience.** A platform engineer or applied-AI lead at a Big Tech
> / large enterprise (Google / Meta / Discord / a major bank /
> insurer / healthtech) evaluating Duecare as a content-safety
> harness around Gemma 4 inside an existing product surface.
>
> **Premise.** You already have a hosted LLM, an SRE rotation, an
> SSO mesh, and a procurement pipeline. You're not asking how to
> install Docker. You're asking: how do I bring Duecare into a
> tier-1 production environment without breaking the existing
> service?

## TL;DR — 30-day pilot plan

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Stand up pre-prod | Duecare deployed in your dev k8s, ServiceMonitor + Loki shipping, smoke-test passes |
| 2 | Wire to your stack | Tenant-id mapped from your OIDC, an internal team using `/api/chat` from a thin client, baseline metrics in Grafana |
| 3 | Stress + observe | k6 load profile against expected RPS, capacity sized, alerts tuned, runbook reviewed by SRE |
| 4 | Production cutover | Helm release in prod-NS with HPA + PDB + NetworkPolicy, OAuth proxy in front, on-call rotated |

Total org effort: ~1 platform engineer, half-time, for 4 weeks.

## Architecture inside an enterprise

Three load-bearing changes to the open-source defaults:

### 1. Use your existing OIDC / SSO instead of self-hosting oauth2-proxy

Duecare's `TenancyMiddleware` reads tenant id from `X-Forwarded-User`
/ `X-Auth-Request-User`. Your existing edge auth (Google IAP /
Cloudflare Access / AWS ALB / Azure App Gateway / a service-mesh
JWT validator) already sets these or equivalents. **Skip
`docker-compose.auth.yml` entirely** — it's for orgs that don't
have edge auth.

Configuration:
- Configure your edge proxy to forward the user's email or numeric
  ID as `X-Tenant-ID`
- Set `DUECARE_DEFAULT_TENANT=anonymous` so unauthenticated requests
  (e.g., from internal load-balancer healthchecks) get a stable id

### 2. Use your existing model gateway (vLLM / TensorRT-LLM / Ollama pool)

Duecare's `OllamaGemmaEngine` (Android) and `duecare-llm-models`
adapters speak the OpenAI-compatible `/v1/chat/completions` shape.
Point at your existing model gateway:

```yaml
# infra/helm/duecare/values.yaml override
chat:
  env:
    DUECARE_BACKEND: openai-compatible
    OPENAI_API_BASE: https://gemma4.your-org.internal/v1
    OPENAI_API_KEY: ${YOUR_INTERNAL_TOKEN}
    DUECARE_MODEL_NAME: gemma-4-e4b-it
```

Skip the bundled Ollama container — your gateway is faster, more
HA, and probably already GPU-pooled.

### 3. Per-tenant cost recording + chargeback

`packages/duecare-llm-server/src/duecare/server/metering.py` ships
the per-tenant token counter. Hook the counter to your billing
pipeline:

- Scrape `duecare_model_tokens_in_total` + `duecare_model_tokens_out_total`
  from Prometheus
- Multiply by your internal cost-per-1k-tokens
- Roll up daily by `tenant` label
- Push to your billing/showback system

Recording rule template in `docs/considerations/multi_tenancy.md`.

## Things to negotiate with your security team early

These are the conversations that take real time at a Big Tech org:

### Threat model walk-through (Week 1)

Hand them [`docs/considerations/THREAT_MODEL.md`](../considerations/THREAT_MODEL.md).
It's STRIDE across 4 trust boundaries, sized to a security-review
agenda. Expect questions about:

- Boundary 4 (cloud routing) — you're not using it inside a Big
  Tech deployment because your model gateway is internal; explicitly
  document this exclusion in your security-review packet
- Supply chain — pin to a specific GHCR image SHA + verify cosign
  signature in admission policy
- Multi-tenancy — RLS on the audit-log Postgres + per-tenant
  namespace isolation in k8s

### Compliance crosswalk (Week 1-2)

Hand them [`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md).
SOC 2 + GDPR + HIPAA + FedRAMP control map. Most controls are
**inherited from your existing platform** (you already have an
incident-response process, a key-management system, an audit-log
shipper, a data-residency policy). Duecare's specific controls
(per-request audit log, encryption at rest in journal, panic-wipe
primitive) are mapped to the framework controls.

### Vendor security questionnaire (Week 2)

Even though Duecare is open-source, your procurement team will
demand a CAIQ-Lite / SIG-Lite. Hand them
[`docs/considerations/vendor_questionnaire.md`](../considerations/vendor_questionnaire.md)
— it's pre-filled, with each row sourced to a specific repo file.

### Data-handling DPIA (Week 2-3)

Article 30 ROPA + Article 35 DPIA are operator responsibilities.
Duecare doesn't ship templates (yet) — your DPO has them already.
The harness's data-flow diagram for the DPIA is the boundary
diagram in `docs/considerations/THREAT_MODEL.md`.

## What "production-ready" means inside an enterprise

| Dimension | Open-source default | Enterprise-grade target |
|---|---|---|
| Deploy | `docker compose up` | Helm chart in prod-NS via Argo CD, signed image, mTLS |
| Auth | oauth2-proxy overlay | Existing SSO mesh (Google IAP / Cloudflare Access / Azure App Gateway) |
| Model | Ollama on the same box | Internal model gateway (vLLM / TensorRT-LLM / Ollama pool) over OpenAI-compatible API |
| Storage | SQLite | Postgres with RLS + read replicas + backup-as-a-service |
| Observability | Prom + Grafana + Loki + OTel locally | Existing telemetry stack (Datadog / New Relic / Grafana Cloud) |
| Secrets | env vars | Existing secret manager (Vault / GCP Secret Manager / AWS Secrets Manager) integrated via External Secrets Operator |
| Image supply chain | GHCR multi-arch | Pinned SHA, cosign-verified at admission, SBOM scanned in CI |
| Rate limit | per-tenant token bucket | Same + edge-level WAF + global-level distributed limiter (Redis or your existing one) |
| DR | Manual backup script | Your existing backup-as-a-service + RTO/RPO commitments |
| On-call | Runbook in the repo | Runbook reviewed by SRE + page rotation in PagerDuty/Opsgenie |

The `docs/considerations/enterprise_readiness.md` doc is the
checklist.

## Common pilot anti-patterns

Avoid:

- **"Wrap Duecare in a different framework first"** — defer until
  Week 5+. The bundled FastAPI server speaks OpenAPI 3 + has
  TypedDict request/response models; integrating with your own
  Python framework is mostly env-var passthrough.
- **"Re-implement the harness in our stack"** — the GREP rules +
  RAG corpus + tools are content, not framework-specific. Use the
  bundled implementation. If you need to extend the GREP catalog
  for your domain, see [`docs/extension_pack_format.md`](../extension_pack_format.md).
- **"Run Duecare with our internal model only; skip Gemma 4
  benchmarking"** — defeats the point. The harness's lift numbers
  (+56.5 pp mean across 207 hand-graded prompts) are measured
  against Gemma 4. If you want to run it against your internal
  model, run the bench-and-tune notebook (A2) against that model
  first to establish a baseline.
- **"Build a custom UI; don't use the bundled chat playground"** —
  the playgrounds are reference UIs. Your product surface is your
  call. The harness exposes `/api/chat` + `/api/classify` +
  `/api/research` + `/pipeline` — use those from your own client.

## What ships out-of-the-box vs what you build

| You get | You build |
|---|---|
| 17 PyPI packages + 6 + 5 Kaggle notebooks + Helm chart + Docker image | Your client UI (web / mobile / Slack / Discord / etc.) |
| 37 GREP rules + 26 RAG docs + 4 corridor lookups | Your domain-specific extensions (custom GREP rules, internal corpus, internal tools) |
| 11 ILO C029 indicators + 6 corridor profiles | Your jurisdiction-specific corridors / regulators / NGO lists |
| Per-tenant token + cost meter | Hook to your billing pipeline |
| OpenTelemetry traces + Prometheus metrics | Hook to your existing observability stack |
| Cosign-signed image | Cosign verification policy in admission |

## Negotiation: what to ask Duecare maintainer for

Most of this can be self-served via the open-source repo. Two
things that benefit from a direct conversation:

- **Custom GREP / RAG / corridor extensions** — if your enterprise
  domain (e.g., financial-fraud detection, recruitment-platform
  compliance) needs rules the bundled corpus doesn't cover, the
  maintainer can advise on the extension pattern + which existing
  rule to model after.
- **Reference architecture for your specific cloud** — if you're
  deploying on a less-common platform (Cloudflare Workers, a
  private cloud, an air-gapped environment), a 30-min call will
  save you a week of trial.

Reach out per `SECURITY.md`.

## See also

- [`docs/considerations/`](../considerations/) — the full enterprise governance set
- [`docs/deployment_topologies.md`](../deployment_topologies.md) — Topology C is the relevant shape
- [`docs/cloud_deployment.md`](../cloud_deployment.md) — 13-platform cloud cookbook
- [`docs/adr/005-tenant-id-from-edge-proxy.md`](../adr/005-tenant-id-from-edge-proxy.md) — why the auth pattern is what it is
