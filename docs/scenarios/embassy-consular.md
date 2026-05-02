# Embassy consular officer — protecting your nationals abroad

> **Persona.** You're a consular officer at an embassy or consulate
> in a destination country (Philippine Consulate Hong Kong,
> Indonesian Consulate Riyadh, Nepali Embassy Doha, Bangladeshi
> Embassy Beirut, Mexican Embassy in Washington, etc.). Distressed
> nationals come to you weekly — wage theft, passport withholding,
> abuse, repatriation. You have limited staff + limited authority
> in the host country + a backlog.
>
> **What this gives you.** A way to triage cases faster, draft
> verbal-note style complaints to the host-country regulator with
> the right statute citation, and produce a structured handoff
> packet for your origin-country labor ministry.

## TL;DR

| You'd normally... | With Duecare you... |
|---|---|
| Read each complaint individually + write notes by hand | Paste into the chat; get structured patterns + ILO indicators in 5s |
| Draft a verbal note to the host-country labor ministry | The Reports tab generates a draft cover letter with the right statute |
| Hand off to Manila / Jakarta / Kathmandu via email summary | Generate a markdown intake packet that the home-country regulator can act on directly |
| Wait days for headquarters to clarify which statute applies | Look up the controlling statute + ILO convention + corridor cap in real time |
| Track which recruiters generate complaints | Per-recruiter rollup via the metering layer |

## Set-up — what fits a consulate

Consulates typically have:
- Shared workstations on a closed network (not exposed to the
  open internet)
- Existing M365 / Google Workspace / similar SSO
- Strict data-residency: case data may not leave the country, OR
  may not leave the host-country embassy compound, OR specific
  data classes (PII, biometrics) have separate handling

The deployment shape that fits is the
[NGO-office-edge topology](./ngo-office-deployment.md) on a single
on-prem box (Mac mini / NUC / repurposed desktop) with these
modifications:

- **Behind your existing SSO.** Use the
  `docker-compose.auth.yml` overlay configured against M365 /
  Google Workspace per `docs/considerations/multi_tenancy.md`.
- **Multi-tenant per consular section.** Each section
  (Welfare, Legal, Migration) gets its own tenant id with its
  own audit-log shard + its own daily token budget.
- **Air-gapped or VPN-only network.** No outbound HTTPS except
  for the one-time model download. Disable cloud routing entirely.
- **NetworkPolicy default-deny** in the Helm chart if you're on
  k8s; otherwise the bundled compose stack's network is already
  isolated to a single bridge.

For a small consulate (1-3 consular officers + 1-2 admin staff),
single Mac mini is fine. For a large consulate / embassy with
20+ consular staff, k8s with the Helm chart.

## Workflow 1 — Walk-in worker triage

A worker walks in with a complaint. The desk officer:

1. Logs into the on-prem dashboard
2. In the chat, types the worker's narrative (composite labels
   only — "the worker from intake 2026-05-02", not real name)
3. The harness returns:
   - Patterns fired (passport withholding, wage theft, restriction
     of movement, debt bondage, etc.)
   - Controlling statute on the **host-country side** (HK Cap. 57,
     Saudi MoHR Domestic Worker Regulation, etc.)
   - Controlling statute on the **origin-country side** (POEA MC
     14-2017, BMET fee schedule, etc.)
   - ILO indicators
   - Recommended action (verbal note vs immediate repatriation
     vs civil refund-claim referral)

Auto-routed to the appropriate consular section's queue based
on classification.

## Workflow 2 — Drafting a verbal note

For host-country regulator engagement, the Reports tab generates
a cover letter. Edit to match diplomatic conventions:

- Replace the bundled "Dear Sir/Madam" with the host-country
  regulator's appropriate honorific
- Add your consulate's reference number + signature block
- Localize the date format
- Translate to the host country's official language if needed

The harness's draft contains:
- The statute the host country has agreed to enforce (often
  bilateral labor agreement reference)
- The specific ILO convention the host country has ratified
- The factual narrative based on the worker's intake

For complaints requiring a verbal note rather than an email/letter,
the structured fact pattern still saves hours of hand-drafting.

## Workflow 3 — Origin-country handoff

The Reports tab's "Generate intake document" produces a packet
your headquarters can act on:

- Worker's status (composite label, no PII)
- Corridor + current stage
- ILO indicator coverage
- Detailed risk findings with statutes + recommended next steps
- Fee table (if applicable) with legality flags
- Timeline of contacts with consular section
- Recommended NGO referrals on both sides

Email / fax / forward via your normal headquarters channel. The
markdown format renders cleanly in any email client + can be
printed for diplomatic-pouch transmission if needed.

## What's pre-loaded that helps a consulate specifically

The bundled corridor profiles include:

- **Origin-country labor regulator** with phone + URL (so you can
  call your counterpart at POEA / BMET / DoFE / BP2MI directly
  without looking up the contact each time)
- **Destination-country regulator** with phone + URL (so you can
  reach the host-country labor ministry directly)
- **3-4 NGO contacts per corridor** in the host country, vetted
  for quality. These are the organizations your worker can be
  referred to for shelter, legal aid, return assistance.

For PH-HK consular work specifically: POEA Anti-Illegal
Recruitment Branch (+63-2-8721-1144), HK Labour Department
Foreign Domestic Helpers Section (+852 2717 1771), Mission for
Migrant Workers HK (+852 2522 8264), PathFinders HK (+852 5190
4886), HELP for Domestic Workers (+852 2523 4020) — all bundled,
all addressable from the chat surface.

## Limitations specific to consular work

Honest counsel:

- **The harness doesn't know your bilateral labor agreements.**
  Some destination-country statutes are tempered by BLAs
  (e.g., the 2017 Kenya-Saudi BLA's zero-fee policy). The harness
  knows the published BLAs but not your consulate's case-by-case
  diplomatic understandings with the host-country MoHR.
- **The harness doesn't speak diplomatese.** Cover-letter drafts
  use the legal-aid clinic register; you'll want to redraft for
  diplomatic conventions.
- **The harness can't issue a travel document.** Repatriation
  decisions go through your existing visa + travel-document
  pipeline; the harness only structures the case for those
  decisions.
- **The harness doesn't know your consular case-management
  system.** Wire `/api/classify` to your CMS via the integration
  patterns in [`docs/scenarios/chief-architect.md`](./chief-architect.md).
- **The harness's NGO directory may be stale.** NGO contacts in
  destination countries change as funding shifts. Verify the
  phone is current before referring a worker.

## What you can NOT use Duecare for in consular work

- ❌ Issuing official statements that the bundled cover letters
  are diplomatic acts. They're drafts; your section chief signs.
- ❌ Treating the harness output as evidence. It's analysis.
  Evidence comes from the worker's own statement + documents +
  any host-country documentation.
- ❌ Sharing worker PII with the harness. Use composite labels.
  The harness records hashes only, not plaintext, but consular
  notes are subject to subpoena in some jurisdictions.

## Compliance considerations for embassies

Most foreign ministries have specific data-handling requirements:

- **Data residency** — if your country requires consular data to
  remain in the country (or in the embassy compound), the on-prem
  Mac mini deployment satisfies this.
- **Encryption at rest** — SQLCipher journal on Android; for the
  server's evidence-db, your IT must configure Postgres TDE / RDS
  encryption / etc.
- **Audit log retention** — the bundled 90-day default may need
  extension. Set `DUECARE_AUDIT_RETENTION_DAYS=2555` (7 years) for
  most embassies' record-keeping requirements.
- **No 3rd-party processors** — leave cloud routing OFF + leave
  internet search OFF if your foreign ministry's data-handling
  policy prohibits external data flows.

The vendor questionnaire at
[`docs/considerations/vendor_questionnaire.md`](../considerations/vendor_questionnaire.md)
pre-fills CAIQ-Lite for procurement. The compliance crosswalk at
[`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md)
covers SOC 2 / GDPR / ISO 27001 — your foreign ministry's specific
classification framework will need its own crosswalk done by your
IT security office.

## Day-1 setup (specific to a consulate)

1. **Get IT security sign-off.** Hand them the threat model + the
   compliance crosswalk + the vendor questionnaire. Most foreign
   ministries have a 2-4 week security review for new tools.
2. **Pick a hardware location.** A Mac mini in the consulate IT
   closet, on the consulate's internal network, behind the
   existing firewall. NOT on a desk where unauthorized visitors
   could touch it.
3. **Configure SSO.** `docker-compose.auth.yml` overlay against
   your foreign ministry's M365 / Google Workspace / Entra ID.
4. **Onboard one consular officer.** Have them run through one
   composite case end-to-end. Identify the diplomatic-conventions
   gap before rolling out to the full section.
5. **Add tenant config per section.** Welfare, Legal, Migration
   each get their own tenant id with their own daily token budget.

After 30 days of pilot use:
- Review with the section chiefs which workflows are saving time
  vs which are adding friction
- Customize the cover-letter templates for your consulate's
  diplomatic conventions
- Wire to your existing CMS via the OpenAPI 3 schema if not
  already done
- Train the next consular cohort

## What this enables that wasn't possible before

- **Consistent statute citation across cases handled by different
  officers.** No more "did Section A cite the right POEA MC?
  Section B's note cites a different one for the same fact pattern."
- **Mass-arrival processing.** When an airline strands 50 OFWs at
  arrivals (happens with corridor disputes), the welfare officer
  can triage all 50 in an hour instead of a day.
- **Quarterly enforcement reports** to your foreign ministry,
  generated from the audit log + per-pattern rollup.
- **Inter-embassy intelligence sharing.** If your consulate sees
  pattern X across 12 cases this quarter, your counterpart in a
  neighboring embassy can compare against their own data — same
  rule pack, same indicators, structurally compatible audit logs.

## Adjacent reads

- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) — your origin-country regulator counterparts
- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — the underlying setup pattern
- [`docs/scenarios/lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) — partner-NGO legal aid clinics' workflow
- [`docs/considerations/multi_tenancy.md`](../considerations/multi_tenancy.md) — per-section tenant isolation
- [`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md) — control map for your foreign ministry's IT-security review
