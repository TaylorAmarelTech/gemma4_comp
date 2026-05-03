# Vendor security questionnaire — pre-filled

> Drop-in answers to the questions every Big Tech / regulated-NGO
> procurement team asks on day 1 of evaluating Duecare for adoption.
> Pairs with [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md) (control map),
> [`docs/considerations/THREAT_MODEL.md`](./THREAT_MODEL.md), and
> [`docs/considerations/SLO.md`](./SLO.md).
>
> Format follows a CAIQ-Lite / SIG-Lite style. Reuse rows verbatim
> when responding to a customer's questionnaire — every answer is
> linked to source-of-truth code or docs in this repo.

## A. General

| # | Question | Answer |
|---|---|---|
| A1 | Is Duecare SaaS or self-hosted? | **Self-hosted only.** Operator deploys to their own infra (laptop / NGO office / cloud / k8s). The Duecare authors do not operate any service that customer data passes through. See [`docs/deployment_topologies.md`](../deployment_topologies.md). |
| A2 | What's the licensing model? | MIT. All 17 PyPI packages, the Docker image, the Helm chart, and the Android repo are MIT. Gemma model weights are Apache 2.0 (Gemma 3/4) or [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (Gemma 2 legacy). |
| A3 | Where's the source code? | https://github.com/TaylorAmarelTech/gemma4_comp + https://github.com/TaylorAmarelTech/duecare-journey-android |
| A4 | Who's the maintainer? | Taylor Amarel (`amarel.taylor.s@gmail.com`). See `SECURITY.md` for vulnerability reporting. |
| A5 | What's the support SLA? | Community / best-effort by default. SLAs are negotiated separately — see operator agreement. |
| A6 | Versioning + release cadence? | Semver across all 17 packages. Tagged releases on GitHub. Multi-arch Docker image published to `ghcr.io/tayloramareltech/duecare-llm` per release. |

## B. Data handling + privacy

| # | Question | Answer |
|---|---|---|
| B1 | What customer data does Duecare process? | Worker chat prompts + responses; structured journal entries + attachments (Android only); RAG retrieval queries; tool-call arguments. Configurable retention. |
| B2 | Where does customer data live? | In whatever store the operator deploys to. Topology B/D = on-prem. Topology C = operator's cloud account. **The Duecare maintainers do not have access to any customer data.** |
| B3 | Is data encrypted at rest? | On Android (Topology D): SQLCipher with key in Android Keystore. On server (evidence-db, audit log): operator's responsibility — Postgres TDE / RDS encryption / GCP CMEK / Azure Key Vault. |
| B4 | Is data encrypted in transit? | TLS 1.3 at the edge. Mutual TLS between cluster pods is recommended via service mesh (Istio / Linkerd / Cilium). |
| B5 | Do you have a data classification scheme? | Yes — see [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md) "GDPR control map" + the `pii_filter.py` taxonomy in `duecare-llm-research-tools`. |
| B6 | Is there a data retention policy? | Default 90 days for the audit log; configurable via `DUECARE_AUDIT_RETENTION_DAYS`. Journal is unbounded — operator chooses. |
| B7 | Can customer data be deleted on request? | Yes. `DELETE /tenant/{id}/data` in `duecare-llm-server`; Settings → Panic wipe in the Android app. Both are immediate + irreversible. |
| B8 | Is data exportable on request? | Yes. `GET /tenant/{id}/data?format=ndjson`; Reports tab → "Generate intake document" in Android. |
| B9 | Do you cross-border transfer customer data? | No — Duecare doesn't transfer data across borders (we don't operate the service). Operator's cloud-region choices control residency. |
| B10 | Sub-processors? | Zero by default. Only present when operator opts in: cloud-Gemma routing (Ollama / OpenAI / HF Inference) + internet search (Tavily / Brave / Serper). All listed in `.env.example` with explicit env-var enablement. |

## C. Identity + access management

| # | Question | Answer |
|---|---|---|
| C1 | Authentication mechanism? | Operator-provided. Reference oauth2-proxy overlay (`docker-compose.auth.yml`) supports Google Workspace, Azure Entra ID, Auth0, Okta, Keycloak, Authentik, Dex, Cognito, GitHub. |
| C2 | MFA enforcement? | Operator's auth provider responsibility. Duecare doesn't downgrade MFA. |
| C3 | RBAC? | Tenant-id based per [`docs/considerations/multi_tenancy.md`](./multi_tenancy.md). Per-tenant rate limits + token budgets. Admin endpoints are out-of-band today. |
| C4 | Privileged access reviewed? | Operator responsibility. Recommended quarterly per SOC 2 CC6.2. |
| C5 | API key management? | Server `DUECARE_API_TOKEN` env var for static bearer-token auth; oauth2-proxy for OIDC. No long-lived API keys baked in. |
| C6 | Service account model? | One default per Helm release; `imagePullSecrets` and `serviceAccountName` configurable via `infra/helm/duecare/values.yaml`. |

## D. Network security

| # | Question | Answer |
|---|---|---|
| D1 | Network segmentation? | NetworkPolicy template in Helm: default-deny + explicit allow for in-cluster Ollama, OTel collector, DNS, opt-in external HTTPS. See `infra/helm/duecare/templates/networkpolicy.yaml`. |
| D2 | Egress filtering? | Operator-configurable via NetworkPolicy + cloud egress firewall. Recommended deny-all-external-HTTPS for air-gapped deployments. |
| D3 | DDoS protection? | Edge responsibility (Cloudflare / AWS Shield / GCP Cloud Armor). Per-tenant rate limits in the app provide secondary defense. |
| D4 | WAF? | Operator-deployed (Cloudflare WAF / AWS WAF / Akamai). |
| D5 | TLS minimum version? | TLS 1.3 at the edge in all reference deployments. |

## E. Application security

| # | Question | Answer |
|---|---|---|
| E1 | SAST in CI? | `ruff check` + `mypy` on every PR. Trivy / Snyk recommended for the operator. |
| E2 | Dependency vulnerability scanning? | `dependabot` + `renovate.json` recommended. Pinned versions in `pyproject.toml`. |
| E3 | SBOM published? | Yes — generated by GitHub's container build at `ghcr.io/tayloramareltech/duecare-llm` (oci-spdx attached); `cosign download sbom`. |
| E4 | Build provenance? | SLSA provenance attestation generated by the GHCR workflow per release. |
| E5 | Container image signing? | cosign keyless signing in the GHCR workflow. Verify with `cosign verify ghcr.io/tayloramareltech/duecare-llm:vX.Y.Z`. |
| E6 | Penetration testing? | Not yet. Recommended per release prior to production. |
| E7 | Secrets management? | All secrets via env var or Kubernetes Secret. No secrets in source. `gitleaks` recommended in CI. |
| E8 | Static container scanning? | Trivy recommended in CI; not yet wired. |

## F. Operational security

| # | Question | Answer |
|---|---|---|
| F1 | Incident response plan? | Yes — [`docs/considerations/runbook.md`](./runbook.md). Severity-based escalation; PR-driven post-mortems. |
| F2 | Threat model? | Yes — [`docs/considerations/THREAT_MODEL.md`](./THREAT_MODEL.md). STRIDE across 4 trust boundaries. |
| F3 | Backup + DR? | Operator responsibility. Backup commands documented in `examples/deployment/ngo-office-edge/README.md`. RTO / RPO operator-defined. |
| F4 | Logging + monitoring? | Yes — [`infra/observability/`](../infra/observability/) (Prometheus + Grafana + OTel Collector + Loki). SLO-anchored alerts in `prometheus/rules.yml`. |
| F5 | Audit log? | Yes. Per-request audit log at INFO via `duecare.observability` JSON-formatted. 90-day default retention. |
| F6 | Change management? | GitHub PR + required CI passes. Helm rollouts use `RollingUpdate` with `maxUnavailable: 1`. |
| F7 | Deployment automation? | GitHub Actions + Helm. Argo CD / Flux recommended for the operator. |
| F8 | Capacity planning? | [`docs/considerations/capacity_planning.md`](./capacity_planning.md) — per-RPS sizing tables + k6 load-test scripts. |

## G. Compliance + certifications

| # | Question | Answer |
|---|---|---|
| G1 | SOC 2 Type II? | Not certified (open-source project, not a service). Control map at [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md) for operator inheritance. |
| G2 | ISO 27001? | Not certified. Annex A control map at [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md). |
| G3 | HIPAA? | Not certified. BAA template = operator's legal team. HIPAA-relevant controls in [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md). |
| G4 | GDPR? | DPIA template not yet shipped (P1). DPO contact = operator's responsibility. Article 30 ROPA template = operator's responsibility. |
| G5 | FedRAMP? | Not authorized. Crosswalk in [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md) for federal-adjacent operators. |
| G6 | PCI-DSS? | Out of scope — Duecare doesn't handle payment data. |
| G7 | CCPA? | Operator handles consumer rights via the export / delete endpoints in B7+B8. |

## H. Business continuity + financial

| # | Question | Answer |
|---|---|---|
| H1 | Operator going-out-of-business risk to my data? | None — self-hosted, no Duecare SaaS dependency. Forking the open-source repo is the long-term mitigation. |
| H2 | Pricing model? | Free + open source. No per-seat / per-call / per-token fees from Duecare. Operator pays for their own model + cloud compute. |
| H3 | What sub-processors charge? | Tavily $0-$N/1k queries; Brave Search $0-$N/1k; Serper $0-$N/1k; OpenAI / Anthropic / Gemini per published rates. Local Gemma via Ollama: $0. |
| H4 | Cost ceiling for a typical 1000-user-month deployment? | $0 with Ollama + local-only; $5-50/mo for a Render-hosted Topology C; $75-500/mo for a managed K8s + GPU pool. See `docs/considerations/capacity_planning.md`. |

## I. Specific contractual + legal

| # | Question | Answer |
|---|---|---|
| I1 | Notice period for changes to terms / DPA? | N/a — open-source, no DPA between Duecare maintainers + operator. Operator's own DPA with their users applies. |
| I2 | Audit rights? | Source code is public. Customers may audit any time. |
| I3 | Right to terminate? | Anytime — uninstall the deployment. |
| I4 | Dispute resolution? | None applicable to the maintainers; operator + their users only. |
| I5 | Limitation of liability? | Per MIT license — provided "as is", no warranties. |

## Reuse + maintenance

This file is published verbatim — operators may copy it into their
internal procurement workflow without modification.

When responding to a customer's bespoke questionnaire:

1. Open this file + the customer's PDF / spreadsheet
2. For each customer question, find the closest row above
3. Copy the answer + cite the source (this repo's URL + doc path)
4. Where Duecare doesn't have an answer, mark "operator
   responsibility" + cite which doc explains the operator hand-off

For new questions worth answering more than once, file a PR adding
a row here. The benefit compounds: every future operator gets a
faster procurement cycle.
