# Email oracle reference design — server-side knowledge solicitation

> **Implementation status, verified 2026-07-28:** this page is a future
> reference design, not a description of a deployed mail agent. The current
> public hub can detect gaps, match address-hash/topic profiles, draft a
> campaign, and vet a manually forwarded observation. It stores no raw
> recipient addresses and therefore cannot send. `scripts/hermes.py` is a
> separate propose-only model discovery daemon; it is not an SMTP/IMAP adapter
> and does not contact civil-society members. No `duecare-llm-oracle` package,
> mail container, automated delivery receipt, or collected human-rating result
> exists in the maintained repository.

## Why email and nothing else

Civil society stakeholders (NGO caseworkers, lawyers, journalists,
hotline volunteers, regulatory inspectors) already manage 5 to 15
accounts for their day job. Asking them to remember one more login
to "contribute to a knowledge hub" is the single fastest way to
ensure they never contribute.

**The constraint, in plain English:** "Civil society doesn't have
the ability to remember another login or account." (Taylor,
2026-05-22.)

The oracle inverts the contribution model:

- **Old model (broken):** Stakeholder must remember to log in to
  the hub, find the right page, write a contribution, submit. Zero
  participation.
- **New model (oracle):** Stakeholder receives a targeted email
  asking a specific knowledge question. They reply when they have
  time. The oracle parses the reply into a knowledge envelope and
  routes it to the curator queue.

Email is universal. Email is asynchronous. Email is already in
their inbox.

## Architecture sketch

```
┌────────────────────────────────────────────────────────────────┐
│ DueCare knowledge layer (451 GREP, 859 RAG, 38 corridor caps)  │
│                                                                │
│ Gap detector: identifies knowledge that needs verification     │
│  - corridor cap last verified > 6 months ago                   │
│  - GREP rule flagged for review by curator                     │
│  - RAG doc with broken citation                                │
│  - new statute published by regulator (web scrape)             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Oracle agent (server-side, hourly cron)                        │
│  - matches gap to subscriber expertise                         │
│  - composes targeted email                                     │
│  - sends via SMTP                                              │
│  - logs sent record                                            │
└────────────────────────────────────────────────────────────────┘
                            ↓ SMTP outbound
                            ↓
                   ┌──────────────────┐
                   │ Stakeholder inbox│
                   └──────────────────┘
                            ↓ (replies when they have time)
                            ↓ IMAP inbound
┌────────────────────────────────────────────────────────────────┐
│ Oracle inbox processor (hourly cron)                           │
│  - polls oracle@... inbox                                      │
│  - parses replies: structured (REPLY: YES) or freeform (Gemma) │
│  - generates knowledge envelope (path 2 schema)                │
│  - routes to curator queue                                     │
│  - sends acknowledgement email back to contributor             │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Curator review queue → Friday cut → published pack             │
│ Contributor receives an "envelope merged" confirmation email   │
└────────────────────────────────────────────────────────────────┘
```

## Subscriber model

Subscribers opt in by emailing `subscribe@<network>.duecare.example`
with a one-line description of their role and corridors of
expertise. The oracle replies with a structured confirmation.

```
From: maria@damayan.example
To: subscribe@gaatw.duecare.example
Subject: Sign up

I'm a caseworker at Damayan in NYC, handling PH-US H-2B and PH-Saudi
domestic worker cases. Happy to verify corridor caps and review
GREP rules in those corridors.

---

From: oracle@gaatw.duecare.example
To: maria@damayan.example
Subject: Welcome to DueCare GAATW Oracle (please confirm)

Hi Maria,

You signed up to receive knowledge-verification emails from the
DueCare GAATW knowledge hub. We registered you for:

- Role: caseworker
- Organisation: Damayan
- Corridors of expertise: PH-US (H-2B), PH-Saudi (domestic worker)

We will email you no more than 1 to 2 times per month with
targeted questions about these corridors. Reply STOP at any time
to unsubscribe.

To confirm your subscription, reply CONFIRM to this email.

Thank you,
DueCare GAATW Oracle
```

Subscriber record (server-side):

```json
{
  "subscriber_id": "sub-2026-05-22-9f8c4d2",
  "email": "maria@damayan.example",
  "role": "caseworker",
  "organisation": "Damayan",
  "corridors_of_expertise": ["PH-US-H2B", "PH-SA-DW"],
  "opt_in_at": "2026-05-22T14:30:00Z",
  "opt_in_confirmed": true,
  "opt_in_envelope_types": ["grep_rule", "corridor_fee_cap", "ngo_contact"],
  "language_preference": "en",
  "email_frequency_cap": "2_per_month",
  "unsubscribed_at": null
}
```

## Outbound email: gap-question template

The oracle composes ONE targeted question per email. No batching of
unrelated questions. One question, one decision, one reply.

```
From: oracle@gaatw.duecare.example
To: maria@damayan.example
Subject: PH-Saudi domestic worker fee cap — verification needed

Hi Maria,

You signed up to help verify DueCare's knowledge for PH-Saudi
domestic worker corridors.

We have the PH-Saudi placement fee cap recorded as PHP 0 (employer-
paid only) per POEA MC 14-2017, last verified 2024-08-15. It's been
over 9 months — is this still accurate?

Reply with ONE of:

  REPLY: YES                  — cap is still PHP 0, no change
  REPLY: NEW: <amount>        — the cap has changed; tell us what it is
  REPLY: SOURCE: <url>        — point us to the regulator's current notice
  REPLY: SKIP                 — you don't have current info; we will ask someone else
  REPLY: STOP                 — unsubscribe from oracle emails

Free-form replies are fine too; we'll do our best to interpret.

Thanks,
DueCare GAATW Oracle

(Question id: q-2026-05-22-corridor-ph-sa-fee-cap)
```

## Inbound parsing rules

The oracle inbox poller processes replies in three tiers:

### Tier 1: structured reply (regex match)

The first line of the reply matches a `REPLY: <verb>(?:\s+(.*))?`
pattern. Handle deterministically:

| Verb | Action |
|------|--------|
| `YES` | Envelope: "corridor cap verified unchanged" + new verification timestamp |
| `NO` | Envelope: "corridor cap claimed stale; awaiting NEW or SOURCE" — pings subscriber for follow-up |
| `NEW: <value>` | Envelope: `corridor_fee_cap` update with the new value; provenance = subscriber + question id |
| `SOURCE: <url>` | Envelope: "source link provided; needs curator citation verification" |
| `SKIP` | No envelope; subscriber's question count is incremented |
| `STOP` | Set `unsubscribed_at` on subscriber record; send confirmation |
| `CONFIRM` | Set `opt_in_confirmed = true` on subscriber record |

### Tier 2: structured reply with substance (Gemma 4 NLP)

If Tier 1 matches `NEW`, `SOURCE`, or no verb at all, the freeform
text gets a Gemma 4 pass:

```
prompt = """
Subscriber {subscriber_id} replied to question {question_id} about
PH-Saudi domestic worker fee cap. Their reply:

---
{reply_body}
---

Extract any of:
- numeric fee cap (currency + amount)
- source URL or citation
- effective date
- statement that the corridor has changed in some other way

Return JSON: {"new_cap": ..., "source": ..., "effective_date": ...,
"other_changes": ...}. If nothing extractable, return {}.
"""
```

### Tier 3: route to human curator

If Tier 2 extracts nothing useful, the reply is queued for the
curator to read manually. Always send an acknowledgement to the
subscriber so they know they were heard.

## Acknowledgement and merge-notification emails

After the curator merges an envelope into the published pack, the
oracle sends one confirmation email to the contributor:

```
From: oracle@gaatw.duecare.example
To: maria@damayan.example
Subject: Your PH-Saudi corridor update is live in DueCare GAATW pack 2026.05.29

Hi Maria,

Thanks for your reply on 2026-05-23. Your input was reviewed by the
curator and merged into the GAATW knowledge pack version 2026.05.29
(published Friday).

What changed:
  PH-Saudi domestic worker placement fee cap:
    Old: PHP 0 (employer-paid only) per POEA MC 14-2017
    New: PHP 0 (employer-paid only) per POEA MC 14-2017
    Verified: 2026-05-23 by Maria @ Damayan

Every member NGO that runs `duecare knowledge sync` after Friday
will see this verification. Thank you for helping keep the pack
accurate.

— DueCare GAATW Oracle
```

## Privacy and consent

| Concern | How handled |
|---------|-------------|
| **Opt-in** | Stakeholder must reply CONFIRM before the oracle starts sending gap questions |
| **Opt-out** | One-line STOP reply is honored within 24 hours |
| **PII** | Oracle never asks for worker PII. Questions are only about systemic knowledge (corridor caps, statute citations, NGO contacts). If a stakeholder volunteers worker PII in a reply, the inbound processor's anonymisation gate redacts before the envelope is created |
| **Audit trail** | Every email sent + received is logged with timestamp, subscriber id, question id. Stored under `data/oracle/audit/`. SHA-256 hashes of email bodies (not plaintext) retained for non-repudiation |
| **Attribution** | Each envelope's provenance records the contributor's organisation (not personal name unless they explicitly request attribution). Pack release notes credit "input from N contributors across M organisations" |
| **Email frequency cap** | Default: 2 per subscriber per month. Caps are per-subscriber preferences set at sign-up |
| **Email service provider** | Self-hosted SMTP/IMAP recommended. Cloud (SendGrid, Postmark, AWS SES) acceptable for outbound only; never for inbound subscriber data |

## Integration with paths 2 and 3

**Path 2 (NGO network):** The oracle runs alongside the curator
function. Curator queue is fed by both manual contributions (path 2
workflow) AND oracle-solicited contributions. The same `duecare-
knowledge-envelope/v1` schema is used regardless of source. Pack
release notes distinguish: "12 envelopes (8 oracle-solicited, 4
manual)".

**Path 3 (government):** A government agency may run its own oracle
against its own subscriber list (regional labour inspectors,
liaison officers at consulates, partner NGO staff). The oracle
respects whatever data-handling policies apply to government staff
communications (e.g., government email only, no third-party SMTP
providers).

## Proposed openclaw and hermes integration

Taylor's broader project ecosystem includes "openclaw" and "hermes"
naming for server-side automation infrastructure. The following adapters were
proposed, not implemented:

- **openclaw** — if this is the message-passing / queue
  infrastructure, the oracle uses it for the gap-detector → outbound
  → inbound → curator-queue pipeline. Configuration via env vars
  pointing at the openclaw bus URLs.
- **hermes** — if this is the SMTP/IMAP delivery layer, the oracle
  uses it for outbound + inbound mail. Configuration via env vars
  pointing at hermes endpoints.

The proposed fallback would use Python's `smtplib` + `imaplib` + a SQLite
subscriber + audit store. That fallback is not present today.

## Proposed implementation surface area

The design calls for a separate package, sibling to the existing packages:
`packages/duecare-llm-oracle/`. Modules:

- `duecare.oracle.subscribers` — opt-in/opt-out + subscriber store
- `duecare.oracle.gap_detector` — scans knowledge layer for stale
  facts and queues questions
- `duecare.oracle.composer` — produces outbound emails from gap +
  subscriber pairs
- `duecare.oracle.smtp_out` — outbound delivery (hermes or fallback)
- `duecare.oracle.imap_in` — inbound polling
- `duecare.oracle.parser` — Tier 1 / Tier 2 / Tier 3 reply parsing
- `duecare.oracle.envelope_emitter` — produces path-2 envelopes
  from parsed replies, queues to curator
- `duecare.oracle.audit` — append-only audit store
- `duecare.oracle.cli` — `duecare oracle subscribers list`,
  `duecare oracle send-questions`, etc.

Folder-per-module per `.claude/rules/40_forge_module_contract.md`.

## Cost projection

For a 200-subscriber deployment with 2-per-month cap:

| Item | Volume / month | Cost |
|------|----------------|------|
| Outbound emails | 200 × 2 = 400 | <$5 self-hosted SMTP, <$20 commercial relay |
| Inbound IMAP polls | 24 × 30 = 720 polls | $0 self-hosted |
| Gemma 4 NLP passes (Tier 2) | ~150 (75% of replies) | $0 self-hosted |
| Curator review on Tier 3 routed | ~50 | included in curator role (no new cost) |
| Audit storage | <100 MB | $0 |

The whole oracle fits on a $5/month VPS. The expensive resource is
not infrastructure; it is curator and contributor time, and the
oracle's job is to make BOTH of those go further.

## What can go wrong + how to handle it

| Failure | Mitigation |
|---------|------------|
| Spam: outsider tries to inject envelopes via the inbox | Authenticate by email-address allowlist (only known subscribers). Replies from unknown addresses queued for curator triage; never auto-merged |
| Phishing: someone spoofs a subscriber address | SPF/DKIM/DMARC enforced on inbound. Suspicious replies flagged for curator |
| Subscriber fatigue | Frequency cap enforced strictly. Default 2/month; subscriber can lower to 1/month or 1/quarter. Unsubscribe always honored |
| Oracle goes silent (cron stops) | Status page on the workbench shows last gap-detect + last outbound. Coordinator gets a weekly status email |
| Tier 2 NLP misinterprets a reply | Curator review on every Tier 2 result before merge. If errors compound, lower Tier 2 confidence threshold |
| Contributor confused about how to reply | Each email includes a 1-line reply guide. If parsing fails 3× in a row, the oracle pings the curator to reach out personally |

## Where this fits in the broader plan

- The oracle is **the engagement layer**. It turns the path-2
  knowledge hub from a curator-only effort into a network-scale
  contribution machine.
- The oracle is **not the knowledge layer itself**. The published
  pack still flows through the curator. The oracle just feeds it
  more inputs.
- The oracle scales paths 2 and 3 without scaling paths 1 or 4. A
  single NGO (path 1) doesn't need an oracle. A platform (path 4)
  has its own engineering team; they don't need an oracle either.

## Next steps

1. Build `packages/duecare-llm-oracle/` skeleton per the module
   list above. Folder-per-module, AGENTS.md + PURPOSE.md etc.
2. Implement the fallback SMTP/IMAP path first (no openclaw/hermes
   dependency). Get end-to-end working with a single subscriber +
   single gap.
3. Add the gap-detector for the easiest gap class: corridor caps
   with `verified_at` more than 6 months old.
4. Add the openclaw/hermes adapter as a second SMTP/IMAP backend
   once the fallback path is solid.

## See also

- [`02_network_hub_bootstrap.md`](02_network_hub_bootstrap.md) —
  what the oracle feeds into
- [`02_network_curator_role.md`](02_network_curator_role.md) —
  curator's review job remains unchanged; volume increases
- [`03_government_workbench.md`](03_government_workbench.md) —
  government deployments may run their own oracle against their
  own subscriber list
- `memory/feedback_email_only_for_civil_society.md` (auto-loaded) —
  the constraint that drove this design
