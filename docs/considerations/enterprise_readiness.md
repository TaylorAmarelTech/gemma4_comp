# Enterprise readiness — CTO gap analysis

> **Voice.** Written from the perspective of a platform CTO at a
> Google / Meta / Discord / Anthropic-scale company evaluating whether
> Duecare is production-ready for a 1M+ user roll-out. Honest grades.
> Each gap has a concrete fix path and a "ship-by" target.
>
> **Generated:** 2026-05-01. Read alongside
> [`docs/rubric_evaluation_v07.md`]( ../rubric_evaluation_v07.md) (the
> hackathon-judge view) and [`docs/deployment_topologies.md`]( ../deployment_topologies.md)
> (how to deploy what's here today).

## TL;DR — readiness score

| Pillar | Today | What it would take to reach "production-grade FAANG-tier" | Priority |
|---|:-:|---|:-:|
| **Containerization** | A– | Multi-arch images: ✓. Distroless runtime: not yet. Multi-stage build: ✓. Image signing (cosign): wired in workflow but verify supply chain. | P1 |
| **Telemetry — metrics** | C | Prom-format `/metrics` endpoint + OpenTelemetry traces + structured logs to Loki. Grafana dashboards committed to repo. | **P0** |
| **Telemetry — traces** | C– | Distributed tracing across the chat → harness → model-call path. OTel SDK in every package. Sampling at the gateway. | P1 |
| **Telemetry — logs** | B | structlog already JSON-by-default. Need: log shipping config (Loki / Datadog / Splunk) and a documented log schema. | P1 |
| **Reporting** | C | Per-tenant token + cost rollup. Per-rule (GREP/RAG/Tool) hit rates. ILO-indicator coverage time series. Today: ad-hoc. | **P0** |
| **Monitoring + alerting** | D | Healthchecks: ✓. SLOs: not defined. Alert rules: not committed. Need: Prometheus alert rules + on-call playbook. | **P0** |
| **Scalability — horizontal** | B– | Stateless server: ✓. Helm chart: ✓. HPA: not yet. Queue for slow inference: not yet. GPU node pool selector: not yet. | **P0** |
| **Scalability — vertical** | A– | Multi-arch (amd64 + arm64): ✓. CPU works for E2B; GPU optional. Documented sizing in `deployment_topologies.md`. | done |
| **Cost tracking** | F | No per-tenant accounting. No model-call billing meter. No carbon-cost rollup. | **P0** |
| **Tunability — config-as-code** | B+ | Pydantic settings: ✓. Env vars: ✓. Per-deployment YAML overrides: ✓. Need: feature flags (LaunchDarkly / OpenFeature). | P2 |
| **Auth / IAM** | D | No SSO. No RBAC. No API key management. Anyone hitting the open server has full access. | **P0** |
| **Multi-tenancy** | F | Single-tenant by design today. Per-customer isolation needs a tenant-id propagated through every layer + per-tenant rate limits + per-tenant audit log. | P1 |
| **Compliance posture** | C | MIT license clear. Privacy stance documented. Need explicit SOC 2 / GDPR / HIPAA control mapping and a vendor-questionnaire-ready doc. | P1 |
| **Disaster recovery** | C– | Backup strategy in `deployment_local.md` + `ngo-office-edge`. RTO/RPO not defined. Restore tested only ad-hoc. | P1 |
| **Documentation — judges** | A | `FOR_JUDGES.md`, `writeup_draft.md`, `rubric_evaluation_v07.md`, `deployment_topologies.md`. Current. | done |
| **Documentation — operators** | C+ | `docs/operations.md` exists. Runbook: not yet. Architecture Decision Records (ADRs): partial. | **P0** |
| **Documentation — security team** | D | `SECURITY.md` exists (boilerplate). Threat model: in `_reference/`. Penetration-test readiness checklist: not yet. | P1 |
| **Sustainability** | F | No carbon-cost tracking. No tooling to estimate energy per inference. | P3 |
| **Localization** | C | English-only docs. Chat surface accepts any language. Worker-facing strings: not localized. | P2 |

---

## What a Google / Meta / Discord CTO would scan for first

### 1. Can I deploy this to my k8s cluster in 60 minutes? (Yes, with caveats.)

Today: `infra/helm/duecare/` exists. `infra/eks/`, `infra/gke/`,
`infra/aks/` have entry-point scripts. Multi-arch image at
`ghcr.io/tayloramareltech/duecare-llm:latest`.

**Missing for production:**

- `HorizontalPodAutoscaler` template (CPU + custom metric: pending request count)
- `PodDisruptionBudget` (`maxUnavailable: 1` minimum)
- `NetworkPolicy` (default-deny, explicit allow for OTel collector + Ollama pool)
- `PodSecurityPolicy` / Pod Security Standards (`restricted` profile)
- `ServiceMonitor` CRD for the Prometheus operator
- Helm values overrides for: image registry, tenant namespace, GPU
  node selector, model variant, OTel endpoint
- Init container that pulls the model on first scheduling

### 2. Can I see what it's doing in real time? (Today: barely.)

The chat server logs JSON via `structlog`. There's no `/metrics`
endpoint. There's no distributed-trace propagation. There's no
Grafana dashboard committed to the repo.

**What an SRE expects:**

- Prom scrape endpoint with the standard set:
  - `duecare_chat_requests_total{tenant, model, status}`
  - `duecare_chat_request_duration_seconds{tenant, model, harness_layer}`
  - `duecare_grep_rule_hits_total{rule_id, severity}`
  - `duecare_rag_retrievals_total{corpus_id}`
  - `duecare_tool_calls_total{tool_name, success}`
  - `duecare_model_tokens_in_total{tenant, model}`
  - `duecare_model_tokens_out_total{tenant, model}`
  - `duecare_ilo_indicator_hits_total{indicator}`
  - `duecare_corridor_lookups_total{corridor_code}`
- OpenTelemetry traces with the spans:
  `chat.handler` → `harness.assemble` → `grep.match` → `rag.retrieve`
  → `tools.lookup` → `model.generate` → `harness.score`
- A `Grafana / Duecare overview.json` dashboard with the headline
  panels (RPS, p95, error rate, tokens-per-tenant, top GREP rules,
  ILO-indicator histogram time series).

### 3. Can I bill this internally? (Not yet.)

There's no per-tenant attribution. A 1M-user platform needs:

- A tenant-id stamped on every request (header, OIDC claim, or
  signed JWT)
- Per-tenant counters of: requests, model tokens in/out, tool calls
- Daily / monthly rollups exported to the company's billing system
- Cost-per-1k-tokens lookup table per model (so spend can be
  estimated without leaving the cluster)
- Carbon-cost estimator (kg CO2eq per inference, given the model
  variant + region power mix)

### 4. Can I survive an audit? (Most of the way.)

Strong points:
- All processing is auditable (every decision logged with
  `(model, prompt_hash, response_hash, grep_hits, rag_doc_ids,
  tool_results, harness_score, model_revision)`)
- Privacy posture is honest and documented
- MIT license is clean (no AGPL contagion)
- Composite-character framing in writeup avoids real-PII issues

Weak points needing closure before a Big Tech security review:
- No SOC 2 control mapping doc
- No GDPR Article 30 record-of-processing template
- No HIPAA business-associate-agreement template
- No FedRAMP moderate baseline crosswalk
- No formal threat model in the public repo (one exists in
  `_reference/` but isn't shipped)

### 5. Can I tune it without forking? (Mostly yes.)

Strong:
- Pydantic settings layer with env-var overrides
- Per-deployment YAML for domain packs, GREP rules, RAG corpus
- Extension-pack format documented in
  [`docs/extension_pack_format.md`]( ../extension_pack_format.md)

Missing:
- Feature flags (OpenFeature / LaunchDarkly / Unleash) — today every
  toggle requires a config push
- A/B split testing primitive (e.g., for new GREP rules: serve to
  10% of traffic, monitor lift, ramp)

---

## Concrete deliverables this audit unlocks

### P0 — needed to ship to a tier-1 platform

1. **`infra/observability/`** — Docker Compose stack: Prometheus +
   Grafana + OpenTelemetry Collector + Loki. Bring up locally with
   `make observability`. Single-command parity with what the SRE
   would build in their cluster.
2. **`/metrics` endpoint** in `duecare-llm-server` (Prometheus
   exposition format). Add `prometheus-client` as a dep.
3. **OpenTelemetry SDK wiring** in `duecare-llm-engine` so every
   inference call generates a span.
4. **HPA + PodDisruptionBudget + NetworkPolicy** Helm templates.
5. **Per-tenant token + cost meter** in the server (middleware).
6. **`docs/considerations/runbook.md`** — incident response: what to look at when
   p95 spikes / error rate climbs / model returns garbage.
7. **`docs/considerations/SLO.md`** — explicit SLOs: 99.5% chat-completion success,
   p95 < 8s for E2B chat, p99 < 20s.
8. **OAuth2 proxy + per-tenant rate-limit middleware** at the edge.

### P1 — needed for compliance review

9. **`docs/considerations/COMPLIANCE.md`** — SOC 2 + GDPR + HIPAA + FedRAMP control
   mapping. Cite where each control is implemented in the codebase.
10. **`docs/considerations/THREAT_MODEL.md`** — STRIDE breakdown of the chat surface
    + the harness + the journal.
11. **Multi-tenant isolation** — tenant-id propagation; per-tenant DB
    schemas or row-level security; per-tenant audit log shard.
12. **Vendor-questionnaire template** — the SIG-Lite / CAIQ /
    SOC-2-Type-II-readiness PDF that will be requested on day 1 of
    a Big Tech procurement.

### P2 — quality-of-life for operators

13. **Feature flags** via OpenFeature SDK with a YAML provider for
    self-hosted deployers and a LaunchDarkly provider for cloud.
14. **Locale / i18n** for the worker-facing surfaces (Tagalog,
    Bahasa, Nepali, Bangla, Arabic, Spanish).
15. **Carbon-cost middleware** — log per-inference `kg CO2eq`
    estimate based on `(model_variant, region, hardware)`.
16. **Capacity planning doc** with load-test artifacts (`k6` or
    `locust` scripts; recommended replica count per RPS tier).

---

## Prioritized 17-day plan (alongside hackathon submission work)

| Day | Deliverable | Lift it provides |
|---|---|---|
| Day 1 (today) | `infra/observability/` compose stack; `/metrics` endpoint stub; this doc | Visible "we monitor" story |
| Day 2 | Helm HPA + NetworkPolicy + PDB templates | Production k8s posture |
| Day 3 | Cost-tracking middleware design doc + per-tenant counter implementation | Billing story for procurement |
| Day 4 | `docs/considerations/COMPLIANCE.md` + `docs/considerations/THREAT_MODEL.md` + `docs/considerations/runbook.md` | Survives a security review |
| Day 5 | Grafana dashboard JSON committed; OTel SDK wired in `duecare-llm-engine` | "We can see everything" story |
| Day 6+ | Multi-tenancy primitives + feature flags + vendor questionnaire template | P1 polish |

This work is **independent of the hackathon submission video** — it
makes the *code repo* judges click into look like a production-ready
project, which is part of "Technical Depth & Execution" (30 points).

---

## What this doc commits to

The current Duecare repo is **research-grade with a clean engineering
spine** — typed Protocols, semver-tagged packages, multi-arch images,
working cloud deployment configs, comprehensive deployment-topology
docs. A motivated SRE could put it into production in a week.

The gaps to **enterprise-grade** (FAANG-tier) are the standard ones:
observability, multi-tenancy, cost attribution, SLO/SLA, and a
formal compliance posture. None of them are research problems; all
are 1-3 day each of focused engineering.

The next 17 days should close the **P0 set** (observability +
per-tenant cost meter + HPA + runbook + SLO + OAuth2 proxy +
COMPLIANCE.md). Together those move the repo from "interesting
research" to "you could honestly hand this to a Big Tech adoption
team."
