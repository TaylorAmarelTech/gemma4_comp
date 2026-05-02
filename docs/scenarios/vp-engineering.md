# VP of Engineering — adopting Duecare across a product org

> **Persona.** You're VP / Director of Engineering at a 200-2000
> person tech company (a marketplace, a social platform, a recruiting
> tech, a fintech, a healthtech). Trust & Safety is bringing you a
> request: "we want a content-safety harness around the Gemma 4
> we're already running, sourced from open source, integrated with
> our existing stack."
>
> **What you actually need to decide.** Build vs adopt. Team to
> staff. Quarterly milestones. Ownership boundaries with adjacent
> teams (Trust & Safety, Platform, SRE, Security). Risk to the
> product roadmap.
>
> **What this doc gives you.** A 90-day adoption plan, the team
> shape, the integration boundaries, the metrics that prove it's
> working, and the predictable failure modes.

## TL;DR

| Decision | Recommendation |
|---|---|
| Build or adopt? | Adopt the harness; build only the integration into your product surface. |
| Team size for adoption | 1.5 FTE — 1 platform engineer + 0.5 product engineer + part-time PM |
| Time to MVP | 6 weeks |
| Time to GA | 12 weeks |
| Cross-team coordination | Trust & Safety (data + rubric), SRE (ops), Security (review), Platform (infra) — kickoff with all four in week 1 |
| Year-1 cost (people) | ~$300-500k loaded in salary |
| Year-1 cost (infra) | ~$5-50k depending on RPS |
| Risk to roadmap | Low if you stage it as a Trust & Safety side-pipe; medium if you make it a hard dependency for a launch |

## Build vs adopt

**Build a content-safety harness from scratch:** ~6-9 months,
2-3 FTE, ~50% chance of shipping something useful in year 1, ~80%
chance you reinvent the layers (regex catalog + RAG + tool calls +
multi-tier scoring) that already exist in Duecare's open-source
implementation.

**Adopt Duecare:** ~6-12 weeks, 1.5 FTE, the layers are already
there. Your team's time goes into:
1. Integration with your product surface (your client UI, your
   identity stack, your data pipeline)
2. Custom domain extensions specific to your business (your own
   GREP rules, your own RAG corpus, your own fee-table lookups
   if you're in a regulated marketplace)
3. Ops + on-call + telemetry hookup

The math favors adoption unless you have a unique constraint
(air-gapped FedRAMP-High deployment with no allowed open-source
deps; an existing in-house harness already at parity).

## The team shape

### Platform engineer (1.0 FTE)

Owns the Duecare deployment + integration into your stack.
Background: backend / SRE / DevEx-adjacent. Uses Docker, Helm,
Terraform / Pulumi, and your existing observability stack. They:

- Stand up the Helm release in your dev / staging / prod clusters
- Wire `TenancyMiddleware` to your OIDC / IAM
- Configure metric scraping into your existing Prometheus / Datadog
- Hook up the runbook to PagerDuty / Opsgenie
- Pin image SHA + cosign verification in admission

### Product engineer (0.5 FTE)

Owns the integration of Duecare's HTTP API into your product
surface. Background: full-stack, comfortable with FastAPI / OpenAPI
schemas. They:

- Generate a typed client from `https://your-deploy/openapi.json`
- Add the chat / classify / pipeline endpoints to whatever your
  product UI is (React widget? Slack bot? in-app modal?)
- Wire per-user feedback ("this answer was wrong") into your
  existing event-tracking
- Build any custom UI that wraps the bundled chat surface

### Part-time PM (0.25 FTE)

Owns the rubric — what's "good enough" for your specific Trust &
Safety use case. They:

- Define the 10-20 prompt + expected-response pairs that count as
  the launch gate
- Coordinate with T&S for the canonical examples + the failure
  modes that matter
- Sign off on the launch metric thresholds
- Review weekly metric trends post-launch

### Ad-hoc consultations

- **Security** review: 1 day in week 2, 1 day in week 8 (final
  approval). Hand them `docs/considerations/COMPLIANCE.md` +
  `docs/considerations/THREAT_MODEL.md` + the vendor questionnaire.
- **SRE** integration: 2 days in week 4 to wire the Helm chart's
  ServiceMonitor into your existing Prometheus + the runbook into
  your incident process.
- **Trust & Safety** corpus contribution: 2 days in week 6 to
  hand-grade 50-100 prompts in your specific domain.
- **Legal** review: 1 day in week 8 if your product handles
  user-uploaded content (DPA implications).

## 90-day plan

### Week 1-2: Stand up + first chat

**Goals.** Duecare deployed in dev. Platform engineer has a working
chat against your internal model gateway.

**Steps.**
- Day 1-3: Helm chart in dev k8s, multi-tenant config from your IAM
- Day 4-7: ServiceMonitor wired, baseline metrics in Grafana
- Week 2: First 10-prompt smoke test (use the bundled `tests/load/k6_chat.js`)

**Done when:** `make doctor` passes in dev cluster.

### Week 3-4: Integrate with product

**Goals.** The product engineer has a working integration with one
internal user-facing surface.

**Steps.**
- Generate typed client from OpenAPI spec
- Add a hidden internal-only feature flag exposing the chat to your
  T&S team
- Wire feedback signal (thumbs up/down or per-response rating)
- Add per-user attribution via `X-Tenant-ID` header from your IAM

**Done when:** 5 internal users can chat with the harness through
your product surface, telemetry shows their requests in Grafana.

### Week 5-6: Trust & Safety rubric

**Goals.** PM + T&S have a written rubric for "ready to launch".

**Steps.**
- T&S hand-grades 50-100 prompts in your domain (they know what
  good looks like; their grading is the rubric)
- PM defines launch thresholds (e.g., p95 latency < 5s, refusal
  rate on harmful prompts > 95%, no PII leaks in audit log over
  10k requests)
- Custom GREP rules for your domain via [`docs/extension_pack_format.md`](../extension_pack_format.md)
  if needed

**Done when:** rubric is in a Notion / Google Doc, signed off by
T&S lead.

### Week 7-8: Production cutover

**Goals.** Behind a feature flag, served to 1% of real users.

**Steps.**
- Helm release in prod NS with HPA + PDB + NetworkPolicy
- Image pinned to SHA, cosign verification in admission
- OAuth-proxy (or your existing auth mesh) in front
- 1% rollout via your existing feature-flag system (or Duecare's
  bundled `feature_flags.py` for stable per-tenant bucketing)
- On-call rotation engaged

**Done when:** 1% of traffic is going through Duecare for one week
without paging.

### Week 9-12: Ramp + measure

**Goals.** 100% rollout. Quarterly metric report to leadership.

**Steps.**
- 1% → 10% → 50% → 100% with 1-week soaks at each step
- Per-week metric review against the launch thresholds
- Monthly cost report (per-tenant token rollup)
- Incident post-mortems for any > P2 issue

**Done when:** It's just the way the product works now.

## Cross-team boundaries

### With Trust & Safety

- **They own**: the rubric, the corpus extensions, the per-incident
  rule additions
- **You own**: the platform, the deployment, the SLOs
- **Shared**: weekly review of incident → rule additions backlog

### With SRE

- **They own**: pager rotation, runbook execution, capacity
  decisions when you cross load-test thresholds
- **You own**: app-level health (the chat tier; not the model
  gateway, not the underlying k8s)
- **Shared**: SLO definition + alert tuning (`docs/considerations/SLO.md`)

### With Security

- **They own**: the security review process, the threat-model walk-through,
  the vendor questionnaire approval
- **You own**: implementing whatever they ask (cosign verify,
  network policy, mTLS, etc.)
- **Shared**: post-incident security review

### With Platform / Infra

- **They own**: the model gateway (vLLM / TensorRT-LLM / Ollama
  pool), the k8s cluster, the secret manager
- **You own**: configuring Duecare to talk to their gateway
- **Shared**: capacity planning when Duecare's load shape changes
  the gateway's RPS profile

## Metrics that prove it's working

Top-line, in priority order:

1. **Harness lift** — for your T&S team's hand-graded rubric, what
   percentage of prompts get a "better" response with Duecare on
   vs off? The published number for trafficking-specific prompts
   is +56.5 pp mean across 207 prompts ([`docs/harness_lift_report.md`](../harness_lift_report.md));
   yours will differ by domain.
2. **Per-tenant token cost** — `duecare_model_tokens_out_total` rolled
   up per tenant per day, multiplied by your internal cost-per-1k.
   Should be predictable + within budget.
3. **Latency p95** — < 8s for E2B, < 16s for E4B. Your SLO.
4. **Error rate** — < 0.5% per the bundled SLO.
5. **Audit-log completeness** — 100% of requests with full
   provenance chain.
6. **Saved-time per case / per user / per session** — your own
   custom metric. Caseworkers using the harness for refund-claim
   prep save ~2 hours per case (per [`docs/scenarios/caseworker_workflow.md`](./caseworker_workflow.md)).

## Predictable failure modes

| Failure | Why it happens | How to avoid |
|---|---|---|
| Launch slips to month 6 | Coupling Duecare adoption to a hard product launch deadline | Stage it as a side-pipe T&S tool first, then ramp to product surface |
| Cost surprises in month 2 | Enabled cloud Gemma fallback without per-tenant cap | Set `DUECARE_RATE_LIMIT_PER_MIN` + tenant token budgets BEFORE enabling cloud fallback |
| T&S can't tell if it's working | No rubric defined | Week 5-6 is non-negotiable. PM owns this. |
| Security review takes 12 weeks | Started conversation in week 8 | Day-1 hand off the threat model + compliance docs |
| Engineers reimplement the harness | "Just use the regex catalog and skip Gemma" | Set the rule: ship the bundled harness first, optimize after measurable demand |
| Two teams own the deployment | Platform + Product both want it | Designate the Platform engineer as DRI on day 1; Product owns the integration only |

## What you'll show your CEO at the end of the quarter

A one-page report:

- **What we shipped**: chat / classify / pipeline integration in
  product, gated by T&S rubric, 1% → 100% rolled out
- **Lift**: +N percentage points on the T&S rubric (your domain's
  numbers, not the bundled trafficking numbers)
- **Cost**: $X / month, $Y / 1000 requests, on track for $Z annual
- **Reliability**: N nines uptime, P incidents, T median MTTR
- **What we learned**: the 3 most surprising patterns the harness
  caught + the 1 false-positive class we're still tuning

The numbers come from the bundled metrics; the narrative is yours.

## Adjacent reads

- [`docs/scenarios/enterprise_pilot.md`](./enterprise_pilot.md) — the platform-engineer-level pilot plan
- [`docs/scenarios/chief-architect.md`](./chief-architect.md) — design integration patterns
- [`docs/scenarios/it-director.md`](./it-director.md) — TCO + ops view
- [`docs/considerations/`](../considerations/) — the full governance set
- [`docs/considerations/enterprise_readiness.md`](../considerations/enterprise_readiness.md) — pillar-by-pillar gap analysis

## When NOT to adopt

Honest counsel:

- **You're sub-50 employees** — the deployment overhead doesn't
  amortize. Use the public Kaggle notebooks for evaluation; come
  back when you have a real Trust & Safety function.
- **Your domain is fully covered by an existing T&S vendor**
  (Microsoft Azure Content Safety, OpenAI Moderation, Hive,
  Sift, etc.) and switching costs > 6 months — keep what you have
  and revisit when contract renewal hits.
- **You don't have a model gateway** — adopt a model gateway first
  (vLLM / TGI / Together / Replicate). Duecare assumes one exists.
- **You can't dedicate 1.5 FTE for a quarter** — defer.

The bundled harness only earns its keep when you have a Trust &
Safety problem, an LLM in production, and a team that can own
both ends.
