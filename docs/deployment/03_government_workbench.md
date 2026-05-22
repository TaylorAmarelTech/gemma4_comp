# Path 3 — Government workbench (field-inspector pilot)

For a national or sub-national government office whose investigators
audit recruitment agencies, screen incoming complaints, or
investigate trafficking cases in the field. Examples in this
audience: Philippines DMW (Department of Migrant Workers, successor
to POEA), Indonesia BP2MI, Bangladesh BMET, Nepal Department of
Foreign Employment, Vietnam DOLAB, UK GLAA (Gangmasters and Labour
Abuse Authority), Australia Fair Work Ombudsman, US DOL Wage and
Hour Division, Saudi MHRSD, UAE MoHRE, Qatar MoL.

This document covers the **field workbench path**. For the bulk
processing API path, see
[`03_government_api_integration.md`](03_government_api_integration.md).

## What you get

A handheld AI workbench an inspector can carry into a recruitment
agency audit, port-of-entry interview, or worker-complaint intake
office. It:

- Photographs a recruitment contract or job ad, runs OCR + Gemma 4
  vision, produces an instant red-flag report
- Looks up the relevant section of your domestic statute and the
  matching ILO convention article for any flagged practice
- Produces a draft inspection report or violation notice with the
  citation matrix already filled in
- Logs every query to an immutable audit trail (FOIA-defensible)
- Operates fully offline once the model and knowledge layer are
  loaded

Same software as path 1 (single NGO), with rubric weights tuned to
your jurisdiction and an FOIA audit layer enabled.

## What you provide

| Resource | Pilot | Production |
|----------|-------|------------|
| Inspector hardware | 1 ruggedised tablet or laptop per inspector (16 GB RAM, GPU optional) | Same; standard issue across the inspectorate |
| Storage | 30 GB free per device | Same |
| Network | Initial install + jurisdiction tuning over secured network | Optional WAN sync for updated rubric or new statute releases |
| Operator | 2 to 5 inspectors for pilot + 1 IT helper | All inspectors after pilot |
| Domain expertise | 1 senior inspector to co-author the jurisdiction tuning | Same; quarterly review |
| Legal review | 1 staff lawyer to verify statute-citation matrix | Same; quarterly |

## Pilot scope

**In scope (30 to 60 day pilot):**

- Recruitment agency audit workflow: inspector visits a licensed
  agency, scans 5 sample worker contracts, gets instant red-flag
  flags + statute citations + draft inspection notes
- Port-of-entry interview workflow: inspector interviews a returning
  worker, transcribes salient facts into the workbench, gets a
  preliminary trafficking-indicator assessment + referral pathway
- Complaint intake desk: front-desk officer accepts a walk-in
  complaint, workbench helps classify (trafficking / unfair
  recruitment / contract substitution / wage theft) and routes to
  the right unit
- Jurisdiction tuning pass: senior inspector + staff lawyer review
  the rubric weights, citation matrix, and templates for your
  agency's specific statutes

**Out of scope (Phase 2):**

- Integration with your existing case-management system — handled in
  [`03_government_api_integration.md`](03_government_api_integration.md)
- Cross-agency data sharing — requires data-sharing MOUs that take
  longer than a pilot window
- Public-facing complaint intake — initially restricted to
  inspector-mediated use
- Anything that would require the workbench to call out to a
  third-party model API — never enabled on government deployments

## Deployment topology

```
┌─────────────────────────────────────────────────────────────────┐
│ Inspector device (ruggedised tablet or laptop)                   │
│  - duecare workbench (FastAPI on localhost:8080)                 │
│  - Gemma 4 E2B or E4B loaded from local disk                     │
│  - bundled knowledge pack: tuned for THIS jurisdiction           │
│  - FOIA audit log: append-only SQLite                            │
│  - Disk encryption: agency standard (BitLocker / FileVault)      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ (no network egress in field)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agency internal network (only when inspector returns to base)   │
│  - upload audit log to central archive                          │
│  - download updated rubric / new statute releases               │
│  - never calls out to public internet                           │
└─────────────────────────────────────────────────────────────────┘
```

## Jurisdiction tuning

Every government deployment goes through a one-week tuning pass
before the pilot. The senior inspector and staff lawyer work with
DueCare to:

1. **Verify the citation matrix.** Each ILO convention article and
   destination/origin-country statute referenced in the bundled
   knowledge pack is checked against the agency's authoritative
   register. Anything stale, mis-cited, or repealed gets corrected.

2. **Weight the cluster thresholds.** The bundled rubric uses
   six clusters with default thresholds (legal grounding 60%, harm
   avoidance 80%, worker protection 70%, pattern recognition 60%,
   resources 70%, ethical framing 70%). A government rubric usually
   wants different weights — more legal grounding for a regulator,
   more pattern recognition for an enforcement unit, more resources
   for a complaint-intake desk.

3. **Author jurisdiction-specific templates.** The 34 bundled
   templates cover the major regulators globally. Your agency may
   want 2 to 4 additional templates specific to your enforcement
   tools (administrative penalty notice, license suspension order,
   referral to prosecutor, joint operation request to another
   agency).

4. **Configure the FOIA audit layer.** What gets logged, who can
   read the log, retention period, redaction rules for log
   exports.

5. **Train the inspectors.** Two-day classroom on the workbench;
   five field shadows on real (mock) audits.

The tuning produces a `duecare-jurisdiction-<agency>-config.yaml`
file plus an updated knowledge pack. This is checked into your
internal repo (not the public DueCare repo).

See [`03_government_jurisdiction_tuning.md`](03_government_jurisdiction_tuning.md)
for the full tuning checklist.

## FOIA audit log

Every query an inspector runs against the workbench produces an
audit log entry:

```json
{
  "request_id": "req-2026-05-22-9f8c4d2",
  "investigator_id": "inspector-id-redacted-for-this-doc",
  "device_id": "device-007",
  "query_at": "2026-05-22T14:30:00Z",
  "query_type": "audit_recruitment_contract",
  "query_summary_hash": "sha256:af83c2d1...",
  "input_artefact_hashes": ["sha256:11ee..."],
  "rubric_dims_evaluated": ["fee_camouflage_recognition", "contract_substitution", "..."],
  "statutes_returned": ["POEA-MC-14-2017-Sec-3a", "RA-8042-as-amended-Sec-6c", "ILO-C181-Art-7"],
  "citations_returned": [{"id": "...", "verbatim": "...", "source_url": "..."}],
  "workbench_version": "0.1.0-rc4",
  "knowledge_pack_version": "2026-05-22-jurisdiction-dmw"
}
```

Properties:

- **Append-only.** No edits, no deletes from inside the workbench.
- **Hash-linked.** Each entry includes the hash of the previous
  entry, forming a chain that detects tampering.
- **Plaintext queries never stored.** Only SHA-256 hashes of the
  query and input artefacts. The plaintext is in the inspector's
  case file, governed by your existing case-management retention
  rules.
- **Exportable for FOIA.** A separate command produces a redacted
  log export suitable for FOIA / right-to-information disclosure.
  Inspector IDs and device IDs are tokenised; statutory references
  and rubric dimensions are kept verbatim.

## Multi-language

Your inspectors and the workers they interview probably do not
speak the same language as the statute or the ILO convention text.
The workbench supports:

- **Input** in any language Gemma 4 covers (Tagalog, Bahasa,
  Vietnamese, Bengali, Nepali, Arabic, Spanish, Portuguese, English,
  French, Mandarin, Cantonese, Korean, Japanese, Hindi, Urdu,
  Punjabi, Tamil, Sinhalese, Burmese, Khmer, Thai, Lao, Russian,
  Ukrainian, Romanian, Bulgarian)
- **Statute citations** in the agency's working language (English
  + your national language, side by side)
- **Templates** in any pair: input language for the worker section,
  agency language for the inspector / legal section

A jurisdiction tuning may add a third language (e.g., a Saudi MHRSD
deployment may want Arabic + English + Tagalog because of the worker
base coming from PH).

## Pilot success metrics (30 to 60 days)

| Metric | Target |
|--------|--------|
| Audit time per recruitment agency | 30% reduction vs. current process |
| Statute citations correct (verified by staff lawyer) | 100% on the first 100 audits |
| Inspectors using the workbench voluntarily after week 2 | 80%+ |
| Complaints reclassified by workbench review (caught missed trafficking) | At least 1 per week on average |
| Audit log completeness | 100% of queries logged; chain integrity verified weekly |
| Network egress events from inspector devices | 0 |

## Procurement bullet points

For when your procurement officer needs the one-pager:

- **License:** MIT. No per-seat or per-query fee. Modify and
  self-host freely.
- **Vendor lock-in:** None. The model (Gemma 4) and the knowledge
  layer are open. If DueCare goes away tomorrow, your inspectors
  can keep using the workbench indefinitely on the version they
  have, and you can fork the codebase to maintain it yourselves.
- **Data residency:** All data on agency hardware. No SaaS, no
  third-party model API, no cloud egress. Air-gapped deployment
  supported.
- **Audit:** FOIA-defensible audit log built in. Hash-chained,
  exportable, tamper-evident.
- **Compliance:** Designed around ILO conventions (15 covered),
  Palermo Protocol, regional anti-trafficking treaties, and the
  destination/origin-country statutes for the 11 major migrant-
  labour corridors.
- **Support:** Open-source community + paid support tiers
  available from DueCare project staff.
- **Source:** `github.com/TaylorAmarelTech/gemma4_comp`. Public
  repository; agency self-hosts a private fork.

## What can go wrong + how to handle it

| Failure | Mitigation |
|---------|------------|
| Inspector's tablet runs out of battery in the field | Local cache lets the inspector keep collecting notes; sync to workbench when battery is back |
| Inspector incorrectly accepts a Gemma 4 statutory citation that is hallucinated | Citation matrix on every output is shown verbatim; inspector training drills the "verify the citation in the bundled register, not the model's claim" practice |
| Worker has insufficient command of the agency's working language to consent to an interview | Workbench prompts for an interpreter; logs the language barrier; flags case for follow-up |
| Senior inspector retires; jurisdiction tuning expertise leaves | Tuning is checked into the agency's internal repo as YAML; the next senior inspector reviews and updates rather than re-learning |
| A new statute is enacted mid-deployment | Jurisdiction tuning quarterly review picks it up; DueCare team can produce an interim patch in days if urgent |
| Inspector loses tablet in the field | Disk encryption prevents data exposure; audit log on the lost device is reconstructed from the central archive's last sync; replacement device re-issued from spares |

## See also

- [`03_government_api_integration.md`](03_government_api_integration.md) —
  bulk processing API path for back-office integration with
  existing case management
- [`03_government_jurisdiction_tuning.md`](03_government_jurisdiction_tuning.md) —
  detailed tuning checklist for the one-week pre-pilot pass
- [`oracle_email_solicitation.md`](oracle_email_solicitation.md) —
  optional component for soliciting input from partner NGOs +
  liaison officers + consular staff
- [`01_ngo_pilot_brief.md`](01_ngo_pilot_brief.md) — same software,
  different operator role; useful context for the agency's NGO
  partnership desk
