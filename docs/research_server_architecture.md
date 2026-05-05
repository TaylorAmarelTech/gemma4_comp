# Continuous Research Server — Architecture (v1)

> **Status (2026-05-01):** architecture only. Implementation is a
> 2-4 week post-hackathon project. The pull-based update server +
> signed pack format (`docs/extension_pack_format.md`) is what apps
> actually consume; this doc describes the upstream pipeline that
> generates those packs from continuously-changing real-world data.
>
> **Companion:** `docs/extension_pack_format.md` — the wire format
> the research server outputs.

## Why this exists

Migrant-worker law is a moving target:

- **POEA Memorandum Circulars** are issued multiple times per year
  (MC 14-2017 was the canonical PH→HK zero-fee directive; MC 02-2026
  hypothetically supersedes parts of it).
- **Kafala reform** in Saudi Arabia (2021) and the 2024 expansion
  invalidated several previously-valid forced-labour patterns and
  added new ones (huroob workflow changes).
- **Court decisions** establish new precedent monthly — PACER, AustLII,
  HK Judiciary, BAILII publish anti-trafficking rulings worth
  citing.
- **NGO reports** (IJM, Polaris, ECPAT, MfMW HK) quantify new
  recruitment-fraud patterns yearly.
- **Recruitment-fee camouflage labels evolve** — 2020's "training
  fee" becomes 2026's "platform onboarding fee" (the GREP rules need
  the new label).

A static bundle becomes stale in 6-12 months. Manually keeping the
bundle current doesn't scale (one maintainer, hundreds of
jurisdictions, dozens of languages). The continuous research server
is the production-mode answer: an always-running pipeline that
crawls primary sources, drafts updates, asks NGO partners to verify,
and publishes signed extension packs to the registry.

## High-level pipeline

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                  Continuous Research Server                      │
   │                  (private; you operate; one VM is enough)         │
   │                                                                   │
   │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐          │
   │  │ [1] Crawler │→ │ [2] Extractor│→ │ [3] Generator  │          │
   │  │  agent      │  │  (Gemma 4 +  │  │  (Gemma 4 +    │          │
   │  │  Playwright │  │  named-      │  │  rubric-aware) │          │
   │  │  + BYOK     │  │  entity ext) │  │                │          │
   │  └─────────────┘  └──────────────┘  └────────┬───────┘          │
   │       ↑                                      │                   │
   │  ┌────┴────────┐                             ▼                   │
   │  │ [0] Source  │                  ┌────────────────────┐         │
   │  │ catalog     │                  │ [4] NGO email      │         │
   │  │ (ILO Normlex│                  │  verifier loop     │         │
   │  │  POEA URLs, │                  │  (sends diff       │         │
   │  │  PACER docs,│                  │   asks Y/N)        │         │
   │  │  IJM reports│                  └────────┬───────────┘         │
   │  │  ...)       │                           │ verified            │
   │  └─────────────┘                           ▼                     │
   │                                  ┌────────────────────┐          │
   │                                  │ [5] Pack signer    │          │
   │                                  │  (Ed25519 key in   │          │
   │                                  │   HSM / hardware   │          │
   │                                  │   token)           │          │
   │                                  └────────┬───────────┘          │
   └───────────────────────────────────────────┼──────────────────────┘
                                                ▼ signed pack
                                 ┌──────────────────────────┐
                                 │  Update server           │
                                 │  (GitHub Pages —         │
                                 │   already documented in  │
                                 │   extension_pack_format) │
                                 └──────────┬───────────────┘
                                             ▼ pull
                              ┌──────────────────────────────┐
                              │  Apps in the field           │
                              │  (Android, chat, classifier, │
                              │   notebooks, custom integ.)  │
                              │  All opt-in.                  │
                              └──────────────────────────────┘
```

## Component specifications

### [0] Source catalog

A versioned YAML file (`research_server/sources.yaml`) listing every
URL the crawler watches. Each source entry:

```yaml
- id: poea_memorandum_circulars
  name: POEA Memorandum Circulars
  url: https://www.dmw.gov.ph/circulars
  scope:
    corridors: [PH-HK, PH-SA, PH-AE, PH-SG]
    legal_areas: [recruitment_fees, deployment_authorization]
  crawl_frequency: weekly
  selector_css: "div.circular-list a"
  diff_threshold_chars: 200      # ignore tiny re-issuance edits
  primary_extractor: poea_mc_extractor

- id: ilo_normlex_c181
  name: ILO Normlex — C181 monitoring
  url: https://normlex.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:11300:0::NO::P11300_INSTRUMENT_ID:312326
  scope:
    legal_areas: [private_employment_agencies]
  crawl_frequency: monthly
  ...
```

50-100 sources to start (~10 jurisdictions × 5-10 source types each).
Extensible per corridor. Adding a source requires a sources.yaml PR
that the maintainer reviews — keeps the crawler scope auditable.

### [1] Crawler agent

Adapts the existing `duecare-llm-research-tools` package
(`packages/duecare-llm-research-tools/`) which already has:

- `WebFetchTool` (httpx + trafilatura)
- `BrowserTool` (Playwright real browser, used by the A4
  agentic-research notebook)
- `WikipediaTool`, `FastWebSearchTool` (BYOK Tavily/Brave/Serper or
  DDG fallback)
- `PIIFilter` (hard gate)

Crawler logic per source:

1. Fetch the source URL (BrowserTool when JS-rendered, WebFetchTool
   otherwise).
2. Compute SHA256 of stripped content; compare against last-seen
   hash in `research_server/state.db`.
3. If unchanged: log "no change" + sleep until next interval.
4. If changed: dump the new content to `crawl_artifacts/<source_id>/<timestamp>.html`
   and pass to the extractor.

Privacy invariant: PIIFilter applies to every fetched page — never
log raw worker / case names from court filings even when crawling
public records. Hash worker names if they appear in the content.

Audit log: every fetch records `(source_id, fetched_at, content_sha256, status_code)`
to a WORM-friendly stream.

### [2] Extractor agent

Pulls structured facts out of the crawled HTML. Two strategies:

**a) Per-source extractor module** (preferred). Hand-written for
high-value sources like POEA MC pages, where the structure is
predictable. Returns a strongly-typed `ExtractedFact` dict:

```python
{
    "source_id": "poea_memorandum_circulars",
    "source_url": "https://www.dmw.gov.ph/circular/MC-2026-02",
    "extracted_at": "2026-04-30T12:00:00Z",
    "fact_type": "memorandum_circular_issued",
    "facts": {
        "circular_number": "MC 02-2026",
        "title": "Revised Placement Fee Cap for Domestic Workers Deployed to GCC",
        "effective_date": "2026-05-01",
        "supersedes": ["MC 14-2017 (partial)"],
        "summary": "...",
        "full_text_path": "crawl_artifacts/.../MC-02-2026.txt"
    }
}
```

**b) Gemma 4 generic extractor** for sources without a dedicated
module. Prompts:

```
You are a legal-text extractor. The following is content fetched from
<source URL>. Extract every fact relevant to migrant-worker
exploitation, recruitment, or trafficking law as a JSON list of
ExtractedFact objects matching this schema: {...}. If nothing
relevant, return [].
```

Runs Gemma 4 31B (or whatever the bench-and-tune notebook produced)
on a GPU node. Bounded retries; outputs validated against the
ExtractedFact JSON schema.

### [3] Generator agent

Takes extracted facts and produces draft updates: new GREP rules,
new RAG corpus entries, new prompt tests, new tool data.

For example, a `MC 02-2026` fact triggers:

- A draft RAG doc (the controlling text + citation)
- Possibly a new GREP rule if the fact mentions a new fee-camouflage
  label
- A new prompt test verifying that the harness cites the right
  controlling MC

The generator runs Gemma 4 with a structured-output system prompt
that emits the exact JSON shapes the extension pack format expects.
Each draft is tagged with `source_traceability` linking back to the
extracted fact + crawled artifact, so reviewers can see "this rule
was generated from this fact extracted from this page on this date."

### [4] NGO email verifier loop

Drafts go to a small Postgres `pending_review` queue. A scheduler
sends nightly digest emails to named NGO contacts:

```
Subject: Duecare daily review queue (3 items, ~5 min)

Hello Anna,

3 new draft updates need your review.
Each one is a 1-click Approve / Revise / Reject decision.

1. NEW RAG doc: "POEA MC 02-2026 — Revised Placement Fee Cap"
   Source: https://www.dmw.gov.ph/circular/MC-2026-02 (verified)
   Affects: PH-SA, PH-AE, PH-SG corridors
   Approve: https://review.duecare.example/r/abc123/approve
   Revise:  https://review.duecare.example/r/abc123/revise
   Reject:  https://review.duecare.example/r/abc123/reject

2. NEW GREP rule: detection pattern for "platform onboarding fee"
   ...
```

Approve → moves to the published-pack queue. Revise → opens a web
form for the NGO partner to edit. Reject → dropped + logged.

Tradeoffs:

- **Email channel** because NGO partners aren't on Slack, are often
  field-deployed, work asynchronously, and email is durable evidence
  of the verification chain.
- **Lightweight web review UI** because no NGO partner will install
  yet another app. A click-through link with the diff inline + an
  Approve button is the minimum-friction path.
- **Named contacts only.** The NGO must designate one or more
  reviewers per corridor. No public review (would invite poisoning).

### [5] Pack signer

When N approvals accumulate (or a weekly cadence elapses), assemble
the approved drafts into a `.tar.gz` per `docs/extension_pack_format.md`
and sign with the publisher's Ed25519 key.

Key custody:

- Each NGO partner has their OWN signing key, generated on their
  device, public fingerprint added to the trust root.
- The Duecare maintainer's root key is hardware-token-backed
  (Yubikey, etc.) and only touched during trust-root rotations.
- Per-publisher keys are stored in the research server's HSM /
  KMS (cloud KMS for cloud deploys, software keystore for self-
  hosted).

Failure mode: if the research server is compromised, the attacker
can publish packs signed with the per-publisher KMS keys but
**cannot** modify the trust root. Clients still verify against
the trust root, so the worst case is "we revoke the compromised
publisher's key in the next trust-root rotation and clients
auto-refuse the bad pack."

## Operational model

### Hosting

- One VM (any cloud, ~$30/month at modest scale).
- Postgres (any managed offering or sqlite for the smallest deploy).
- Separate GPU instance only when running the Gemma extractor —
  spot instance, ~$0.50/hr, runs ~2hr/day = ~$30/month.
- Object store (S3 or B2) for crawl artifacts.

Total: ~$60-100/month at modest scale. Could run on a single Hetzner
CCX13 + a small GPU rental for the extraction window.

### Privacy posture

- No worker data ever touches this server. Only public source
  content (court filings already public, NGO reports already
  published, government circulars already public).
- PIIFilter on every fetched page — strips names that appear in
  public court filings before they go into the corpus, replaces
  with case-number references.
- NGO reviewer interactions are minimum: which draft they
  approved, when, scope. No worker case data exchanged via the
  review channel.

### Cadence

- Crawl: per-source (weekly to daily depending on source).
- Extract: continuous (queued).
- Generate: continuous.
- NGO review: nightly digest.
- Pack publish: weekly OR when N=10 approvals accumulate, whichever
  is sooner.
- Trust-root rotation: annually.

### Observability

OpenTelemetry. Every span tagged with `(source_id, fact_type,
publisher_id, pack_id, pack_version)`. A simple dashboard answers:

- Which sources have we crawled most recently?
- What's our extraction success rate?
- How long does NGO review take per publisher?
- Which packs have been published in the last quarter?
- How many client deployments pulled each pack version?

## What this is NOT

- **Not a way to make decisions for workers.** The server publishes
  rules + RAG docs. The advice surface in the apps still belongs to
  the worker — the server only updates the FACTS the advice grounds in.
- **Not a worker-facing service.** Workers never interact with this
  server directly. They interact only with the on-device app, which
  optionally pulls pre-signed packs from the static GitHub Pages
  registry.
- **Not a recipient of telemetry.** Apps pull from the registry;
  the registry does not log requests beyond standard CDN access logs
  (which we cannot turn off but contain only IP + timestamp + path,
  no app or worker identifiers).
- **Not a substitute for the canonical bundle.** The wheel ships
  with 37 GREP rules, 33 RAG docs, etc. — that's the floor. Packs
  are additive enhancements.

## Build phases

1. **Phase 1 (week 1-2 post-hackathon).** Crawler + per-source
   extractors for 5 high-value sources (POEA, BMET, BP2MI, Saudi
   MoHR, ILO Normlex). No NGO loop yet — Duecare maintainer
   reviews drafts directly, signs, publishes. Proves the pipeline.
2. **Phase 2 (week 3-4).** NGO email loop with one partner (MfMW HK
   or Polaris depending on relationship). Move PH-HK corridor to
   their authority.
3. **Phase 3 (month 2-3).** Gemma extractor for low-volume sources
   without dedicated extractor modules. NGO authority expanded to
   3-5 partners (one per major corridor).
4. **Phase 4 (month 4+).** Trust root rotation flow + per-publisher
   key rotation flow + observability dashboard + replication of the
   pipeline for a second region (ID-corridor focus or SA-domestic
   focus).

## Reference implementation

Lives at `research_server/` in this repo (planned, not yet created).
Uses:

- `duecare-llm-research-tools` (already published) for the crawler
- `duecare-llm-models` (already published) for Gemma extractor
- `duecare-llm-publishing` (already published) for HF Hub interactions
- New: `research_server/extractors/` (per-source modules)
- New: `research_server/generator/` (draft writer)
- New: `research_server/review/` (NGO email loop + web review)
- New: `research_server/registry_publisher/` (signs + uploads to gh-pages)

## See also

- `docs/extension_pack_format.md` — the wire format the server outputs
- `packages/duecare-llm-chat/src/duecare/chat/extensions/__init__.py` —
  the client that pulls + verifies + merges packs
- `scripts/build_extension_pack.py`, `scripts/sign_extension_pack.py`,
  `scripts/verify_extension_pack.py` — the reference tooling
