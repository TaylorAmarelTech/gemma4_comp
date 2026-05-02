# Multi-tenancy in Duecare

How Duecare distinguishes one customer / NGO / department from
another, what each tenant gets isolated, and how to wire it.

## TL;DR

Duecare attributes every chat / classify / research request to a
**tenant id**, then uses that id to:

- Stamp every Prometheus metric label (`tenant`)
- Stamp every OpenTelemetry span attribute (`tenant.id`)
- Enforce per-tenant rate limits (RPM + concurrency)
- Track per-tenant token + cost rollup
- Filter audit log per tenant
- (Optional) Route to a per-tenant model variant or domain pack

The middleware that does this lives in
[`duecare.server.tenancy`](../packages/duecare-llm-server/src/duecare/server/tenancy.py).
Auth is **always** the upstream proxy's job (see
[OAuth2 proxy overlay](#oauth2-proxy-overlay)). Tenancy is just
attribution; auth is enforcement.

## Tenant id resolution — order of precedence

Each request resolves its tenant id from the first source available:

1. **`X-Tenant-ID` header** — explicit. Best for service-to-service.
2. **`X-Forwarded-User` / `X-Auth-Request-User` / `X-Forwarded-Email` /
   `X-Auth-Request-Email`** — set by oauth2-proxy / Cloudflare Access /
   any OIDC reverse proxy. Best for human users.
3. **`DUECARE_DEFAULT_TENANT`** env var — a single value for the whole
   server. Best for single-tenant deployments (a single NGO running
   the harness for itself).
4. **literal `"public"`** — when nothing else resolves.

The id is sanitized to a small charset (`[a-z0-9._@_-]`) and
truncated to 64 chars before it ever reaches a metric label or
storage column.

## What's isolated per tenant

| Resource | Isolation | Where enforced |
|---|---|---|
| Request rate | Token bucket of `DUECARE_RATE_LIMIT_PER_MIN` rpm | `RateLimitMiddleware` |
| Concurrency | Hard cap of `DUECARE_CONCURRENCY_PER_TENANT` in-flight | `RateLimitMiddleware` |
| Token budget | `duecare_tenant_token_budget_daily{tenant}` gauge → `DuecareTokenBudgetExhausted` alert | `metering.set_tenant_budget()` + Prometheus |
| Audit log | Tenant id stamped on every audit row | `duecare-llm-evidence-db` |
| Metrics | Every counter / gauge / histogram has a `tenant` label | `duecare.server.observability` |
| Traces | Every span has a `tenant.id` attribute | `duecare-llm-engine.otel` |

## What is NOT isolated by default

- **Model weights** — every tenant talks to the same Ollama / model
  endpoint. To split (e.g. a tenant with stricter privacy gets a
  per-tenant Ollama pod), deploy multiple Helm releases of the
  Duecare chart and put a tenant-aware ingress in front.
- **Domain pack content** — the GREP rules + RAG corpus + tools are
  shared. To split (e.g. a tenant with their own legal corpus),
  use the [extension pack format](./extension_pack_format.md) and
  load per-tenant packs at request time.
- **Storage** — the SQLite/Postgres DB is single-schema. For
  per-tenant row-level security, enable PG RLS and partition the
  audit table by `tenant_id`.

These three are deliberately operator-controlled rather than
hard-coded in the middleware — most deployments don't need them, and
adding them later is straightforward.

## OAuth2 proxy overlay

The `docker-compose.auth.yml` overlay puts oauth2-proxy in front of
the chat service. Bring it up with:

```bash
cp .env.example .env
# Fill in OAUTH2_OIDC_ISSUER_URL, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET
# (any OIDC provider: Google Workspace, Azure Entra, Auth0, Okta, Keycloak, Authentik, Dex)
openssl rand -base64 32 | tr -d '\n' > .cookie_secret  # OAUTH2_COOKIE_SECRET

docker compose -f docker-compose.yml -f docker-compose.auth.yml up -d
```

Then visit `http://localhost:4180`. Login redirects through the
configured OIDC provider; after login, every request to the chat
upstream carries `X-Forwarded-User: <user@example.com>` and
TenancyMiddleware uses that as the tenant id.

For HTTPS production deployments:

```bash
OAUTH2_COOKIE_SECURE=true
OAUTH2_REDIRECT_URL=https://chat.your-org.com/oauth2/callback
```

## Provider configuration cheat sheet

### Google Workspace

```bash
OAUTH2_PROVIDER=google
OAUTH2_OIDC_ISSUER_URL=https://accounts.google.com
OAUTH2_CLIENT_ID=<your-google-client-id>
OAUTH2_CLIENT_SECRET=<your-google-client-secret>
OAUTH2_EMAIL_DOMAINS=your-org.com,partner-ngo.org
```

### Azure Entra ID (formerly AAD)

```bash
OAUTH2_PROVIDER=oidc
OAUTH2_OIDC_ISSUER_URL=https://login.microsoftonline.com/<tenant>/v2.0
OAUTH2_CLIENT_ID=<your-app-registration-id>
OAUTH2_CLIENT_SECRET=<your-app-registration-secret>
```

### Keycloak / Authentik / Dex (self-hosted)

```bash
OAUTH2_PROVIDER=oidc
OAUTH2_OIDC_ISSUER_URL=https://keycloak.your-org.com/realms/duecare
OAUTH2_CLIENT_ID=duecare
OAUTH2_CLIENT_SECRET=<from-keycloak-credentials-tab>
```

## Per-tenant configuration at server start

Operators with hundreds of tenants typically load tenant config from
a YAML file at startup:

```python
# in duecare-llm-server's startup hook
from duecare.server.metering import set_tenant_budget

for row in load_tenants_yaml("/etc/duecare/tenants.yaml"):
    set_tenant_budget(row["id"], row["daily_token_budget"])
```

YAML shape:

```yaml
tenants:
  - id: ngo-mfmw-hk
    daily_token_budget: 5_000_000
    rate_limit_per_min: 120
    concurrency: 30
  - id: ngo-pathfinders
    daily_token_budget: 1_000_000
    rate_limit_per_min: 60
    concurrency: 10
  - id: enterprise-acme
    daily_token_budget: 50_000_000
    rate_limit_per_min: 600
    concurrency: 100
```

The control plane that watches this YAML and pushes updates to a
running cluster is intentionally NOT in this repo — operators wire
it to their existing config-management stack (Argo CD, Flux,
Terraform Cloud).

## Per-tenant cost reporting

Roll up daily / monthly cost via PromQL:

```promql
# Top 10 tenants by output tokens last 24h
topk(10, sum by (tenant) (increase(duecare_model_tokens_out_total[24h])))

# Estimated USD spend per tenant last 30 days, with the cost-per-1k
# table joined client-side. Direct PromQL doesn't have a per-model
# cost table; instead, use a recording rule:
#
# - record: duecare:tenant_cost_usd_30d
#   expr: |
#     sum by (tenant) (
#       increase(duecare_model_tokens_in_total[30d]) / 1000 * 0.0005
#       + increase(duecare_model_tokens_out_total[30d]) / 1000 * 0.0015
#     )
# (replace 0.0005 / 0.0015 with per-model rates if you want exact)
```

For per-call cost (used by `duecare.server.metering.estimate_cost_usd`),
the lookup table lives at
[`packages/duecare-llm-server/src/duecare/server/metering.py`](../packages/duecare-llm-server/src/duecare/server/metering.py)
and is overridable via `DUECARE_MODEL_COSTS_FILE`.

## Auditing tenant-isolation correctness

After enabling tenancy, verify with:

```bash
# Generate test traffic from two tenants
for i in 1 2 3 4 5; do
  curl -s -H "X-Tenant-ID: tenant-a" http://localhost:8080/api/chat \
       -d '{"question":"test"}' >/dev/null
  curl -s -H "X-Tenant-ID: tenant-b" http://localhost:8080/api/chat \
       -d '{"question":"test"}' >/dev/null
done

# Confirm metrics are split per tenant
curl -s http://localhost:8080/metrics | grep duecare_chat_requests_total
# Expect two lines: ...{tenant="tenant-a",...} 5
#                   ...{tenant="tenant-b",...} 5

# Confirm rate limit counts independently
for i in $(seq 1 70); do
  curl -s -o /dev/null -w "%{http_code}\n" \
       -H "X-Tenant-ID: tenant-a" http://localhost:8080/api/chat \
       -d '{"question":"test"}'
done | sort | uniq -c
# Expect 60 200s + 10 429s for tenant-a; tenant-b is unaffected
```

If any of the above fails, the middleware order in
`packages/duecare-llm-server/src/duecare/server/app.py` is wrong —
TenancyMiddleware must be added LAST (Starlette runs middleware in
reverse-add order, so last added is innermost / runs first).
