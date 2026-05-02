# Enterprise considerations

> **Optional supplements.** None of these docs are required to deploy
> Duecare. They exist for operators who need to defend a Duecare
> deployment to a security review, procurement team, compliance
> officer, or SRE on-call rotation.
>
> If you're a solo NGO advocate or a developer evaluating the harness,
> skip this folder — the [README](../../README.md) and
> [`docs/deployment_topologies.md`](../deployment_topologies.md)
> are everything you need.

## When to read what

| If you're... | Read |
|---|---|
| A solo NGO advocate / developer | Skip this folder. Use the topology selector in [`docs/deployment_topologies.md`](../deployment_topologies.md). |
| An SRE on-call for a Duecare deployment | [`runbook.md`](./runbook.md) + [`SLO.md`](./SLO.md) |
| A platform CTO evaluating Duecare | [`enterprise_readiness.md`](./enterprise_readiness.md) — the gap analysis with grades + 17-day plan |
| A multi-tenant platform operator | [`multi_tenancy.md`](./multi_tenancy.md) |
| A security review team | [`THREAT_MODEL.md`](./THREAT_MODEL.md) + [`COMPLIANCE.md`](./COMPLIANCE.md) |
| Procurement responding to a customer questionnaire | [`vendor_questionnaire.md`](./vendor_questionnaire.md) — pre-filled CAIQ-Lite answers |
| Capacity planning for a > 200-RPS deployment | [`capacity_planning.md`](./capacity_planning.md) + the k6 script at `tests/load/k6_chat.js` |

## What's in this folder

| Doc | Purpose |
|---|---|
| [`enterprise_readiness.md`](./enterprise_readiness.md) | CTO-perspective scorecard per pillar (telemetry, scalability, cost, IAM, compliance) with concrete deliverables |
| [`runbook.md`](./runbook.md) | Incident response per Prometheus alert (chat down, error rate, latency, etc.) |
| [`SLO.md`](./SLO.md) | Explicit availability + latency SLOs and the error-budget policy |
| [`multi_tenancy.md`](./multi_tenancy.md) | Tenant id resolution + isolation + OAuth2 provider cheat sheets |
| [`THREAT_MODEL.md`](./THREAT_MODEL.md) | STRIDE breakdown across 4 trust boundaries |
| [`COMPLIANCE.md`](./COMPLIANCE.md) | SOC 2 + GDPR + HIPAA + FedRAMP + ISO 27001 control map |
| [`vendor_questionnaire.md`](./vendor_questionnaire.md) | Pre-filled CAIQ-Lite answers for procurement |
| [`capacity_planning.md`](./capacity_planning.md) | Per-RPS sizing tables + k6 load-test recipe |

## What's NOT in this folder

These are core docs that every reader needs (kept at `docs/`):

- [`docs/architecture.md`](../architecture.md) — what Duecare is
- [`docs/deployment_topologies.md`](../deployment_topologies.md) — pick a deployment shape
- [`docs/cloud_deployment.md`](../cloud_deployment.md) — 13-platform cloud cookbook
- [`docs/deployment_local.md`](../deployment_local.md) — three local paths
- [`docs/embedding_guide.md`](../embedding_guide.md) — client integration
- [`docs/containers.md`](../containers.md) — Docker / dev / observability surfaces
- [`docs/FOR_JUDGES.md`](../FOR_JUDGES.md) — the hackathon submission roadmap
- [`docs/writeup_draft.md`](../writeup_draft.md) — the 1,500-word submission writeup
- [`docs/adr/`](../adr/) — architecture decision records

## Maturity status

The "considerations" docs are at **L3** maturity: comprehensive,
peer-reviewable, but the operator typically inherits responsibility
for actually filing the artifacts (DPIAs, BAAs, audit attestations).
We provide the templates; the operator's legal + security team
finalize them per their environment.

If you're trying to take Duecare into a regulated environment and
need help, the maintainer is reachable per `SECURITY.md`.
