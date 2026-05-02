# Cross-NGO trend sharing without sharing PII

> **Problem.** A trafficking pattern lights up across 12 NGOs in
> the PH-HK corridor — all in the same week. None of them know.
> Each NGO sees only their own caseload. By the time anyone
> publishes a regional report, the recruiter has moved 50 more
> workers through the same pipeline.
>
> **What this proposes.** A privacy-preserving federation protocol
> that lets NGOs (and regulators, and ILO regional offices) share
> *aggregate trend signal* without sharing protected PII or
> revealing individual cases. Built on top of the existing
> Duecare audit-log + per-tenant counter infrastructure.
>
> **Status.** Architecture + protocol design (this doc). Reference
> implementation outline below. Production deployment requires
> coordination with a hosting partner (ILO, Polaris, Anti-Slavery
> International, or a regional consortium). **Not yet running.**
> File issues + PRs to advance the design.

## Privacy contract — what's shared vs not

The hard rule: **only aggregated counts of harness signals leave the
contributing NGO**. Specifically what's shared:

| Field | Shared? | Type | Example |
|---|---|---|---|
| Case narrative text | **Never** | n/a | n/a |
| Worker name / age / nationality | **Never** | n/a | n/a |
| Recruiter name / employer name | **Never** | n/a | n/a |
| Specific dates of incidents | **Never** | n/a | n/a |
| Tenant id / NGO id | Pseudonymous, optional | string | `sha256("polaris-org-id" + secret)` truncated |
| Corridor code | Yes | string | `"PH-HK"` |
| GREP rule IDs that fired | Yes | string | `"passport-withholding"` |
| Severity of fired rules | Yes | enum | `"critical"` |
| ILO indicator numbers triggered | Yes | int 1-11 | `8` |
| Count of cases per (corridor, rule, week) | Yes | int | `12` |
| Week (ISO 8601 week) | Yes | string | `"2026-W18"` |
| Aggregate-only — never per-case rows | enforced | n/a | n/a |

**What an attacker who compromised the central aggregator could
learn:** that NGO X reported 12 passport-withholding cases on the
PH-HK corridor in week 2026-W18. They cannot learn who any of those
12 workers are, who the recruiter was, or any specifics. The
maximum disclosure is the count + the corridor + the week.

**What an attacker who compromised a contributing NGO could
learn:** anything in that NGO's local audit log (which they could
already learn). The federation protocol doesn't add new attack
surface to the contributing NGO.

## Protocol — what flows on the wire

```
┌─────────────── NGO 1 (Mac mini in office) ───────────────┐
│                                                            │
│  Local Duecare deployment                                  │
│   - Audit log: per-decision provenance (hashes only)       │
│   - Prom counters: per-rule + per-corridor + per-tenant    │
│                                                            │
│  Weekly export job (cron):                                 │
│   1. Read last week's `duecare_grep_rule_hits_total` +     │
│      `duecare_ilo_indicator_hits_total` +                  │
│      `duecare_corridor_lookups_total`                      │
│   2. Bucket by (corridor, rule_id, severity, week)         │
│   3. Apply differential-privacy noise (Laplace, ε=1.0)     │
│   4. Sign payload with NGO's Ed25519 contribution key       │
│   5. POST signed JSON to central aggregator                │
│                                                            │
└────────────────────────────┬───────────────────────────────┘
                             │ HTTPS (TLS pinned to aggregator cert)
                             │ JSON payload, ~5-50 KB / NGO / week
                             ▼
┌──────────────── Central aggregator ─────────────────────────┐
│  (Hosted by ILO, Polaris, ASI, or a federated consortium)   │
│                                                              │
│  - Verify signature against NGO's registered Ed25519 pubkey  │
│  - Drop payloads from non-registered NGOs (rate-limit too)   │
│  - Insert rows into per-week aggregate table                 │
│  - On each batch: recompute regional rollups                 │
│  - Publish public read-only dashboard                        │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ Read-only public dashboard
                           ▼
┌──────────────────── Public consumers ────────────────────────┐
│                                                                │
│  Contributing NGOs see:                                       │
│   "Last week, fee-camouflage on PH-HK was up 40% across       │
│    12 NGOs reporting"                                          │
│                                                                │
│  Researchers see anonymized aggregates                         │
│  Regulators see corridor-level trends                          │
│  Journalists see public dashboard for stories                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Payload format

JSON, each row = one (corridor, rule_id, severity, week) bucket.
NGO submits ~10-50 rows per week.

```json
{
  "schema_version": "1.0",
  "submitter": {
    "id": "abc123def456...",
    "name_optional": "Mission for Migrant Workers HK",
    "country_code": "HK"
  },
  "submitted_at": "2026-05-04T03:00:00Z",
  "covers_week": "2026-W18",
  "signature": "base64(ed25519_sig(...))",
  "rows": [
    {
      "corridor": "PH-HK",
      "rule_id": "passport-withholding",
      "severity": "critical",
      "ilo_indicator": 8,
      "raw_count": 12,
      "noised_count": 12.7,
      "epsilon": 1.0
    },
    {
      "corridor": "PH-HK",
      "rule_id": "training-fee-camouflage",
      "severity": "high",
      "ilo_indicator": 4,
      "raw_count": 23,
      "noised_count": 22.3,
      "epsilon": 1.0
    },
    {
      "corridor": "ID-HK",
      "rule_id": "wage-deduction-to-lender",
      "severity": "critical",
      "ilo_indicator": 4,
      "raw_count": 8,
      "noised_count": 8.1,
      "epsilon": 1.0
    }
  ]
}
```

The `noised_count` is what's published. The `raw_count` is included
inside the signed envelope so the aggregator can audit the noise
calibration; aggregator MUST drop `raw_count` before any storage
or downstream forwarding (verified by code review + the aggregator
being open source).

## Differential privacy budget

For each (corridor, rule_id, week) bucket, NGO adds Laplace noise
`Lap(b)` with `b = 1/ε`. Default `ε = 1.0`:
- Standard deviation of noise: `√2 / ε ≈ 1.41` cases per bucket
- Counts ≥ 5 are recoverable with high confidence
- Counts of 1-2 are essentially noise (privacy preserved)

Why this matters: a recruiter who knows of one specific complaint
to a specific NGO can't determine whether it was reported in the
weekly upload, because the noise dominates at low counts.

NGOs with very high case volume (regional umbrella organizations)
may want stricter `ε = 0.5`; small NGOs typically use default `ε = 1.0`.
Configurable per-NGO at registration time.

## Per-NGO contribution registration

Onboarding flow (one-time per NGO):

1. NGO downloads the `duecare-llm-trends-federation` package + reads
   this doc + reviews the open-source aggregator source code.
2. NGO generates an Ed25519 keypair locally:
   ```bash
   duecare trends keygen --org-name "Mission for Migrant Workers HK"
   # writes private key to ~/.duecare/trends.key
   # writes public key to stdout for registration
   ```
3. NGO emails the **public key** + organization name + contact to the
   aggregator operator (e.g., Anti-Slavery International). The
   aggregator's terms of participation are public (MOU template
   included with the package).
4. Aggregator operator adds the public key to the registry. Future
   submissions from that NGO are accepted.
5. NGO sets up the weekly cron job:
   ```bash
   # Add to /etc/cron.d/duecare-trends-export
   0 3 * * 1 duecare trends export --since=last-week --submit
   ```

NGOs can opt out anytime by stopping the cron job. The aggregator
holds no leverage — NGO's data is local; only the noised aggregates
have ever left.

## Aggregator design

The aggregator is a small FastAPI service:

```python
# packages/duecare-llm-trends-federation/aggregator/server.py
@app.post("/contributions")
async def receive(payload: dict):
    # Verify signature
    pubkey = REGISTRY.get(payload["submitter"]["id"])
    if not pubkey or not verify(pubkey, payload):
        raise HTTPException(403)
    # Rate-limit per NGO (1 submission per hour)
    if rate_limit_exceeded(payload["submitter"]["id"]):
        raise HTTPException(429)
    # Drop raw_count BEFORE any storage
    rows = [
        {k: v for k, v in row.items() if k != "raw_count"}
        for row in payload["rows"]
    ]
    db.insert_aggregate(rows, payload["covers_week"], payload["submitter"]["id"])
    return {"received": len(rows)}

@app.get("/dashboard")
def public_dashboard():
    # Read-only public view of regional rollups
    return {
        "by_corridor": db.rollup_by_corridor(),
        "by_rule": db.rollup_by_rule(),
        "by_week": db.timeseries_by_week(),
    }
```

Hosted as a Hugging Face Space, on Render, or self-hosted by
the aggregator operator (ILO / Polaris / ASI). Source is open;
operators can be audited.

## What NGOs can learn back

After 2 weeks of contributions, the public dashboard surfaces:

- **Per-corridor trend lines** — "passport-withholding cases up 40%
  on PH-HK this month vs last 3 months"
- **Per-rule rollups** — "fee-camouflage is the most-fired rule
  globally this quarter (1,247 hits across 47 NGOs)"
- **Cross-NGO comparison** — "your NGO's debt-bondage rate is in
  the 75th percentile of contributing NGOs on the same corridor"
- **Early-warning signal** — "new pattern emerging on KE-SA: 6
  NGOs reported critical-severity hits in the past 2 weeks for a
  rule that fired only 1× in all of Q1"

Each of these is computed without any NGO ever sharing a worker's
name, a recruiter's name, or a case narrative.

## Threat model — what could go wrong

| Threat | Mitigation |
|---|---|
| Compromised NGO submits fake counts to skew the dashboard | Per-NGO rate limits + outlier detection at aggregator + ability to revoke a NGO's pubkey |
| Compromised aggregator leaks who reported what | Aggregator is open source + can be self-hosted by the participating consortium |
| Re-identification of small NGOs via singular reporting | Suppress aggregates with < 3 contributing NGOs per (corridor, rule, week); or apply k-anonymity at aggregator |
| Pattern signature reveals which case was reported | Differential-privacy noise + bucketing at week granularity (not day) |
| Aggregator operator subpoenaed for raw data | Aggregator never receives raw data — only noised aggregates. Subpoena yields nothing identifying. |
| NGO leaks their own private key | Revocation flow + audit log of submissions per pubkey |

## Reference implementation outline

A new package: `packages/duecare-llm-trends-federation/`

```
duecare-llm-trends-federation/
├── pyproject.toml              # depends on duecare-llm-evidence-db
├── README.md                   # public-facing, this design doc lives here
├── src/duecare/trends/
│   ├── __init__.py
│   ├── exporter.py             # weekly export + Laplace noise
│   ├── signer.py               # Ed25519 sign/verify
│   ├── client.py               # POST to aggregator
│   ├── cli.py                  # `duecare trends keygen / export / submit`
│   └── aggregator/
│       ├── server.py           # FastAPI receiving service
│       ├── registry.py         # known-NGO pubkey registry
│       ├── rollups.py          # per-corridor / per-rule / per-week aggregations
│       └── dashboard.py        # public read-only view
└── tests/
    ├── test_dp_noise.py
    ├── test_signing.py
    └── test_aggregator_rejects_unsigned.py
```

Estimated effort: ~3-5 days for a working implementation, ~2 weeks
including the test suite + a deployable Hugging Face Space for the
aggregator.

## What's NOT in scope (yet)

- **Federated learning across NGO models.** Each NGO trains its
  own (or uses the bundled) GREP / RAG pack. We're not federating
  model weights; only counts. (Future v2 — but adds substantial
  complexity.)
- **Cross-NGO case-record matching.** "Did NGO 1's case 47 and
  NGO 2's case 102 involve the same recruiter?" — requires Private
  Set Intersection (PSI) on hashed recruiter names. PSI primitives
  are mature; integration is non-trivial. (Future v2.)
- **Real-time alerting across NGOs.** Current design is weekly
  batch. Real-time would need a streaming aggregator + careful
  rate-limit + DP composition analysis. (Future v3.)
- **Cross-border worker case-handoff.** When a worker moves from
  NGO 1's catchment to NGO 2's, how does case continuity work?
  Out of scope here; that's a worker-portability problem (potentially
  solved via the worker's own Android app journal).

## Adoption pathway

For this to actually exist:

1. **Get one anchor partner.** Anti-Slavery International, Polaris,
   IJM, or an ILO regional office agrees to host the aggregator.
2. **Publish the package.** `duecare-llm-trends-federation` on PyPI.
3. **Pilot with 5-10 NGOs.** Run for 8 weeks. Verify the signal
   is useful + the privacy is intact.
4. **Open public dashboard.** After pilot, the aggregator's public
   dashboard goes live.
5. **Iterate on rule pack.** Patterns the federation surfaces become
   inputs to the bundled GREP rule pack updates.

This is a 6-12 month roadmap item, not a hackathon-week deliverable.
But the architecture is sound + the protocol is implementable
today + the privacy contract is honest.

## Adjacent reads

- [`docs/considerations/THREAT_MODEL.md`](considerations/THREAT_MODEL.md) — STRIDE for the local Duecare deployment
- [`docs/considerations/multi_tenancy.md`](considerations/multi_tenancy.md) — per-NGO tenant isolation today
- [`docs/research_server_architecture.md`](research_server_architecture.md) — the continuous-research server design
- Apple's [Differential Privacy Overview](https://www.apple.com/privacy/docs/Differential_Privacy_Overview.pdf)
- Google's [RAPPOR paper](https://research.google/pubs/rappor-randomized-aggregatable-privacy-preserving-ordinal-response/) — reference for population-statistics differential privacy
