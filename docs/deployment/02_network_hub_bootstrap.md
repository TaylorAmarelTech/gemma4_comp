# Path 2 — NGO network knowledge-hub bootstrap

For an NGO network of 50 to 200+ member organisations that wants
shared trafficking-pattern intelligence without sharing case PII.
Examples: GAATW (Global Alliance Against Traffic in Women), La Strada
International (10 EU member organisations), COATNET (Christian
Action and Networking against Trafficking), Talitha Kum (~ 60
country networks of Catholic women religious), regional clusters of
Polaris partners, NSWP (Global Network of Sex Worker Projects).

## The shape of the hub

Every member NGO runs the path 1 workbench locally. Case PII never
leaves the member. What flows between members is **knowledge
envelopes** — small JSON files containing newly discovered
trafficking patterns, fee-camouflage labels, NGO contact updates,
or template improvements, fully anonymised at source.

```
┌─────────────────────────────────┐
│ NGO A (Damayan, NYC)            │
│  workbench: case PII local      │
│  contributes: pattern envelope  │
│  ↓                              │
└─────────────────────────────────┘
                                 ↓
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ Hub coordinator          │ ←  │ NGO B (Kalayaan, UK)            │
│ - review envelopes       │    │  workbench: case PII local      │
│ - merge into pack        │    │  contributes: NGO contact update│
│ - publish weekly         │    │  ↓                              │
└──────────────────────────┘    └─────────────────────────────────┘
       ↓                                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  duecare-knowledge-pack-<region>  (Kaggle Dataset / git repo)   │
│  - versioned (semantic version + commit SHA)                    │
│  - 439 GREP rules, 859 RAG docs, 34+ templates, etc.          │
│  - every member NGO syncs weekly                                │
└─────────────────────────────────────────────────────────────────┘
       ↓                                          ↓
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│ NGO A pulls updates             │    │ NGO B pulls updates             │
│  duecare knowledge sync         │    │  duecare knowledge sync         │
└─────────────────────────────────┘    └─────────────────────────────────┘
```

## Roles

| Role | Who | Time commitment |
|------|-----|-----------------|
| **Coordinator** | One member organisation (e.g., GAATW Secretariat) or a small steering committee | 4 to 8 hours/week |
| **Curator** | The coordinator's designated reviewer for each envelope class (GREP, RAG, templates, contacts) | 1 to 2 hours/week per class |
| **Contributor** | Any member NGO submitting envelopes | Variable; can be zero if just consuming |
| **Consumer** | All member NGOs syncing the pack | 0 hours; automatic on `duecare knowledge sync` |

## Knowledge envelope schema

Each envelope is a single JSON file, named
`<envelope_type>-<short-hash>.json`, with the following shape:

```json
{
  "schema": "duecare-knowledge-envelope/v1",
  "envelope_id": "grep-2026-05-22-9f8c4d2",
  "envelope_type": "grep_rule",
  "source_ngo": "Damayan",
  "submitted_at": "2026-05-22T14:30:00Z",
  "submitted_by": "case-worker-id-redacted",
  "region_relevance": ["PH", "HK", "global"],
  "summary": "New fee-camouflage label: 'placement advance via assignment'",
  "rationale": "Observed in 8 PH-HK domestic worker cases in Q1 2026 where agencies restructured PHP 50k recruitment fees as 'advance payments from training centre assigned to HK collection agent' to evade POEA MC 14-2017 audit.",
  "payload": {
    "rule_id": "b_fee_camouflage_placement_advance_via_assignment",
    "patterns": [
      "\\b(?:placement\\s+advance|training\\s+payment)\\s+(?:assigned|transferred)\\s+to\\s+(?:collection|HK|destination)\\b"
    ],
    "severity": "high",
    "citation": "POEA MC 14-2017 + HK Cap. 57 Sec. 32 + ILO C181 Art. 7",
    "indicator": "Substance-over-form analysis required..."
  },
  "anonymisation": {
    "passed_gate": true,
    "pii_hashes": [],
    "manual_review": true
  },
  "review_status": "pending"
}
```

Envelope types:

| Type | Payload shape | Example |
|------|---------------|---------|
| `grep_rule` | `{rule_id, patterns, severity, citation, indicator}` | New fee-camouflage pattern |
| `rag_doc` | `(id, title, citation, body)` tuple | New ILO Helpdesk briefing |
| `template` | TemplateSpec (id, title, jurisdiction, audience, summary, body, fields) | New regulator complaint template |
| `corridor_fee_cap` | `{(origin, destination): {service, training, medical, total}}` | Updated cap after regulator change |
| `ngo_contact` | `{(origin, destination): [name, phone, url]}` | New peer organisation registered |
| `persona` | persona JSON | New audience role |
| `ilo_convention` | `{id, title, key_articles, focus, ratifications}` | New convention added |
| `correction` | `{target_envelope_id, correction_reason, replacement_payload}` | Fix to a prior envelope |

## Coordinator bootstrap (week 1)

1. **Pick the hub host.** Options: a Kaggle Dataset (free,
   versioned, public/private), a private git repository (more
   control, more setup), or a CKAN / Dataverse instance for the
   academic-research variant. For a 50- to 200-member network,
   start with a private Kaggle Dataset.
2. **Define the namespace.** Convention:
   `duecare-knowledge-pack-<region-or-network>`. Examples:
   `duecare-knowledge-pack-asia-pacific`,
   `duecare-knowledge-pack-gaatw`,
   `duecare-knowledge-pack-la-strada-eu`.
3. **Seed with the bundled knowledge layer.** Run
   `duecare knowledge export --bundle-baseline` to produce the
   initial pack from the current 439 GREP rules + 859 RAG documents
   + 36 templates + 37 personas + 38 corridor fee caps + 30 NGO
   contacts + 16 ILO conventions.
4. **Establish the curator review queue.** Either a Notion board,
   a GitHub Issues project, or a shared spreadsheet. Each new
   envelope gets one row; columns: envelope_id, type, source_ngo,
   submitted_at, reviewer, status (pending / approved / rejected /
   needs_revision), notes.
5. **Publish the contribution guide.** A short doc telling member
   NGOs how to use the workbench's "Contribute to hub" button,
   what each envelope type is for, and what the curator will check
   before merging.

## Curator review checklist

Before approving an envelope into the pack, the curator verifies:

| Check | What to verify |
|-------|----------------|
| **Anonymisation** | The envelope passed the workbench's anonymisation gate (`anonymisation.passed_gate == true`). No worker names, addresses, phone numbers, or case identifiers in any field. |
| **Provenance** | The `rationale` field cites the basis: "observed in N cases of corridor X", "court record cite", "regulator publication date Y". No naked assertions. |
| **Citation accuracy** | If the envelope claims a statute / ILO convention / case-law citation, the curator (or a peer reviewer) verifies the citation actually exists and says what the envelope says it says. |
| **Region relevance** | The `region_relevance` tags match the substance. A PH-HK pattern should not be tagged as `global` unless it really generalises. |
| **Schema validity** | The envelope JSON validates against `duecare-knowledge-envelope/v1`. |
| **Substance-over-form** | If it is a `grep_rule`, the regex is actually testable (no `.*.*` greed). If it is a `rag_doc`, the body is non-empty and source-cited. |
| **No duplicate** | An existing pack rule does not already cover the case. (Search by keyword first; if there is overlap, propose a `correction` envelope instead.) |

## Sync mechanics for member NGOs

Each member NGO runs (e.g., weekly):

```bash
duecare knowledge sync --pack duecare-knowledge-pack-gaatw
```

This downloads the latest pack version, diffs against the local
knowledge state, and applies new envelopes. The workbench's Status
page shows the last sync time and the diff summary (+12 GREP rules,
+3 RAG documents, +1 corridor fee cap, etc.).

A member NGO can also lock to a specific pack version
(`--pack-version 2026.05.22`) if they need stability between
audits.

## Versioning convention

`duecare-knowledge-pack-<region>` versions follow YYYY.MM.DD with
optional `-rcN` for release candidates:

- `2026.05.22` — weekly snapshot
- `2026.05.22-rc1` — release candidate (curator has approved, awaiting
  peer review)
- `2026.05.22-corrections` — fixes shipped between snapshots

Major versions are reserved for breaking schema changes
(`v2` of the envelope schema, for example).

## Trust model

1. **Member NGOs trust each other for non-malicious contributions.**
   The hub is not a security boundary against insider threats; it is
   a knowledge-sharing convenience.
2. **The curator is the final filter for substance.** They are the
   only person who can merge an envelope into the pack.
3. **The anonymisation gate is the final filter for PII.** It runs
   at the submitter, and re-runs at the curator before merge.
4. **The pack is open-membership inside the network.** Anyone who
   has access to the pack has full read access to all envelopes.
   For sensitive intelligence (active investigation, named
   trafficker, on-going operation), do NOT use the pack — use
   point-to-point sharing between specific NGOs.

## What can go wrong + how to handle it

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Member submits an envelope containing PII the anonymiser missed | Curator catches in review | Reject envelope; flag the anonymiser rule that should have caught it; ship a hotfix to all members |
| A `correction` envelope contradicts an earlier `grep_rule` | Curator review notices the conflict | Open a discussion in the network's review queue; resolve by peer consensus before publishing |
| Curator's review backlog grows | Status page shows queue size | Recruit a second curator from a different region; split the queue by envelope type |
| Pack version drifts between members (some on `2026.05.22`, some still on `2026.04.15`) | `duecare knowledge sync` shows version skew on Status page | Coordinator publishes a "minimum required version" advisory for shared cases; members upgrade |
| Hub host goes down | Members cannot sync | Coordinator maintains a backup mirror on a separate git repo; members can `--pack-source <url>` to fall back |

## Cost projection

| Cost | Amount |
|------|--------|
| Hub host (private Kaggle Dataset) | $0 |
| Coordinator time | 4 to 8 hrs/week ≈ 0.1 to 0.2 FTE |
| Per-member sync time | < 1 hour/week per NGO |
| Storage | < 100 MB for the pack at typical size (hundreds of rules, hundreds of docs, tens of templates) |

The model is volunteer-coordinator + self-host member. If a network
wants paid coordination, the budget pays for the coordinator role,
not for software or infrastructure.

## See also

- [`02_network_curator_role.md`](02_network_curator_role.md) —
  detailed curator-role responsibilities, review process,
  escalation paths
- [`oracle_email_solicitation.md`](oracle_email_solicitation.md) —
  server-side email oracle that proactively solicits contributions
  from civil society stakeholders, feeding the same curator queue
  the manual submission flow uses
- [`01_ngo_pilot_brief.md`](01_ngo_pilot_brief.md) — what each
  member NGO is running locally
- `.claude/rules/10_safety_gate.md` — PII rules that apply at
  envelope creation and curator review
- `packages/duecare-llm-publishing/` — the package that produces
  the pack format from local workbench state
