# Duecare vs the alternatives

> Honest comparison against the commercial + open-source content
> safety options procurement teams ask about. We're not trying
> to win every column — for some use cases, an alternative
> genuinely fits better. The matrix tells you when.

## What you'd be comparing

The alternatives evaluators typically consider:

| Class | Examples |
|---|---|
| **Big Tech moderation APIs** | Google Cloud Natural Language Moderation, Azure Content Safety, AWS Comprehend, OpenAI Moderation API |
| **Trust & Safety vendors** | Hive, Sift, ActiveFence, Spectrum Labs, Two Hat / Microsoft Community Sift, Tremau |
| **Open-source frameworks** | Llama Guard 3, NeMo Guardrails (NVIDIA), LangChain content-safety chains, ShieldGemma (Google) |
| **In-house build** | Your engineering team + 6-18 months |

Duecare sits between **open-source frameworks** and **in-house
build** — we're a fully-implemented harness around Gemma 4 with
domain content baked in (ILO indicators, migration corridors,
recruitment-fee statutes). Use the matrix to figure out if that
specific shape fits.

## The matrix

| Dimension | Big Tech APIs | T&S Vendors | Llama Guard / ShieldGemma | NeMo Guardrails | Duecare | In-house |
|---|---|---|---|---|---|---|
| **Cost (small NGO)** | $0-100/mo | $1k-10k/mo | $0 + compute | $0 + compute | $0 + compute | $300k-1M to build |
| **Cost (enterprise)** | $1k-50k/mo | $10k-100k/mo | $0 + compute | $0 + compute | $0 + compute | Sunk cost forever |
| **Data leaves your infra** | Yes (their cloud) | Yes (their cloud) | No | No | No | No |
| **Open source** | No | No | Yes | Yes | Yes (MIT) | Yes (yours) |
| **Domain-tuned for trafficking / migrant labor** | No | Some (Spectrum, ActiveFence) | No | No | **Yes** | Maybe |
| **Citation-grounded outputs** | No | Some | No | Yes (with custom config) | **Yes** (statute + ILO) | Maybe |
| **Multi-language** | Yes | Yes | Yes | Yes (model-dependent) | Yes (Gemma 4 multilingual) | Maybe |
| **Audit log per decision** | Limited | Yes | Self-implement | Self-implement | **Yes** | Yes |
| **Per-tenant rate-limit + chargeback** | No | Some | Self-implement | Self-implement | **Yes** | Yes |
| **Deploy on-prem / air-gapped** | No | Rare | Yes | Yes | **Yes** | Yes |
| **Time to first response in production** | 1 day | 4-12 weeks | 1 week | 2-4 weeks | 1 day to 6 weeks | 6-18 months |
| **Customizability of detection rules** | Low | Medium | Medium | High | **High** | Highest |
| **Worker-facing mobile app included** | No | No | No | No | **Yes** (Android v0.9) | DIY |
| **Maintained by** | Vendor team | Vendor team | Open-source community | NVIDIA | One open-source maintainer | You |

## When NOT to use Duecare

Honest counsel — sometimes a different tool fits better:

### Use a Big Tech moderation API instead when

- You need **a single REST call** for general content moderation
  (CSAM, hate speech, generic violence) and the trafficking-specific
  domain isn't your priority
- You're already deep in one cloud (GCP / AWS / Azure) and want
  one vendor invoice
- You don't want to operate any container infrastructure
- Your scale is **5k+ requests/sec** and the per-call latency of
  the Big Tech endpoint matters more than data residency

Examples: Google Cloud Natural Language Moderation, Azure Content
Safety, OpenAI Moderation API.

### Use a T&S vendor instead when

- You need a **mature human-review queue + escalation workflow**
  bundled with the detection (Sift, Hive, Spectrum Labs)
- You need a **vendor SLA with contractual remedies** (you're
  not OK with "best effort, MIT license, no warranty")
- Your trust & safety team wants **off-the-shelf rule packs** for
  20+ harm categories without building each one
- Procurement is comfortable with $50k-500k/year contracts and
  prefers vendor risk over self-host risk

Examples: Hive, Sift, ActiveFence, Spectrum Labs, Two Hat.

### Use Llama Guard / ShieldGemma instead when

- You want **just a content-classifier model** (no harness, no
  domain tooling, no journal) wrapped around your existing chat
- You're already running Llama 3 or Gemma 2 and want a guard model
  from the same family
- You don't need citation-grounded reasoning — just yes/no
  classification

### Use NeMo Guardrails instead when

- You want a **declarative, framework-grade** way to define
  guardrails that compose with LangChain / LlamaIndex / your own
  agent framework
- You have an NVIDIA GPU stack and want their tuning advantages
- Your domain isn't migrant trafficking specifically — NeMo is
  domain-agnostic

### Build in-house instead when

- Your domain is **specific enough** (e.g., your platform has its
  own content categories not in any public taxonomy) that 6-18
  months of in-house work pays back
- You have the **engineering capacity** (3+ FTEs minimum) and
  **roadmap commitment** (2+ years)
- You need **vendor-zero** for regulatory or geopolitical reasons

## When Duecare specifically fits

Choose Duecare when most of these are true:

- ✅ Your domain is **migrant-worker safety**, **trafficking
  prevention**, **labour-recruitment compliance**, or an adjacent
  use case where the bundled rule pack + corpus matter
- ✅ You need **on-prem / air-gapped** capability (NGO offices,
  regulators, legal aid clinics with privilege concerns)
- ✅ You want **explainable outputs** — the Pipeline modal shows
  exactly which rule + which corpus doc + which tool fired for
  each response
- ✅ You're comfortable running **Docker Compose** or **k8s** in
  your own environment
- ✅ Cost ceiling matters — you can't pay $10k-100k/year SaaS
- ✅ You want **per-tenant cost attribution** + per-tenant rate
  limits (chargeback, multi-NGO sharing, per-caseworker isolation)
- ✅ You need a **mobile app for workers** (Android v0.9 is
  shipping)
- ✅ You're OK with **community support** (GitHub issues, no
  paid SLA, single-maintainer project)

## Hybrid patterns

Duecare composes with other tools — these aren't either/or
choices:

### Duecare + Big Tech API

Use Duecare for the trafficking domain + a Big Tech API for
generic harms (CSAM, hate speech, spam). Multiple
classification calls per message; combine results in your action
layer.

### Duecare + T&S vendor's review queue

Use Duecare's `/api/classify` for detection; pipe the results
into your existing T&S vendor's review queue. You get domain
expertise + the vendor's mature workflow.

### Duecare + your in-house tools

Use Duecare's open-source harness layers (GREP / RAG / Tools)
inside your in-house framework. The packages are MIT — fork the
GREP catalog or the RAG corpus into your own service.

## Cost worked example: 200 caseworkers, 50k chats/month

| Approach | Year-1 cost |
|---|---|
| Azure Content Safety + OpenAI GPT-4o for chat | ~$4k Azure + ~$2k OpenAI = **~$6k/yr** |
| Hive Moderation enterprise | ~$30k-60k contract |
| Sift trust & safety platform | ~$60k-150k contract |
| In-house build (3 FTE × 12 months) | ~$600k-1.2M |
| **Duecare on a small cloud server** | **$0 license + ~$300/yr cloud** |
| **Duecare on a single Mac mini** | **$600 hardware + $0 cloud = ~$600 one-time** |

The cost gap is real. The trade-offs are also real (no vendor SLA,
single-maintainer project, you operate the infra).

## Decision framework

Run this on a Friday afternoon — should be a 30-minute call:

1. **What's our trafficking-specific use case?** If "none, we just
   need general moderation" → use a Big Tech API. Stop here.
2. **Can we run a Docker container?** If "no, we're fully SaaS" →
   use a T&S vendor.
3. **Can we live with community support + MIT license?** If "no,
   we need a contract with remedies" → use a T&S vendor.
4. **Do we need worker-facing mobile?** If "yes" → Duecare's
   Android app is unique to it.
5. **Are we ≥ 50k QPS?** If "yes" → benchmark Duecare against
   alternatives at that scale; some Big Tech APIs handle scale
   better.
6. **Is data residency mandatory?** If "yes" → Duecare or in-house
   only.

If you're left holding Duecare after these 6 questions, the
[`docs/scenarios/`](./scenarios/) folder has the persona walkthrough
for your role.

## What we're NOT comparing on

These are real differences but not deciding factors for most
evaluators:

- **Inference latency** — depends on model + hardware, roughly
  comparable across Gemma 4 / Llama 3 / Claude Haiku / GPT-4o-mini
- **Per-prompt accuracy** — every classifier has prompts it gets
  wrong; benchmark against your domain
- **Maintainer brand** — most procurement teams don't actually
  weight this heavily once SLA is comparable
- **Specific technical features** that everyone now has (streaming,
  multi-modal, function calling)

## See also

- [`docs/considerations/vendor_questionnaire.md`](./considerations/vendor_questionnaire.md) — pre-filled CAIQ answers for procurement
- [`docs/considerations/COMPLIANCE.md`](./considerations/COMPLIANCE.md) — control-map crosswalk
- [`docs/scenarios/`](./scenarios/) — persona-specific walkthroughs once you've decided
- [`docs/harness_lift_report.md`](./harness_lift_report.md) — quantified results on the trafficking domain
