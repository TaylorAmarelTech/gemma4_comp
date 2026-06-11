# Path 3 — Jurisdiction tuning checklist

Every government deployment goes through this one-week tuning pass
before the workbench or API enters use. It is the difference between
a generic tool and one your agency can defend in front of a court,
a legislator, and a journalist.

Run by: 1 senior inspector + 1 staff lawyer + 1 DueCare engineer.
Duration: 5 working days. Output: a
`duecare-jurisdiction-<agency>-config.yaml` file + an updated
knowledge pack, both checked into your agency's internal repo.

## Day 1 — citation matrix

Goal: every statute, ILO convention article, and case-law reference
that DueCare returns in your jurisdiction has been verified by your
staff lawyer against the authoritative register.

Inputs:
- Bundled knowledge pack (439 GREP rules + 859 RAG documents + 15
  ILO conventions + 36 templates)
- Your agency's statute register (whatever the official source is —
  national legal database, regulator publications site, etc.)

Process:
1. DueCare engineer exports the citations applicable to your
   jurisdiction (`duecare knowledge export --citations --jurisdiction <code>`).
2. Staff lawyer walks the list. For each citation:
   - **Verified:** statute exists, current, says what the entry
     claims it says. Mark `verified: true` + `verified_at: <date>`.
   - **Stale:** statute exists but has been amended. Provide the
     current version; DueCare engineer updates the entry.
   - **Repealed:** statute no longer in force. Mark `superseded_by:
     <new statute>`; entry is removed or rewritten.
   - **Mis-cited:** statute exists but says something different.
     Provide the verbatim correct text; entry is rewritten.
3. Output: an annotated citation list checked into the agency repo.

This is the single most important day of the tuning. If your staff
lawyer cannot defend every citation the workbench produces, the
workbench is not ready for your agency.

## Day 2 — cluster weighting

Goal: the rubric the workbench uses internally matches your
agency's enforcement priorities.

The bundled rubric has six clusters with default thresholds:

| Cluster | Default threshold | When to raise it | When to lower it |
|---------|-------------------|------------------|------------------|
| Legal grounding + precision | 60% | Regulator focused on legal-grounds enforcement | Frontline complaint-intake where speed matters more than precision |
| Harm avoidance + refusal | 80% | Vulnerable-worker desk; trauma-survivor cases | Reduce only with extreme caution and a written justification |
| Worker protection + priority | 70% | Migrant-worker rights inspectorate | When the agency's primary mandate is something else (audit, license, criminal investigation) |
| Pattern + risk recognition | 60% | Investigative unit looking for emerging patterns | Routine compliance enforcement |
| Resources + actionability | 70% | Walk-in complaint desk; community-facing surface | Internal investigation (where resources are the agency's own) |
| Ethical framing | 70% | Public-communications-adjacent role | Internal-only |

Process:
1. DueCare engineer presents the default rubric and 5 to 10 sample
   case outputs.
2. Senior inspector reviews: does the rubric weight the right
   things for THIS agency's mandate?
3. Adjust thresholds; document each change with a one-line reason.
4. Output: `cluster_weights` section in the jurisdiction config.

Example YAML:

```yaml
agency: dmw-ph
jurisdiction_code: dmw-ph
locales: [en-PH, tl-PH]
cluster_weights:
  legal_grounding_precision:
    threshold: 0.70  # raised from default 0.60: regulator focus
    rationale: "DMW is a regulator; legal precision is a primary mandate."
  harm_avoidance_refusal:
    threshold: 0.85  # raised slightly: vulnerable-worker case base
    rationale: "Large proportion of DMW complaints involve worker safety."
  worker_protection_priority:
    threshold: 0.75  # raised from 0.70
    rationale: "Worker protection is a primary mandate per RA 8042 as amended."
  pattern_risk_recognition:
    threshold: 0.60  # unchanged
    rationale: ""
  resources_actionability:
    threshold: 0.70  # unchanged
    rationale: ""
  ethical_framing:
    threshold: 0.70  # unchanged
    rationale: ""
```

## Day 3 — agency-specific templates

Goal: the 34 bundled templates cover the major regulators
globally, but your agency may have enforcement tools that need
their own templates.

Common additions:

| Template | When you need it |
|----------|------------------|
| Administrative penalty notice | Any agency with administrative-fine authority |
| License suspension / revocation order | Recruitment-agency licensing regulators |
| Show-cause notice | Most regulators with hearing procedures |
| Referral to prosecutor | When the agency identifies criminal-level violations |
| Joint operation request | Cross-agency enforcement |
| Worker-side advisory | Inspector-mediated communication back to the worker |
| Site inspection report | Field inspectors |
| Provincial / regional summary report | For agencies with regional offices |

Process:
1. Senior inspector lists the agency's enforcement-instrument
   inventory.
2. For each item not covered by a bundled template, DueCare
   engineer produces a draft using the agency's existing template
   if available (Word doc, PDF) or the agency's regulation text.
3. Staff lawyer reviews each new template for legal sufficiency.
4. Output: agency-specific templates checked into the jurisdiction
   config under `templates_additional`.

## Day 4 — audit + privacy configuration

Goal: the workbench's FOIA audit log and PII handling match your
agency's data-governance policies.

Decisions:

| Decision | Default | Common variant |
|----------|---------|----------------|
| Audit retention | 5 years | Per agency record-retention policy |
| FOIA export format | Redacted JSON + summary CSV | Add agency-specific cover sheet |
| Inspector ID format | `inspector-<uuid>` | Agency employee ID (with separate access control on the audit store) |
| Query hash algorithm | SHA-256 | Some agencies require SHA-512 |
| PII redaction targets | Names, passport, phone, address, DOB | Add agency-specific (case number, license number) |
| Encryption at rest | Per device disk encryption | Agency may require additional layer |
| Encryption in transit | TLS 1.2+ | Same |
| Bearer token rotation | 90 days | Per agency security policy |
| API egress | None | Same — no exceptions |

Process:
1. DueCare engineer presents the audit configuration choices.
2. Agency IT / data governance officer reviews and decides.
3. Configuration written into the jurisdiction config.

## Day 5 — inspector training + shadow run

Goal: at least 2 inspectors can use the workbench / API
independently and have walked through real (mock) cases.

Schedule:

| Block | Activity |
|-------|----------|
| Morning, hour 1 | Workbench tour: pages, personas, activity log, templates, knowledge lookup |
| Morning, hour 2 | Sample case 1: clear-cut trafficking indicator. Inspector drives; engineer observes. |
| Morning, hour 3 | Sample case 2: ambiguous case. Inspector decides what to flag. |
| Afternoon, hour 1 | Sample case 3: contract substitution. Inspector drafts a notice using a template. |
| Afternoon, hour 2 | Sample case 4: a normal worker FAQ that should NOT be flagged. Verify the workbench handles it gracefully. |
| Afternoon, hour 3 | Audit log review: inspect what was logged for each case. Verify chain integrity. |

At end of day 5: senior inspector signs off on production
readiness. Pilot can begin.

## Output artefact

The full tuning produces one YAML file per agency:

```yaml
schema: duecare-jurisdiction-config/v1
agency: dmw-ph
jurisdiction_code: dmw-ph
agency_locale: en-PH
agency_languages: [en, tl]
duecare_version: "0.1.0"
knowledge_pack_version: "2026-05-22-jurisdiction-dmw"
created_at: "2026-05-22"
created_by: ["sr-inspector-id-redacted", "staff-lawyer-id-redacted", "duecare-engineer-id-redacted"]

cluster_weights:
  legal_grounding_precision: {threshold: 0.70, rationale: "..."}
  # ... (see Day 2)

citation_overrides:
  - id: "poea_mc_14_2017"
    verified: true
    verified_at: "2026-05-21"
    notes: "Verified against POEA Memorandum Circulars register."

templates_additional:
  - id: "dmw_show_cause_notice_v3"
    purpose: "Administrative show-cause notice for recruitment-agency licensees"
    file: "templates/dmw_show_cause_notice_v3.md"

audit:
  retention_years: 7
  hash_algorithm: "sha256"
  pii_redaction_targets:
    - "name"
    - "passport_number"
    - "phone"
    - "address"
    - "dob"
    - "philsys_id"
  api_egress_allowed: false

unsupervised_use_allowed: false  # workbench requires inspector login
notes: |
  Tuning conducted 2026-05-19 to 2026-05-22. Signed off by senior
  inspector and staff lawyer.
```

This YAML is checked into the agency's internal repo. It is the
authoritative configuration for the agency's DueCare deployment.

## When you re-do the tuning

Quarterly review (4 hours):

- Walk the citations: any new statutes? Any amendments?
- Walk the templates: any new enforcement instruments?
- Walk the audit log: any incidents this quarter? Anything to
  change?
- Walk the rubric: does the cluster weighting still match agency
  priorities?

Plus any time:

- A new senior statute is enacted (immediate update)
- A new agency mandate is added (cluster reweighting)
- A FOIA / right-to-information request reveals an issue with audit
  configuration (immediate update)
- A pilot turns up cases the rubric misses (rubric tuning)

## See also

- [`03_government_workbench.md`](03_government_workbench.md) — field
  workbench surface
- [`03_government_api_integration.md`](03_government_api_integration.md) —
  bulk processing API surface
- [`02_network_curator_role.md`](02_network_curator_role.md) — same
  citation-verification rigour at a different scale
