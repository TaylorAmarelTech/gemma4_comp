# Path 3 — Government API integration (bulk processing path)

For a government agency that wants DueCare's analysis behind its
existing case-management system rather than as a field workbench.
Your intake desk receives complaints, ads, contracts, or interview
transcripts; your system POSTs them to a DueCare API on internal
infrastructure; the analysis is added to the case record without
the operator changing tools.

This is the back-office complement to the field workbench at
[`03_government_workbench.md`](03_government_workbench.md). Many
agencies will deploy both.

## What you get

A FastAPI service from `packages/duecare-llm-server/` that exposes
a small set of internal endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/triage/ad` | Analyse a job ad / recruitment posting |
| `POST /api/triage/contract` | Analyse an employment / recruitment contract |
| `POST /api/triage/interview` | Analyse an intake-desk interview transcript |
| `POST /api/triage/chat` | Analyse a worker-recruiter chat conversation |
| `POST /api/templates/render` | Produce a draft administrative notice from a case bundle |
| `GET /api/knowledge/lookup` | Look up corridor cap / statute citation / NGO contact |
| `GET /api/health` | Liveness probe for your monitoring |
| `GET /api/audit/<request_id>` | FOIA-style audit trace lookup |

The service is stateless. Raw inputs come in, structured analysis
goes out. The service does not persist case content outside the
audit trace (hashes only).

## Request and response shape

Example: triage a recruitment contract.

```http
POST /api/triage/contract HTTP/1.1
Content-Type: application/json
Authorization: Bearer <internal-token>

{
  "request_id": "case-2026-05-22-1234",
  "content_type": "contract_text",
  "content": "{...verbatim contract text or OCR output...}",
  "jurisdiction": "dmw-ph",
  "locale": "en-PH",
  "case_metadata": {
    "corridor": "PH-SA-DW",
    "complainant_role": "worker",
    "case_intake_at": "2026-05-22T10:15:00Z"
  }
}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "request_id": "case-2026-05-22-1234",
  "audit_trace_id": "trace-9f8c4d2",
  "model_version": "gemma-4-e4b@0.1.0",
  "knowledge_pack_version": "2026-05-22-jurisdiction-dmw",
  "indicators": [
    {
      "id": "fee_camouflage_training_medical_advance",
      "severity": "high",
      "evidence_excerpt": "...verbatim quote from contract...",
      "citation": "POEA MC 14-2017 Sec. 3(a); ILO C181 Art. 7"
    }
  ],
  "statute_violations": [
    {
      "statute": "POEA MC 14-2017",
      "section": "3(a)",
      "verbatim_text": "...",
      "agency_action_options": ["administrative_penalty", "license_review"]
    }
  ],
  "suggested_actions": [
    {"action": "issue_show_cause_notice", "template": "dmw_show_cause_notice_v3"},
    {"action": "refer_to_legal_unit", "reason": "high_severity_indicator_present"}
  ],
  "confidence": 0.87,
  "latency_ms": 412
}
```

## Deployment topology

```
┌───────────────────────────────────────────────────────────────┐
│ Agency case-management system (existing)                      │
│  - intake desk staff                                          │
│  - case officer dashboard                                     │
│  - legal review queue                                         │
└───────────────────────────────────────────────────────────────┘
                            │  HTTPS POST (internal network only)
                            ↓
┌───────────────────────────────────────────────────────────────┐
│ DueCare API service (duecare-llm-server)                      │
│  - internal load balancer + auth                              │
│  - 2 to 4 worker pods, each with Gemma 4 E4B loaded           │
│  - knowledge pack: tuned for THIS jurisdiction                │
│  - stateless: no case content stored beyond audit hashes      │
└───────────────────────────────────────────────────────────────┘
                            │
                            │  (internal-only)
                            ↓
┌───────────────────────────────────────────────────────────────┐
│ Audit archive (agency's existing tamper-evident log store)    │
│  - hash-chained audit traces                                  │
│  - retention per agency policy                                │
└───────────────────────────────────────────────────────────────┘
```

## Authentication and authorisation

- **Internal-only.** Service binds to internal network interface;
  no public ingress. Your case-management system is the only
  authorised client.
- **Bearer token** in the `Authorization` header. Token rotated
  per agency security policy.
- **Per-endpoint scopes** via the token: `triage:read`,
  `templates:render`, `audit:read`. Scopes enforced server-side.
- **Optional mTLS** for agencies that require client-cert
  authentication between internal services.

## Latency budget

| Endpoint | Target p50 | Target p95 |
|----------|------------|------------|
| `/api/triage/ad` | 300 ms | 800 ms |
| `/api/triage/contract` | 600 ms | 1.5 s |
| `/api/triage/interview` | 900 ms | 2.5 s |
| `/api/triage/chat` | 800 ms | 2.0 s |
| `/api/templates/render` | 1.2 s | 3.0 s |
| `/api/knowledge/lookup` | 50 ms | 200 ms |

Targets assume Gemma 4 E4B running on a T4-class GPU or equivalent.
Knowledge lookups are deterministic and do not invoke the model.

## Capacity planning

For an agency processing ~10,000 cases per month:

| Resource | Quantity | Notes |
|----------|----------|-------|
| Worker pods | 4 (active) + 1 (standby) | Each pod: 1 GPU, 16 GB VRAM, 64 GB RAM |
| Throughput | ~5 requests/sec sustained | Bursts to ~15 req/sec |
| Storage | 200 GB total (audit log + knowledge pack mirrors) | Per region |
| Backup | Daily snapshot to agency archive | Standard ops |

Smaller agencies (fewer than 1,000 cases/month) can run a single
pod on a workstation with consumer GPU.

## Integration with your case-management system

Three integration patterns, pick whichever matches your existing
architecture:

1. **Synchronous inline analysis.** Intake desk officer hits "Save"
   on the case form; your system POSTs to `/api/triage/*` and
   waits for the response (< 2 seconds typical); analysis is
   attached to the case before the officer's next click. Best UX,
   highest latency sensitivity.

2. **Asynchronous queue.** Intake desk officer saves the case; your
   system enqueues an analysis job; DueCare API processes it in
   the background; result is attached when ready (typically
   < 10 seconds). Best for high-volume intake, can absorb latency
   spikes.

3. **Periodic batch.** Cases accumulate; a nightly job POSTs each
   to `/api/triage/*`; analyses attached the next morning. Best
   for legacy systems that can't be modified.

## Data flow (what crosses each boundary)

| Boundary | What crosses |
|----------|--------------|
| Case-management system → DueCare API | Verbatim case content (contract text, interview transcript, chat content, ad text); case metadata (corridor, role, timestamps) |
| DueCare API → model | Verbatim content, in-memory only; never written to disk on the API host |
| DueCare API → audit archive | SHA-256 hash of content, request/response IDs, model + knowledge pack versions, statute citations returned. Never raw content |
| DueCare API → case-management system | Structured analysis JSON (indicators, citations, actions). Original content not echoed back |
| Anything → public internet | Nothing. The API service has no external egress |

## Procurement bullet points

- **License:** MIT. No per-call fee. Self-hosted indefinitely.
- **Vendor lock-in:** None. JSON API is documented; alternative
  servers can speak the same protocol. Knowledge pack format is
  open.
- **Data residency:** All data stays on agency infrastructure. No
  outbound calls.
- **Audit:** Hash-chained audit log, exportable for FOIA / right-
  to-information requests.
- **Performance:** Real-time analysis (< 1 second p50 for ads;
  < 2 seconds p50 for contracts) on commodity GPU hardware.
- **Disaster recovery:** Stateless service; restart from snapshot
  in minutes. Knowledge pack and model weights are open and
  reproducible.
- **Source:** `github.com/TaylorAmarelTech/gemma4_comp`. Agency
  self-hosts a private fork.

## What can go wrong + how to handle it

| Failure | Mitigation |
|---------|------------|
| Case-management system sends a payload exceeding the API's input limit | API rejects with a clear error; case-management system chunks the input |
| GPU node fails | Load balancer routes to remaining nodes; pod replaced from snapshot in < 5 minutes |
| Knowledge pack update breaks a citation | Roll back to previous knowledge pack version (it's immutable + versioned). Agency's quarterly tuning review prevents this from reaching production |
| Audit archive fills | Standard archive rotation per agency policy. Audit log is small (hashes + metadata only); years of data fits in modest storage |
| Bearer token leaks | Rotate token; all old requests with the leaked token are flagged in audit log |
| Case-management system expects a synchronous response, but model is overloaded | API responds with 503 + retry-after header; case-management system queues to retry |

## Pilot checklist (90 to 180 days)

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Procurement + IT security review | 30 to 90 days | Signed deployment approval |
| Network + auth setup | 5 days | Service reachable from case-management system, no public ingress |
| Jurisdiction tuning | 5 days | `duecare-jurisdiction-<agency>-config.yaml` checked into agency repo |
| Integration with case-management | 10 to 20 days | Intake desk submits one case, gets analysis attached |
| Shadow run | 30 days | Service processes real intake in parallel with current process; analysts compare; no enforcement decisions based on it |
| Limited production | 30 days | Service results visible to case officers; enforcement decisions still require human sign-off |
| Full production | Ongoing | Service results are part of standard case workflow |

## See also

- [`03_government_workbench.md`](03_government_workbench.md) — the
  field-inspector path; same software, different surface
- [`03_government_jurisdiction_tuning.md`](03_government_jurisdiction_tuning.md) —
  the tuning pass both paths share
- `packages/duecare-llm-server/` — the FastAPI service source
- `.claude/rules/10_safety_gate.md` — PII handling applicable to
  case content
