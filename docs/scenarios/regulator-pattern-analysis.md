# Government regulator — pattern analysis at scale

> **Persona.** You're a labor-recruitment regulator: POEA / DMW
> in the Philippines, BMET in Bangladesh, BP2MI in Indonesia, DoFE
> in Nepal, the Saudi Ministry of Human Resources, the HK Labour
> Department, an MOM enforcement officer in Singapore. You receive
> hundreds of complaints per month. You need to triage them,
> identify repeat-offender recruiters, and produce evidence
> packets that your inspectors can act on.
>
> **What this gives you.** A way to run the harness against your
> existing complaint queue, get back structured pattern detection
> + statute citations + recommended action, and roll up to a
> per-recruiter dashboard your inspectors trust.

## TL;DR

| You'd normally... | With Duecare you... |
|---|---|
| Read complaints one at a time, manually flagging patterns | Batch-classify in seconds; the rules + ILO indicators are pre-coded |
| Cite the wrong section of the same regulation 3 times in a year | The statute citation is consistent across every classification |
| Lose track of which recruiter has had 5 prior complaints | Per-recruiter rollup in the dashboard |
| Spend 30 min drafting a complaint-disposition letter | Generate a draft from the structured analysis in 30 seconds |
| Reactive, complaint-driven enforcement | Proactive — feed Facebook job-group scrapes through the same pipeline |

## What it is, in regulator terms

The harness is a **classifier + research assistant + drafting tool**
trained on the public statute corpus you already enforce:

- **Your own regulations** (POEA MCs, BMET fee schedules, BP2MI
  Permenakers, DoFE FEAs, etc.) — pre-loaded for the 6 corridors
  the bundled corpus covers
- **ILO conventions** that your country has ratified
- **Case patterns** from open-source enforcement actions

It does NOT have:
- Your internal complaint database
- Your prior dispositions
- Your inspector notes

You wire it to those via the OpenAPI 3 schema. Common integration:
your existing case management system POSTs each new complaint to
Duecare's `/api/classify`, gets back structured findings, files
them in the case record.

## Three workflows

### Workflow 1: Single-complaint triage

A worker walks in with a complaint. Your front-desk officer:

1. Logs into the on-prem Duecare dashboard
2. Pastes the worker's narrative into the chat
3. The harness returns:
   - Which patterns fired (passport withholding, fee camouflage,
     debt bondage, etc.)
   - The controlling regulation + section number from your country
   - The ILO indicator number(s)
   - Recommended action (refer to inspector vs criminal referral
     vs civil refund-claim path)
   - Recommended NGO partners for shelter / counsel referral

The dashboard auto-tags the case with the patterns. Your inspector
queue picks it up.

### Workflow 2: Batch classification

You have 5,000 backlogged complaints from the last 6 months. A
script POSTs each to `/api/classify` overnight. By morning:

- Per-complaint classification with controlling-statute citation
- Per-recruiter rollup: which recruiters appear N times, with which
  patterns
- Per-corridor heatmap: which corridors generate the most
  passport-withholding complaints
- Per-inspector workload: how to distribute the triage queue

The bundled rate limit + token budget protect your model gateway
from being saturated by the batch job. Use a separate tenant id
for the batch job (`tenant=batch-2026-q2`) to keep its load
attribution clean.

### Workflow 3: Proactive scraping

Your enforcement unit runs a script that scrapes Facebook recruitment
groups, Telegram channels, and online job boards for posts about
overseas employment. Each post goes through `/api/classify`.

Posts that fire critical-severity rules (e.g., "training fee" +
"zero-fee corridor" → fee-camouflage violation) get auto-routed
to your inspector queue with the structured finding attached.

This converts your enforcement posture from reactive (complaints
only) to proactive (you find violations before workers do).

## Set-up shape

Use the [NGO-office-edge topology](./ngo-office-deployment.md)
or the [Topology C cloud server](../deployment_topologies.md#topology-c--server--thin-clients)
depending on your IT environment:

| Your environment | Topology |
|---|---|
| Single office, ≤ 20 inspectors | NGO-office-edge (Mac mini / NUC on the LAN) |
| Multi-office, single country | Topology C on your government cloud (AWS / Azure / GCP gov) |
| Inter-agency (multiple ministries) | Topology C with per-ministry tenant ids |
| Air-gapped (high-security mandate) | NGO-office-edge with no internet egress; corpus updates via signed extension packs |

Per-tenant config:

```yaml
# /etc/duecare/tenants.yaml
tenants:
  - id: poea-airb           # POEA Anti-Illegal Recruitment Branch
    daily_token_budget: 50_000_000
    rate_limit_per_min: 600
    concurrency: 50
  - id: poea-overseas        # POEA Overseas Employment Welfare Office
    daily_token_budget: 20_000_000
    rate_limit_per_min: 300
    concurrency: 30
  - id: batch-2026-q2        # Quarterly batch reclassification
    daily_token_budget: 200_000_000
    rate_limit_per_min: 1200
    concurrency: 100
```

Per-tenant audit log + per-tenant cost rollup so each unit can be
chargedback by your finance office.

## Custom domain pack for your jurisdiction

The bundled corpus covers 6 corridors (PH-HK, ID-HK, PH-SA, NP-SA,
BD-SA, ID-SG). For your specific regulator's jurisdiction, you'll
likely add:

- **Your country's specific MCs / regulations** (recent ones the
  bundled corpus doesn't have yet)
- **Your country's specific licensed-recruiter database** (so a
  named recruiter resolves to a license-status check)
- **Your country's specific complaint disposition templates**
  (the bundled refund-claim template is a starting point, not
  your actual letter format)

This is done via the [extension pack format](../extension_pack_format.md):
a signed zip of new GREP rules + RAG corpus docs + tool definitions
that gets loaded at server startup. Update with `kubectl rollout
restart deploy duecare-chat` (or `make demo` for the on-prem variant).

## Integration with your existing case management

Whatever you run today (a custom .NET / Java app, Salesforce
Public Sector, a SharePoint-based system, a CRM), the integration
point is HTTP:

```python
# Your existing case-management code, with one new step:
import requests

def on_new_complaint(complaint):
    # Classify via Duecare
    resp = requests.post(
        "https://duecare.your-ministry.gov/api/classify",
        json={"text": complaint["narrative"]},
        headers={"X-Tenant-ID": complaint["unit"], "Authorization": f"Bearer {API_TOKEN}"},
    )
    findings = resp.json()

    # Attach to the case record
    complaint["auto_classification"] = findings["classification"]
    complaint["auto_grep_hits"] = findings["grep_hits"]
    complaint["auto_recommended_action"] = findings["recommended_action"]
    complaint["auto_statute_citations"] = findings["citations"]

    # Route per the recommended action
    if findings["severity"] == "critical":
        route_to_priority_queue(complaint)
    else:
        route_to_normal_queue(complaint)
```

The `/api/classify` shape returns a stable JSON envelope you can
deserialize into your existing data model.

## Auditability + due process

Three properties that matter for a regulator:

### 1. Every classification is traceable

The audit log row includes `(prompt_hash, response_hash, model,
model_revision, grep_hits, rag_doc_ids, tool_results)`. If a
recruiter contests a finding, you can re-run the classification
on the same model revision and get the same answer.

### 2. Every cited statute is verifiable

The harness shows you which RAG document supports each citation.
The corpus is open-source. A defendant's lawyer can audit the
corpus and contest specific citations.

### 3. The human is always in the loop

The harness produces a draft + recommended action; your inspector
issues the actual disposition. The draft is editable. The
disposition is signed by a human inspector, with the harness's
output attached as supporting analysis (not as the decision).

This satisfies most administrative-law requirements that automated
decisions affecting a regulated person be subject to human review.

## Per-recruiter rollups

The Prometheus counter `duecare_grep_rule_hits_total{rule_id, severity}`
keys off rule IDs but not (today) off recruiter names. To track
per-recruiter patterns:

1. Stamp each complaint with a `recruiter_id` (from your licensee
   database) before posting to `/api/classify`.
2. Add a custom Prometheus counter incremented by your case-management
   side after classification: `complaints_per_recruiter{recruiter_id, pattern}`.
3. Grafana dashboard: top-10 recruiters by critical patterns last
   90 days.

When a recruiter crosses an internal threshold (5 critical patterns
in 90 days, say), your enforcement unit gets paged. Convert from
"react to complaints" to "investigate the top 10 worst actors
proactively."

## Cost (for a national-scale regulator)

| Scale | Sizing | Monthly cost |
|---|---|---|
| 50,000 complaints/year | 1 mid-size cloud server, CPU only | ~$50/mo |
| 500,000 complaints/year | 4-replica chat tier + GPU pool for batch reprocessing | ~$1500/mo |
| 5M complaints/year (proactive scraping) | Multi-region k8s + dedicated GPU pool | ~$10k/mo |

For most national labor regulators, the middle tier covers it.
$1.5k/mo is well within procurement-by-purchase-order for any
ministry-level office.

## Compliance with civil-service procurement

Duecare's open-source MIT license + zero-vendor-dependency posture
make it usable in environments where commercial SaaS is restricted.
Specifically:

- **No data leaves the deployment** — satisfies local data-residency
  rules
- **Open-source code** — passes most government source-code-availability
  requirements
- **No subscription** — no procurement contract to draft / renew
- **Forkable** — if Duecare maintainers go away, your IT keeps
  running the image you already pulled

For a formal procurement file, [`docs/considerations/vendor_questionnaire.md`](../considerations/vendor_questionnaire.md)
pre-fills the standard CAIQ-Lite / SIG-Lite questions.

## What this enables that wasn't possible before

- **Inspector workload distribution by pattern severity** — instead
  of round-robin or seniority, route critical patterns to your
  most-experienced inspectors
- **Automated quarterly enforcement reports** — generate from the
  audit log + rollup metrics
- **Cross-corridor pattern detection** — a recruiter who's clean
  in your data but has 12 critical patterns from another country's
  data; if you share via a regional inter-regulator agreement, the
  harness output is immediately structurally compatible
- **Faster complaint-to-disposition cycle time** — most clinics
  report 60% reduction after wiring the harness into intake

## Adjacent reads

- [`docs/scenarios/lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) — what counsel does with the same intake
- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — the on-prem deployment pattern
- [`docs/considerations/multi_tenancy.md`](../considerations/multi_tenancy.md) — per-unit tenant isolation
- [`docs/extension_pack_format.md`](../extension_pack_format.md) — adding your country's specific regulations
