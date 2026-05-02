# Threat model

> **Method.** STRIDE applied to the four trust boundaries of a
> production Duecare deployment. Each entry: **threat**, **affected
> component**, **impact**, **mitigation today**, **residual risk**.
>
> **Audience.** Security review teams, NGO IT staff, anyone considering
> Duecare for adoption inside a regulated environment. Pairs with
> [`docs/considerations/COMPLIANCE.md`](./COMPLIANCE.md) (control mappings) and
> [`docs/considerations/runbook.md`](./runbook.md) (incident response).

## Trust boundaries

```
                              ┌──────── External ────────┐
                              │                          │
                              │ Worker / NGO browser     │
                              │ Embedded chat client     │
                              │ Telegram / Messenger /   │
                              │   WhatsApp gateway       │
                              │                          │
                              └─────────────┬────────────┘
                                            │ HTTPS
                          ╭─────── Boundary 1: edge ─────╮
                          │                              │
                          │  oauth2-proxy / Cloudflare   │
                          │  Access / NGINX-ldap-auth    │
                          │                              │
                          ╰──────────────┬───────────────╯
                                         │ HTTP (in-mesh)
                          ╭─── Boundary 2: app server ───╮
                          │                              │
                          │  duecare-llm-server          │
                          │  - TenancyMiddleware          │
                          │  - RateLimitMiddleware        │
                          │  - RequestMetricsMiddleware   │
                          │                              │
                          ╰──────────────┬───────────────╯
                                         │ HTTP / gRPC
              ╭─────────── Boundary 3: workload pool ───────────╮
              │                                                  │
              │  Ollama (local model)                            │
              │  duecare-llm-research-tools (web search)         │
              │  evidence-db (Postgres / SQLite)                 │
              │                                                  │
              ╰──────────────────────────────────────────────────╯
                                         │ HTTPS
                          ╭── Boundary 4: 3rd-party APIs ─╮
                          │                                │
                          │  Tavily / Brave / Serper       │
                          │  HuggingFace Inference          │
                          │  OpenAI / Anthropic / Google    │
                          │  (only if cloud routing on)    │
                          │                                │
                          ╰────────────────────────────────╯
```

Each boundary is a place where data crosses from one trust domain
into another, and where input must be validated + output must be
attested.

## STRIDE — Boundary 1: Edge (untrusted internet → reverse proxy)

| Threat (STRIDE) | Risk | Mitigation today | Residual |
|---|---|---|:-:|
| **S**poofing of a tenant identity | A request claims `X-Tenant-ID: alice@ngo.org` but isn't authenticated | When `docker-compose.auth.yml` is on, oauth2-proxy strips client-supplied X-Tenant-ID and only forwards `X-Forwarded-User` it set itself. Without auth, X-Tenant-ID is trusted — appropriate for single-tenant deployments only. | Low |
| **T**ampering with prompt content in transit | MITM injects a worse prompt before it reaches Gemma | TLS 1.3 at the edge; HSTS recommended; Cloudflare / oauth2-proxy enforce HTTPS; certificate pinning recommended for the Android client | Low |
| **R**epudiation of an action | Tenant later denies sending a request that produced harmful output | Per-request audit log: `(timestamp, tenant, prompt_hash, response_hash, model, model_revision, harness_score, grep_hits, rag_doc_ids)` | Low — non-repudiation requires the audit log to be tamper-evident; today it isn't append-only-signed |
| **I**nformation disclosure of other tenants' data | Per-tenant audit log row leaks via search / API | DB row-level security recommended for Postgres deployments; today the SQLite default is single-schema and operator must enforce isolation at the proxy layer | **Medium** — closed by RLS / partitioning |
| **D**enial of service | Single tenant exhausts the inference pool | Per-tenant token bucket + concurrency cap in RateLimitMiddleware; healthz / metrics paths exempt; Prometheus alert `DuecareTokenBudgetExhausted` warns at 80% | Low |
| **E**levation of privilege | Worker request escalates to admin endpoint | No admin endpoints in the chat surface; control-plane operations (set tenant budget, etc.) are out-of-band today | Low |

## STRIDE — Boundary 2: Reverse proxy → app server

| Threat | Risk | Mitigation today | Residual |
|---|---|---|:-:|
| Spoofing | App server thinks a request came from oauth2-proxy when it didn't | NetworkPolicy default-deny + explicit allow only from the proxy pod label; in-mesh mTLS recommended via Istio / Linkerd | Low |
| Tampering | Headers added/modified between proxy + app | mTLS between proxy + app; oauth2-proxy `OAUTH2_PROXY_REVERSE_PROXY=true` mode trusts X-Forwarded-* only when set inside the trust boundary | Low |
| Repudiation | App handler doesn't log enough to attribute a decision | Every chat / classify / research request stamped with tenant + request id; 90-day audit retention default | Low |
| Information disclosure | App caches a previous tenant's data and serves it to another | App is stateless per request; per-request state lives only on `request.state`; no in-process caching of tenant data | Low |
| DoS | Single replica gets all traffic from the proxy | HPA + multiple replicas; PodDisruptionBudget keeps `maxUnavailable: 1` | Low |
| EoP | Cross-tenant access via in-process state | TenancyMiddleware writes to `request.state.tenant_id` per request; never globals | Low |

## STRIDE — Boundary 3: App server → workload pool (Ollama / DB / research-tools)

| Threat | Risk | Mitigation today | Residual |
|---|---|---|:-:|
| Spoofing | App talks to a malicious Ollama imitating the real one | NetworkPolicy restricts egress to the named in-cluster Ollama service; mTLS recommended via service mesh | Low |
| Tampering | Model weights tampered with on disk | SHA-256 verify on Android v0.6+ model download; Ollama image pulled from official `ollama/ollama:latest` over TLS; pin to a specific tag in production | Low |
| Repudiation | Model returned X but app logs Y | App logs the exact response bytes + prompt hash; cross-checkable with model server's own logs (`OLLAMA_DEBUG=1`) | Low |
| Information disclosure | Prompts leak into the model server's logs / on-disk cache | Ollama doesn't persist prompts by default; `OTEL_LOGS_EXPORTER=none` if extra cautious; the harness's `attributes/scrub` processor hashes `prompt`/`response`/`user_id` before they reach the OTel trace store | Low |
| DoS | Model server runs out of GPU memory and OOM-kills | HPA on the chat tier handles spikes; healthcheck on Ollama; alert `OllamaDown` | Low |
| EoP | Prompt-injection makes Gemma exfiltrate data via tool calls | Tool calls in the harness are deterministic (no agentic loop in core 6); A4 (`chat-playground-with-agentic-research`) is opt-in + sandboxed (DuckDuckGo + URL-fetch only, no shell) | **Medium** — requires explicit opt-in; defended by tool allowlist + PIIFilter on outbound queries |

## STRIDE — Boundary 4: Workload pool → 3rd-party APIs (only if cloud routing on)

| Threat | Risk | Mitigation today | Residual |
|---|---|---|:-:|
| Spoofing | DNS hijack points the cloud Gemma URL at an attacker | Operator chooses + signs the cloud endpoint; certificate pinning recommended; for the Android app, the Settings → Cloud model URL is explicit and TLS-pinned per the network_security_config | Low |
| Tampering | Outbound search query rewritten in transit | TLS 1.3; DNSSEC on the operator's resolver | Low |
| Repudiation | Operator can't prove what was sent to Tavily | `_audit()` in `duecare-llm-research-tools.fast_search` logs every outbound; retention configurable | Low |
| **Information disclosure** | The user's **prompt** + **chat history** reaches a third party | This is the LOAD-BEARING privacy boundary. By default, NO 3rd-party traffic. Opt-in via Settings → Cloud model on Android, or env vars on the server. The `attributes/scrub` OTel processor hashes prompt + response before they leave the cluster as traces. The PIIFilter in research-tools rejects outbound queries containing names / passport numbers / phone numbers per `pii_filter.py` | **HIGH** — closed only by NOT enabling cloud routing |
| DoS | 3rd party rate-limits us; chat surface degrades | SmartGemmaEngine fallback chain (Cloud → MediaPipe → Stub); the fallback is documented in the worker-facing UI | Low |
| EoP | 3rd party returns an attacker's payload that causes the harness to behave maliciously | All 3rd-party responses pass through the same harness scoring as the local model; no bypass | Low |

## Cross-cutting threats

### Supply chain

| Risk | Mitigation today |
|---|---|
| Malicious dependency in a wheel | All 17 wheels built from this repo; `dependabot` or `renovate` recommended for upstream pin updates; cosign signing of the GHCR image (workflow wired) |
| Malicious model weights | Android downloads SHA-256 verify; Ollama models pulled from `ollama/ollama` registry over TLS; pin to specific digests in production |
| Compromise of GitHub Actions runner | All workflows scoped to least privilege; secrets stored in GitHub Secrets; cosign-signed builds attested to the runner identity |

### Insider threat

| Risk | Mitigation today |
|---|---|
| Operator-side admin reads tenant audit log | Per-tenant audit log shard recommended for high-sensitivity deployments; access reviewed quarterly per SOC 2 CC6.2 (operator responsibility) |
| Compromised operator account exfiltrates models | Models are public Apache 2.0 — no exfiltration risk for Gemma 4 weights themselves; the value sits in tenant data, which is protected per the boundary 3 controls above |

### Side channels

| Risk | Mitigation today |
|---|---|
| Inference timing reveals which GREP rules fired | The chat surface emits per-token streaming, so timing is roughly uniform; the Pipeline modal explicitly discloses which rules fired (no security-by-obscurity) |
| Cache occupancy reveals other tenants' prompts | App is stateless; KV cache lives in Ollama's process and isn't accessible to the chat tier |
| Embedding distance reveals proprietary RAG corpus content | RAG corpus is public (ILO + POEA + Polaris citations); no proprietary corpus today |

## What's explicitly out of scope

These are operator responsibilities Duecare doesn't try to solve:

- **End-user device security** — if the worker's phone is compromised,
  the SQLCipher journal key in Android Keystore is exposed; that's
  outside the harness threat model.
- **NGO operational security** — Duecare doesn't audit the NGO's
  staff training, physical security, or vetting process.
- **Network operator surveillance** — TLS 1.3 + cert pinning protect
  content; metadata (who's talking to whom) is the user's network
  operator's domain.
- **Legal compulsion** — a court order requiring decryption of the
  Android journal must be addressed by the worker / NGO with their
  lawyer; the panic-wipe primitive is the only defense in the app.

## Scoring (CVSS 3.1 base proxy)

| Threat | Score (estimated) |
|---|---|
| Boundary 1 cross-tenant data leak (sans RLS) | 6.5 (Medium) |
| Boundary 3 prompt-injection exfiltration via agentic A4 | 5.4 (Medium) |
| Boundary 4 cloud-routing prompt disclosure (if enabled without informed consent) | 8.2 (High) |
| Supply-chain compromise of GHCR image | 7.0 (High) — assuming cosign isn't verified |
| All other boundaries' threats | < 4.0 (Low) |

The two practical priorities for an operator with a sensitive deployment:

1. **Turn cloud routing OFF unless you have a specific reason** (covered
   by Settings on Android; on the server, leave the default).
2. **Pin the GHCR image to a SHA digest + verify cosign signature** in
   your Helm values and your image-pull policy.

## Updating this document

Re-review:

- Whenever a new feature touches one of the trust boundaries
- After any security incident (post-incident addition)
- Quarterly along with `docs/considerations/SLO.md`

Next review: **2026-08-01**.
