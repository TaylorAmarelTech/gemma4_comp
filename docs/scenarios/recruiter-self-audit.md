# Compliance officer at a recruitment agency — self-audit

> **Persona.** You're the compliance officer (or owner) at a
> licensed recruitment agency. You want to make sure your
> contracts, fee schedules, recruiter scripts, and partner-agency
> arrangements wouldn't trigger a regulator's enforcement action.
> You're not a target — you want to stay clean.
>
> **What this gives you.** A way to run your own contracts and
> fee schedules through the same harness that NGOs + regulators
> use, see what would fire, and fix issues before they reach a
> worker / regulator.
>
> **Why this is useful.** Compliance teams typically learn what's
> illegal from a regulator's complaint letter (too late). The
> harness lets you find the same patterns proactively, before
> anyone files anything against you.

## TL;DR

| You'd normally... | With Duecare you... |
|---|---|
| Wait for a regulator to flag a fee | Run your fee schedule through the corridor classifier in 30 seconds |
| Have your lawyer review every new contract template | Pre-screen the template; lawyer reviews only the flagged sections |
| Reactively fix issues after a complaint | Quarterly self-audit catches issues before they reach the field |
| Hope your sub-agents follow your rules | Run their training scripts through the harness |

This is **defensive compliance**, not gaming the system. The same
patterns the harness flags are what an ILO indicator scoring
auditor or a destination-country labor-tribunal hearing would
flag. Use it as a quality check on the work your team is already
doing, not as a way to find loopholes.

## What you can audit

### 1. Fee schedules

Paste your fee schedule into the chat:

> "We charge our Indonesian domestic workers going to Hong Kong
> the following fees:
> - Training fee: IDR 8,000,000
> - Medical: IDR 1,500,000
> - Visa processing: IDR 2,000,000
> - Insurance: IDR 500,000
> Total: IDR 12,000,000 (~$770 USD).
> What does your harness say about this?"

The harness will:
- Look up the corridor (ID-HK) — the published cap is ~SGD 1,500
  / ~USD 1,100 per Indonesian Permenaker 9/2019
- Compare your $770 to the cap (you're under — good)
- Cite the controlling regulation
- Flag any specific fee categories that the regulation explicitly
  prohibits (e.g., "training fee" labels are subject to extra
  scrutiny in some corridors)
- Note any documentation requirements (receipts, written disclosures)

### 2. Contract templates

Paste a contract clause:

> "Section 12: The Worker shall reside at the Employer's residence
> and shall not leave the premises without express permission of
> the Employer. The Worker's passport shall be held by the Employer
> for safekeeping during the term of this Agreement."

The harness flags:
- Restriction-of-movement clause (ILO C029 indicator #5)
- Passport-withholding clause (ILO C029 indicator #8) — the most
  primary forced-labour indicator
- Cites HK Foreign Domestic Helper Code of Practice + ILO C189
  Article 9 explicitly prohibiting these
- Recommends rewording: passport stays with worker; movement
  restrictions tied to specific safety / contract-defined hours
  only

A clean contract before signing avoids: a labor-tribunal claim
later, a regulator's investigation, a partner agency in the
destination country refusing to onboard new workers from you.

### 3. Recruiter / sub-agent training scripts

Paste your sub-agent's pre-departure briefing script:

> "Tell the worker: 'Sign here for the loan; the agency in Hong
> Kong will deduct ₱5,000 per month from your salary. If you can't
> pay, you'll be sent back home and lose your deposit.'"

The harness flags:
- Debt-bondage pattern (loan + salary deduction + threat of
  forfeit) — ILO C029 indicator #4
- Coercion pattern (threat of repatriation + financial loss) —
  ILO C029 indicator #2
- Cites POEA MC + ILO C095 Article 8 (deduction prohibition
  without explicit worker consent)

Useful for catching when a sub-agent has drifted from your
official script.

### 4. Marketing materials

Some agencies' marketing materials contain prohibited promises
(guaranteed employment, guaranteed salary, "no qualifications
needed"). Run your Facebook ads, your website copy, your job-fair
flyers through the harness:

> "Earn ₱40,000 per month working in Singapore as a domestic helper.
> No experience required. We handle everything for free. Apply now."

The harness flags:
- "No experience required" + specific salary promise without
  contract — high-risk recruitment-fraud pattern
- "Free" claim — most regulators require disclosure that some
  fees apply
- Cites POEA MC + Singapore MOM advertising rules

## How to set it up for compliance use

For a recruitment agency, the deployment shape is the same as the
[NGO-office topology](./ngo-office-deployment.md): a single Mac
mini in your office, on the office Wi-Fi.

Differences in configuration:

```yaml
# tenants.yaml — one tenant per compliance officer
tenants:
  - id: compliance-lead@your-agency.com
    daily_token_budget: 5_000_000
  - id: legal-counsel@your-agency.com
    daily_token_budget: 2_000_000
```

Optional: load your own corpus alongside the bundled one. Your
internal compliance manual + your destination countries' specific
regulations + your historical complaint dispositions become RAG
documents the harness can cite alongside the public corpus. Use
the [extension pack format](../extension_pack_format.md).

## A quarterly self-audit cycle

Every quarter:

| Week | Activity |
|---|---|
| 1 | Compliance lead pastes the active fee schedule for each corridor; harness classifies; lead reviews flagged items |
| 1 | Compliance lead pastes the active contract template; same |
| 2 | Sample 20 sub-agent training scripts (or the most recent version of each); same |
| 2 | Sample 50 recent worker complaints (with PII redacted); harness classifies; lead reviews patterns |
| 3 | Lead drafts a remediation list for any flagged items; circulates to operations + legal counsel |
| 4 | Operations implements changes; legal counsel signs off; lead re-runs the audit to confirm zero remaining flags |

A 2-3 hour exercise per quarter. Catches issues that would
otherwise surface in a regulator's enforcement letter (much more
expensive to fix at that point).

## What the harness CANNOT do for compliance

- **Cannot guarantee zero regulatory action.** Regulators have
  discretion. The harness reflects published statutes; an
  inspector may apply a stricter interpretation.
- **Cannot replace your lawyer.** Use the flagged items as a
  shortlist for legal review, not as legal advice.
- **Cannot detect issues outside the trained corpus.** If your
  primary corridor isn't in the bundled 6 (PH-HK, ID-HK, PH-SA,
  NP-SA, BD-SA, ID-SG), you'll need to extend the corpus or
  treat the harness output as suggestive only for that corridor.
- **Cannot tell you about historical patterns at YOUR agency
  specifically.** It works on the document you paste, not on your
  case-management system. For pattern analysis across your own
  history, use the [regulator-pattern-analysis.md](./regulator-pattern-analysis.md)
  workflow.

## What the harness explicitly will NOT help you do

- **Loophole-hunting.** "Show me how to label this fee so it
  doesn't trigger your rule" — the harness fires on substance
  (consistent with Palermo Article 3(b) — consent of the victim
  is irrelevant when coercion / deception means are used). Trying
  to relabel an illegal fee will still fire the relevant pattern.
- **Drafting evasion clauses.** The harness's RAG corpus is
  designed to identify substance-over-form patterns; it won't
  draft language that obscures the substance.
- **Generating false documentation.** The harness explicitly
  refuses requests like "draft a fake receipt for $X."

If you're using the tool to find loopholes, you've found a
different tool. Stop reading.

## Adjacent reads

- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) — what regulators do with the same harness
- [`docs/scenarios/lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) — what counsel does
- [`docs/scenarios/it-director.md`](./it-director.md) — set up the office Mac mini that runs all this
- [`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md) — compliance crosswalk for SOC 2 / GDPR / HIPAA
- [`docs/extension_pack_format.md`](../extension_pack_format.md) — load your internal compliance manual as a RAG corpus

## Bottom line

A recruitment agency that runs its templates + scripts + fee
schedules through Duecare quarterly catches roughly the issues a
regulator would catch in an investigation — for $250-800 of
hardware + 8 hours of compliance-officer time per year.

That's defensible procurement. It's also the right thing to do
for the workers your agency places.
