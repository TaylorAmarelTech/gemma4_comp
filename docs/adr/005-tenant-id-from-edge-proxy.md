# ADR-005: Tenant id extracted from edge-proxy headers (vs in-app auth)

- **Status:** Accepted
- **Date:** 2026-05-01
- **Deciders:** Taylor Amarel

## Context

Multi-tenancy in `duecare-llm-server` requires each request to carry
a tenant identifier so the per-tenant rate limit, token budget,
audit log, and Prometheus labels resolve correctly.

Two architectural paths:

1. **Auth in the app** — `duecare-llm-server` includes its own
   OAuth2 client, JWT validation, session store, password reset
   flow, etc. Heavy + many ways to get wrong.
2. **Auth at the edge** — an upstream reverse proxy
   (oauth2-proxy / Cloudflare Access / AWS ALB / Istio) handles
   identity, then forwards a header to the app.

For a multi-deployment-shape project (NGOs running self-hosted,
enterprises running k8s, individual devs running localhost),
deferring to the edge is the only path that doesn't force the
operator to use Duecare's auth flavor.

## Decision

`duecare-llm-server` does **NOT** authenticate. It reads the tenant
id from a header set by the upstream proxy:

1. `X-Tenant-ID` (explicit, preferred for service-to-service)
2. `X-Forwarded-User` / `X-Auth-Request-User` (oauth2-proxy default)
3. `X-Forwarded-Email` / `X-Auth-Request-Email` (oauth2-proxy default)
4. `DUECARE_DEFAULT_TENANT` env var (single-tenant deployments)
5. literal `"public"` (fully-open kiosk deployments)

The static bearer-token check (`DUECARE_API_TOKEN`) is the one
exception — it provides "any authenticated client" gating for
single-tenant deployments without an OIDC provider, and is purely
optional.

## Alternatives considered

- **Bake OAuth2 client into the app.** Rejected: forces every
  operator to use Duecare's chosen OIDC library; doesn't compose
  with operators who already have an SSO mesh.
- **Per-tenant API keys managed in-app.** Rejected: requires a
  control plane + key rotation infrastructure we'd then own.
- **mTLS with per-tenant client certs.** Considered for high-trust
  service-to-service deployments, complementary to header-based
  auth. Documented as a recommendation in `docs/considerations/multi_tenancy.md`,
  not the default.

## Consequences

**Positive:**
- Operator picks the auth provider they already use (Google
  Workspace / Azure Entra / Auth0 / Okta / Keycloak / Authentik /
  Dex / Cognito / GitHub) via the `docker-compose.auth.yml` overlay
- Duecare doesn't carry an OIDC dep tree it has to keep current
- Identity is single-source-of-truth at the edge; the app sees a
  trusted assertion
- mTLS / WAF / DDoS protection / IP allowlist all live at the edge
  too — they compose

**Negative:**
- Operators MUST configure an upstream proxy to get real auth.
  Skipping it means anyone with the URL is "tenant=public" with
  full access. Mitigated by clear docs in `docs/considerations/multi_tenancy.md`.
- Header-spoofing risk: if a request reaches the app without going
  through the proxy (e.g., misconfigured NetworkPolicy), the app
  trusts whatever `X-Tenant-ID` the client sends. Mitigated by
  NetworkPolicy default-deny in the Helm chart.

## References

- `packages/duecare-llm-server/src/duecare/server/tenancy.py`
- [`docs/considerations/multi_tenancy.md`](../multi_tenancy.md)
- [`docs/considerations/THREAT_MODEL.md`](../THREAT_MODEL.md) Boundary 1 + Boundary 2
- [`docker-compose.auth.yml`](../../docker-compose.auth.yml)
