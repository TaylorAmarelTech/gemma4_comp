# Compliance posture — control mapping

> **Audience.** Procurement / security / compliance teams reviewing
> Duecare for adoption inside a regulated environment (Big Tech
> internal use, NGO with grant-driven data-handling requirements,
> healthcare / government / financial services).
>
> Each control row maps a published framework requirement to where
> Duecare implements it (or explicitly defers it to the operator's
> deployment).

## Frameworks covered

- **SOC 2 Type II** — security + availability + confidentiality
  trust criteria
- **GDPR** — EU data-protection regulation
- **HIPAA** — US health-information privacy (where Duecare is used
  for migrant-worker health-disclosure intake)
- **FedRAMP Moderate** — US federal systems, baseline crosswalk
- **ISO 27001 Annex A** — information-security controls

## Quick verdict

| Framework | Today | Gap to attestable |
|---|:-:|---|
| SOC 2 — Security | C+ | Need: documented access reviews, incident response runbook (✓ today), change management, vendor management |
| SOC 2 — Availability | B | SLOs documented (`docs/SLO.md`); need DR test artifacts |
| SOC 2 — Confidentiality | B+ | Encryption at rest in journal (SQLCipher); encryption in transit (TLS); need key-rotation policy |
| GDPR | B | DPIA template needed; Article 30 record-of-processing template needed |
| HIPAA | C | BAA template needed; PHI redaction is in `duecare-llm-research-tools` (PIIFilter); audit log present; need designated security officer assignment |
| FedRAMP Moderate | D | Far from attestable (would need StateRAMP / 3PAO assessor engagement); Documented for crosswalk only |
| ISO 27001 | C+ | Many Annex A controls implemented organically; would need ISMS scope statement + risk register to certify |

## SOC 2 control map

### Security (CC6 series — Logical & Physical Access Controls)

| SOC 2 control | Where implemented | Status |
|---|---|:-:|
| CC6.1 — Logical access | `duecare-llm-server` middleware (auth proxy expected at edge); `infra/helm/duecare/templates/networkpolicy.yaml` enforces default-deny | A |
| CC6.2 — User access reviews | Operator responsibility; documented in `docs/operations.md` | C |
| CC6.3 — Privileged access | Container runs as non-root user (uid 1000) per `Dockerfile`; pod security context `runAsNonRoot: true` per Helm | A |
| CC6.6 — Inbound/outbound traffic | NetworkPolicy default-deny + explicit allowlist | A |
| CC6.7 — Data transit encryption | TLS terminated at edge; mTLS optional via service mesh (Istio / Linkerd) | A |
| CC6.8 — Anti-malware / vulnerability scanning | `gha-workflow trivy` recommended; not yet wired | C |

### Availability (CC9, A series)

| SOC 2 control | Where | Status |
|---|---|:-:|
| A1.1 — Capacity planning | `docs/deployment_topologies.md` hardware sizing; HPA in Helm | A |
| A1.2 — Backup + recovery | `examples/deployment/ngo-office-edge/README.md` documents backup; no automated DR test | B |
| A1.3 — Operations + monitoring | `infra/observability/` stack + `docs/runbook.md` + `docs/SLO.md` | A |

### Change management (CC8)

| SOC 2 control | Where | Status |
|---|---|:-:|
| CC8.1 — Authorized changes | GitHub PR review + `claude.yml` workflow; semver-tagged releases; required CI passes | A |
| CC8.2 — Production deploy approval | GitHub environments (`production` env requires manual approval) — operator-configurable | B |

### Risk assessment (CC3)

| SOC 2 control | Where | Status |
|---|---|:-:|
| CC3.1 — Threat model | `docs/THREAT_MODEL.md` (planned) | D |
| CC3.2 — Risk register | Operator responsibility | n/a |

## GDPR control map

| GDPR requirement | Implementation | Status |
|---|---|:-:|
| Lawful basis for processing | Documented in writeup + `docs/deployment_modes.md`; lawful basis is "consent" or "legitimate interest in NGO casework" depending on deployment | A |
| Article 5 — Data minimization | Harness only stores: (a) hashed prompt, (b) hashed response, (c) GREP rule IDs, (d) RAG doc IDs, (e) tool-result IDs. Raw text in audit log only when worker explicitly opts in. | A |
| Article 5 — Storage limitation | Configurable retention via `DUECARE_AUDIT_RETENTION_DAYS` env var; default 90 days | A |
| Article 25 — Privacy by design | On-device default (Topology D / Android); cloud routing opt-in; panic wipe primitive | A |
| Article 30 — Records of processing | Per-tenant audit log + provenance chain; need a published Article 30 template | C |
| Article 32 — Security of processing | TLS in transit; SQLCipher at rest in journal; configurable; documented | A |
| Article 33 — Breach notification | Operator responsibility — runbook says "P0 = page on-call"; no automated 72-hour notification | C |
| Article 35 — DPIA | Template needed | D |
| Articles 15-22 — Subject rights | API: `DELETE /tenant/{id}/data` exposed in `duecare-llm-server`; export via `GET /tenant/{id}/data?format=ndjson` | B |

## HIPAA crosswalk (for NGO-side health-disclosure intake)

| HIPAA control | Implementation | Status |
|---|---|:-:|
| §164.308(a)(1)(ii)(A) — Risk analysis | Threat-model doc planned | D |
| §164.308(a)(3) — Workforce security | Operator responsibility | n/a |
| §164.308(a)(4) — Information access management | Auth proxy + RBAC at edge; per-tenant isolation | C |
| §164.308(a)(5) — Security awareness training | Operator responsibility | n/a |
| §164.308(a)(6) — Security incident procedures | `docs/runbook.md` | A |
| §164.308(a)(8) — Evaluation | Penetration testing recommended; not in this repo | D |
| §164.310 — Physical safeguards | Operator responsibility (cloud provider's controls) | n/a |
| §164.312(a)(1) — Access control | Tenant-id stamped on every request; per-tenant isolation primitives | B |
| §164.312(a)(2)(iv) — Encryption + decryption | SQLCipher at rest; TLS in transit; key rotation operator-configurable | A |
| §164.312(b) — Audit controls | Audit log per request: `(model, prompt_hash, response_hash, grep_hits, rag_docs, tool_results, harness_score, model_revision, tenant_id)` | A |
| §164.312(c) — Integrity | Cryptographic hash on every audit-log row | A |
| §164.312(e) — Transmission security | TLS 1.3 minimum at edge; mTLS optional | A |

A signed Business Associate Agreement (BAA) with the operator is the
remaining gap for HIPAA-bound deployments. Duecare doesn't currently
ship a BAA template; engage your legal team or use the HHS sample.

## FedRAMP Moderate crosswalk

This is **informational only** — Duecare has not been through StateRAMP
nor a 3PAO assessment. The crosswalk is included so a federal-adjacent
NGO can evaluate scope.

| Control family | Implementation | Coverage |
|---|---|:-:|
| AC (Access Control) | NetworkPolicy default-deny + auth proxy + per-tenant isolation | partial |
| AU (Audit & Accountability) | structured audit log + 90-day retention | partial |
| CM (Configuration Management) | Helm values + GitHub-tracked changes | strong |
| CP (Contingency Planning) | Backup docs; DR test artifacts not yet committed | partial |
| IA (Identification & Authentication) | Operator brings own auth proxy | partial |
| IR (Incident Response) | `docs/runbook.md` | strong |
| RA (Risk Assessment) | Threat-model doc planned | weak |
| SA (System & Services Acquisition) | All deps pinned + audited; Renovate / Dependabot recommended | partial |
| SC (System & Communications Protection) | TLS + NetworkPolicy + at-rest encryption | strong |
| SI (System & Information Integrity) | SHA-256 verify on model downloads (Android); Tink + SQLCipher (journal) | partial |

## ISO 27001 — Annex A summary

Most Annex A controls map to the SOC 2 + GDPR rows above. The ones
unique to ISO 27001:

| Control | Implementation | Status |
|---|---|:-:|
| A.5.1 — Information security policy | Operator publishes; this repo provides templates | C |
| A.6.3 — Information security awareness | Operator responsibility | n/a |
| A.8.10 — Information deletion | Panic-wipe primitive (Android); `DELETE /tenant/{id}` (server) | A |
| A.8.11 — Data masking | `PIIFilter` in `duecare-llm-research-tools`; `attributes/scrub` processor in OTel collector | A |
| A.8.12 — DLP | OperatorTask — usually layered on top by enterprise SOC | n/a |
| A.8.16 — Monitoring activities | Observability stack | A |
| A.8.32 — Change management | GitHub-tracked + semver | A |

## Vendor questionnaire — common asks answered

These questions show up on every Big Tech procurement:

| Question | Answer |
|---|---|
| **Does Duecare ship as SaaS or self-hosted?** | Self-hosted only. Five deployment topologies in `docs/deployment_topologies.md`. No data ever passes through a Duecare-operated server. |
| **Where does customer data live?** | In whatever data store the operator deploys to. Topology B/D = on-prem. Topology C = operator's cloud account. We never see it. |
| **Is data encrypted at rest?** | In the Android journal (Topology D) yes — SQLCipher with key in Android Keystore. In the server's evidence-db, encryption is the operator's responsibility (Postgres TDE, RDS encryption, etc.). |
| **Is data encrypted in transit?** | TLS 1.3 at the edge. mTLS available via service mesh. |
| **What's the SLA?** | The community + reference SLOs are in `docs/SLO.md` (99.5% chat success, p95 < 8s for E2B). Commercial SLAs are operator-configurable. |
| **What's the data retention default?** | 90 days for the audit log; configurable via env var. Journal is unbounded — operator chooses. |
| **What sub-processors do you use?** | Zero by default. If the operator configures cloud-Gemma routing (Ollama / OpenAI / HF), those become sub-processors. If they enable internet search (Tavily / Brave / Serper), those too. |
| **Is the source code auditable?** | Yes — MIT-licensed, all 17 packages on PyPI, all deps pinned, semver tags. |
| **Any third-party security audits?** | Not yet. Recommended for any production deployment. |

## What's missing from this doc that the audit found

These are documented gaps, not hidden ones:

- **THREAT_MODEL.md** — STRIDE breakdown of the chat surface +
  harness + journal. Drafting in progress.
- **Article 30 GDPR record-of-processing template**
- **DPIA template**
- **BAA template** (HIPAA)
- **Penetration-test readiness checklist**
- **Cosign / SLSA-3 build provenance** — partially wired (workflow
  has cosign step), needs operator's KMS for production signing

Each is a 1-3 day deliverable; tracked in
[`docs/enterprise_readiness.md`](./enterprise_readiness.md) under
the P1 set.
