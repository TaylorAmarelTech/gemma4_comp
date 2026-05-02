# Chief Architect — designing Duecare into your existing system

> **Persona.** Chief / principal architect at an enterprise. You
> care about how things compose: API surface, data flow, dependency
> direction, blast radius, future migration paths. You'll write
> the design doc that other architects review.
>
> **What this doc gives you.** The integration-pattern catalog,
> the API contracts at each boundary, the failure-isolation
> strategy, and the migration paths to other shapes if Duecare
> doesn't work out.

## The shape of Duecare from an architect's POV

Three loosely coupled tiers behind one HTTP API:

```
┌─────────────────────────────────────────────────────────────┐
│                   Your product surface                       │
│              (web / mobile / Slack / Discord / Twilio)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS, OpenAPI 3 schema
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   duecare-llm-server (FastAPI, stateless per request)        │
│                                                              │
│   ┌──── TenancyMiddleware ──── RateLimitMiddleware ────┐   │
│   │                                                      │   │
│   │   /api/chat       → assembler → engine → metering    │   │
│   │   /api/classify   → assembler → engine → metering    │   │
│   │   /api/research   → research-tools                   │   │
│   │   /api/pipeline   → assembler (returns the parts)    │   │
│   │   /metrics        → Prometheus                       │   │
│   │   /healthz        → liveness                         │   │
│   │                                                      │   │
│   └──────────────────────────────────────────────────────┘   │
└─────┬────────────────────┬───────────────────┬──────────────┘
      │ in-process         │ in-process        │ HTTP / gRPC
      ▼                    ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ duecare-llm- │  │  duecare-llm-    │  │  Model gateway       │
│ chat         │  │  research-tools  │  │  (Ollama / vLLM /    │
│ (harness)    │  │  (Tavily/Brave/  │  │   TensorRT-LLM /     │
│              │  │   Serper/DDG)    │  │   OpenAI / HF)       │
└──────────────┘  └──────────────────┘  └──────────────────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │  Gemma 4         │
                                       │  (E2B / E4B / 31B)│
                                       └──────────────────┘
```

Notes:
- **The harness layer is in-process** with the FastAPI server.
  `duecare-llm-chat` is a Python package the server imports; the
  GREP / RAG / Tools / Persona run on the same Python interpreter.
  This is by design — the harness must be unable-to-fail without
  the server failing in a known way.
- **The model gateway is over the network**. Today the bundled
  default is Ollama (in the same docker-compose); in production
  you'll point at your existing gateway via OpenAPI-compatible
  HTTP. Latency from chat tier → gateway is typically 10-50ms
  intra-cluster.
- **The research-tools layer is in-process AND outbound**. It
  makes HTTPS calls to Tavily / Brave / Serper / DuckDuckGo. The
  chat tier serializes outbound calls per request.
- **Tenant id flows from your edge proxy** as a header
  (`X-Tenant-ID` or `X-Forwarded-User`). All metrics, audit log
  rows, and rate-limit decisions key off it.

## Integration patterns

Pick one based on your existing architecture:

### Pattern A — Sidecar to your model gateway

If you already operate a model gateway (vLLM / TensorRT-LLM /
Together / Replicate / a custom inference service), Duecare
becomes a sidecar that wraps it:

```
client → your existing gateway client → Duecare /api/chat → your gateway → model
```

**Best for:** orgs with a mature model-serving stack who want to
add a safety harness without touching the inference layer.

**Compose:** the bundled `docker-compose.yml` minus the Ollama
service. Set `OPENAI_API_BASE` to your gateway. The chat tier
becomes a thin proxy + safety overlay.

### Pattern B — Replace your safety layer

If your current safety layer is rule-based regex + LLM moderation
+ a hand-maintained block list:

```
client → Duecare /api/classify → (your action layer)
```

**Best for:** orgs with a mature action layer (block / queue /
escalate) but a weak detection layer.

**Compose:** standalone Duecare deployment, called as a service
by your existing T&S pipeline. Replace your old safety service's
endpoint with `/api/classify`.

### Pattern C — Embed in your existing chat product

If your product surface IS chat (a Slack bot, a Discord bot, a
web chat widget):

```
client → your chat surface → Duecare /api/chat → render
```

**Best for:** orgs whose users are already chatting; you're
adding domain expertise to the chat.

**Compose:** standalone Duecare, called by your chat surface as
a backend. The bundled chat playground becomes a reference UI you
can copy patterns from but won't ship.

### Pattern D — Embed as a content-moderator at the post / message boundary

```
user submits → your moderation pipeline → Duecare /api/classify → allow/block/queue
```

**Best for:** marketplaces, social platforms, recruiting platforms,
job boards, classified-ad sites where user-generated content needs
real-time classification.

**Compose:** standalone Duecare, scaled per QPS. Use the
classification schema that matches your taxonomy.

### Pattern E — Off-line / batch analyzer

```
your pipeline → batch HTTP loop → Duecare /api/classify → annotate corpus
```

**Best for:** trust & safety teams analyzing existing content for
back-fill, audit, or rubric calibration.

**Compose:** Duecare deployed once, called from a batch script
running concurrent connections (the bundled rate limit + token
budget will throttle politely; raise per-tenant caps for batch
jobs).

## Data flow + retention

| Data | Lives in | Default retention | How to change |
|---|---|---|---|
| Request payload | Request only (not persisted by default) | Request lifetime | Operator can opt in to persistence via `DUECARE_PERSIST_REQUESTS=true` |
| Audit log row | `evidence-db` (SQLite default; Postgres in prod) | 90 days | `DUECARE_AUDIT_RETENTION_DAYS` env var |
| Per-tenant token counter | Prometheus counter (operator's TSDB retention) | Operator-defined | Prometheus retention |
| Distributed trace | OTel collector → operator's trace store | Operator-defined | Sampling at OTel collector |
| Chat history (Android only) | SQLCipher journal on device | unbounded | Worker's panic-wipe |

The audit-log row has the schema:

```python
{
  "request_id": "uuid",
  "timestamp": "ISO-8601",
  "tenant": "extracted from header",
  "model": "gemma4:e2b",
  "model_revision": "sha or vX.Y.Z",
  "prompt_hash": "sha256",
  "response_hash": "sha256",
  "harness_score": 0.85,
  "grep_hits": ["rule_id_1", ...],
  "rag_doc_ids": ["doc_id_1", ...],
  "tool_results": ["tool_name_1", ...],
  "ilo_indicators": [4, 8],
  "corridor_code": "PH-HK"
}
```

Prompt + response **plaintext are NOT in the audit log** — only
hashes. To get the plaintext, the request must have explicitly
opted in to persistence via header (`X-Persist-Plaintext: true`)
which is operator-gated.

## Failure isolation

Duecare is designed to fail in tiers:

1. **Model gateway down** — the bundled `SmartGemmaEngine` (in
   `duecare-llm-server`) falls through to a stub canned response.
   Chat surface stays up; quality degrades; your alert fires.
2. **Harness GREP / RAG layer fails** — falls through to "ungrounded
   model response" (cold model + question only). Lower quality, but
   still working.
3. **Tenancy middleware fails** — request gets attributed to
   `"public"` tenant. Audit log entry still created; metrics still
   stamped.
4. **Audit log write fails** — request is rejected with 503. We
   prefer to drop the request than process it without an audit
   trail.
5. **Rate limit middleware fails open** — rare; only happens if
   the in-process rate-limit store is corrupted (which would also
   drop your event loop). Effectively never seen in practice.

The contract: if the chat tier returns a 200, the audit log row
exists.

## Migration paths

### Out of Duecare to a hosted commercial alternative

Three things you'd need to migrate:

1. **The harness rules** — bundled GREP catalog + RAG corpus +
   tool-call patterns. Open source; portable.
2. **The audit log** — already in `evidence-db` via SQL; export
   via your normal Postgres tooling.
3. **The integration in your product** — it's HTTP / OpenAPI;
   point at the new vendor's URL.

Migration time: ~1 week if the new vendor supports the same
schema. ~4 weeks if you're rewriting the integration.

### Across model variants

Switch `DUECARE_OLLAMA_MODEL=gemma4:e4b` and rolling-restart the
chat tier. The harness layers don't depend on a specific model
revision (they work against any OpenAI-compatible endpoint).

### Across deployment topologies

| From | To | Effort |
|---|---|---|
| Topology A (single laptop) | Topology B (NGO-office Mac mini) | Same compose; new hardware |
| Topology B (single edge box) | Topology C (cloud server) | New Helm release; data import |
| Topology C (single region) | Topology C multi-region | Helm chart + multi-region routing (your existing geo-LB) |
| Topology C (cloud) | Topology B (back to on-prem) | Helm uninstall; same compose on edge box; restore data |
| Server-only | Server + on-device Android | Add the Android APK; configure Settings → Cloud model URL |

Each path is documented in [`docs/deployment_topologies.md`](../deployment_topologies.md).
The image is the same across all of them; only the compose / Helm
shape changes.

## Architecture decision records to read

- [ADR-001: Multi-package PyPI split](../adr/001-multi-package-pypi-split.md) — why 17 packages
- [ADR-002: Folder-per-module](../adr/002-folder-per-module-pattern.md) — why the source layout
- [ADR-003: On-device default; cloud opt-in](../adr/003-on-device-default-cloud-opt-in.md) — why the privacy posture
- [ADR-004: 6+5 notebook shape](../adr/004-six-plus-five-notebook-shape.md) — why the submission shape
- [ADR-005: Tenant id from edge proxy](../adr/005-tenant-id-from-edge-proxy.md) — why we don't bake auth in

These are decisions you might revisit; the ADR explains what was
considered and rejected so you can argue with the decision rather
than re-deriving it.

## Capacity model

The bundled Helm chart's defaults assume:

- 2 replicas minimum, 10 maximum (HPA on CPU + memory)
- 250m CPU request, 2000m limit per replica
- 512Mi memory request, 2Gi limit per replica
- Pod disruption budget: `maxUnavailable: 1`

For a baseline of ~10 sustained chat RPS on `gemma4:e2b` CPU:
- Chat tier: 8 replicas × 2 vCPU = 16 vCPU
- Model gateway: depends on your gateway's profile (Ollama on the
  same node ≈ another 8 vCPU; GPU pool ≈ 4 T4s)

Per-RPS sizing details + load test in
[`docs/considerations/capacity_planning.md`](../considerations/capacity_planning.md)
+ `tests/load/k6_chat.js`.

## Telemetry contract

Duecare exports OpenTelemetry traces + Prometheus metrics + structured
JSON logs. Each follows a stable contract:

### Spans

- `chat.handler` — the FastAPI endpoint
  - `harness.assemble` — building the prompt
    - `grep.match` — regex pass over question + journal context
    - `rag.retrieve` — BM25 over the corpus
    - `tools.lookup` — corridor / fee / NGO lookups
  - `model.generate` — calling the model gateway
  - `harness.score` — post-response scoring

Sampling: 1.0 in dev, 0.1 in prod (configurable).

### Metrics

Listed in [`docs/considerations/SLO.md`](../considerations/SLO.md).
The `tenant` label is on every metric for per-tenant chargeback.

### Logs

JSON per-line via structlog. The standard fields:
`{ts, level, request_id, tenant, route, message, ...event}`.
Plaintext prompts / responses NEVER in logs (the OTel collector's
`attributes/scrub` processor enforces this even if a developer
slips up).

## What to consciously NOT design around

These are decisions you'd be tempted to reverse but shouldn't:

- **Don't bake auth into the chat tier.** ADR-005. Use your edge
  proxy's identity. The `TenancyMiddleware` is the integration
  point.
- **Don't share state between requests.** Every request stands
  alone with its own tenant + audit row. Avoid in-process caches
  beyond the model+rule-catalog warm-up state.
- **Don't reimplement the GREP catalog in your own framework.** It's
  a content asset, not framework code. Use the bundled catalog
  and extend per [`docs/extension_pack_format.md`](../extension_pack_format.md).
- **Don't build a custom UI before measuring with the bundled one.**
  The chat playground is a reference. Measure your users against
  it before designing your own UI; your assumptions will be wrong
  in interesting ways.

## Adjacent reads

- [`docs/considerations/THREAT_MODEL.md`](../considerations/THREAT_MODEL.md) — STRIDE across 4 boundaries
- [`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md) — control map for inheritance
- [`docs/scenarios/enterprise_pilot.md`](./enterprise_pilot.md) — the platform-engineer view
- [`docs/scenarios/vp-engineering.md`](./vp-engineering.md) — the team-shape + 90-day plan
- [`docs/scenarios/it-director.md`](./it-director.md) — the operational TCO view
