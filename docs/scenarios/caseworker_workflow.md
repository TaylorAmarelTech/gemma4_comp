# Caseworker workflow — case intake to NGO referral, end to end

> **Audience.** A caseworker at an NGO that has deployed Duecare per
> [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md).
> This doc walks through one complete case from first contact to
> handoff — the day-to-day rhythm of using the system.

## Scenario

A worker walks into your NGO's office. She's escaped a domestic-work
placement in Hong Kong and arrived back in the Philippines two weeks
ago. She has a phone with photos of her contract, her receipts for
agency fees, and a few WhatsApp screenshots from her former
recruiter. She wants to know: is she owed money? Does she have a
case? Where does she go next?

You have ~45 minutes for this intake.

## Step 1 — Greet + create a case (3 min)

In the office, you're sitting at the front-desk Mac mini that runs
Duecare. Open `http://duecare.local` in the browser.

1. **Journal tab** → **Add entry** (the + button).
2. Set kind to NOTE; title: "Initial intake — Worker A — 2026-05-02";
   body: "First meeting, post-return. PH-HK domestic-work placement.
   Has photo evidence. Walking through guided intake next."
3. Save.

The entry appears in the Journal tab. **The worker's real name is
nowhere — you used "Worker A".** This matters because:
- Caseworker notes can be subpoenaed
- Multiple caseworkers may eventually open this case
- The Reports tab will produce a shareable doc — you don't want
  that doc to leak the worker's identity if you forward it

## Step 2 — Run the guided intake (8 min)

Above the journal, click **Quick guided intake**.

The wizard walks through 10 questions. For each, ask the worker
in plain language and type her answer:

1. **Recruiter name** — "Pacific Coast Manpower Inc., contact
   person Maria. Originally introduced by my cousin's friend."
2. **Recruiter license** — "She showed me a POEA license number
   when I asked: POEA-1234-5678. I don't know if it was real."
3. **Fees paid** — "PHP 50,000 'training fee' before they would
   release my visa. PHP 10,000 medical. Both via BPI bank transfer
   to the agency's account."
4. **Loan terms** — "I borrowed PHP 80,000 from a lender Maria
   introduced me to. 5% per month interest. Monthly payments
   deducted from my salary in Hong Kong."
5. **Contract signed** — "Yes, signed in English. Contract said
   HKD 4,870/month, 1 day off per week."
6. **Wage promise** — "What was promised matched the contract
   on paper. In practice I got HKD 3,500 because of the loan
   deduction."
7. **Passport status** — "My employer in Hong Kong took it
   'for safekeeping'. I never had it back until I returned."
8. **Destination address** — "Mr. and Mrs. Wong, Causeway Bay.
   I never saw a written address before arrival."
9. **Communication restrictions** — "I could call home Sundays
   only. The employer kept my SIM card during the week."
10. **Threats** — "Maria warned me before I left that if I
    quit my employer, she would 'tell the agency to blacklist
    me' and I'd never work overseas again."

The wizard creates **10 journal entries** (one per non-empty
answer). Each entry runs through the auto-risk-tagger.

## Step 3 — Review the Reports tab (5 min)

Click **Reports**.

Top of the tab — **Case overview**:
- **Entries:** 11 (the 10 from the wizard + your initial NOTE)
- **Fee lines:** ≥ 3 (the wizard's free-text answers extracted +
  any structured ones you'll add next)
- **Risk flags:** depending on which patterns matched, ~6-8
- **Critical risks:** likely 3-4 (passport withholding, fee
  camouflage, debt bondage, threat)

**ILO indicator coverage** — the wizard's answers should fire:
- #1 Physical & sexual violence — typically not (no answer claimed it)
- #2 Intimidation & threats — fires (Maria's blacklist threat)
- #4 Debt bondage — fires (loan + salary deduction)
- #6 Isolation — fires (SIM card kept)
- #8 Retention of identity documents — fires (passport-for-safekeeping)
- #9 Deception — fires (zero-fee corridor; PHP 60k charged anyway)

**Detailed risk findings** — each fired rule shows:
- The matched phrase from the entry
- The ILO indicator number
- The controlling statute (e.g., POEA Memo Circular 14-2017 §3)
- A recommended next step

Take a screenshot or copy these citations. They're gold for the
referral packet.

## Step 4 — Add structured fee payments (5 min)

The wizard captured fees as free text; the regex extractor catches
most of them. For higher-quality data, **add structured fees**:

In Reports → **Add fee payment**:

| Field | Value |
|---|---|
| Recipient name | Pacific Coast Manpower Inc. |
| Recipient type | RECRUITMENT_AGENCY |
| Amount | 50000 |
| Currency | PHP |
| Purpose label | training fee |
| Recipient's wording | "Pre-departure orientation training, mandatory per agency policy" |
| Payment method | BANK_TRANSFER |
| Worker's notes | "Paid 2026-04-19 via BPI; receipt screenshot in worker's phone" |

Save. The fee runs through the StructuredFeeAssessor:
- Looks up corridor PH-HK → zero-fee policy under POEA MC 14-2017
- Flags the fee as **ILLEGAL** with the controlling statute attached
- Adds an ILLEGAL **LegalAssessment** row

Repeat for the PHP 10,000 medical and (if you choose) the PHP
80,000 loan.

## Step 5 — Start a refund claim (3 min)

Below the Fee table, every illegal fee row now shows a **"Start
refund claim"** button.

Click it for the PHP 50,000 training fee. The system:
- Creates a draft `RefundClaim` row
- Pre-fills a cover letter naming Pacific Coast Manpower, the
  amount, the controlling POEA MC + ILO C181 citation, the worker's
  payment method, the request for refund + investigation
- Generates a delivery message ready for the OS share sheet

Edit the cover letter inline if needed (add the worker's preferred
contact channel; remove anything you don't want forwarded).

Repeat for any other illegal fees. The Refund claims section now
shows N drafts.

## Step 6 — Generate the NGO intake document (2 min)

In Reports, scroll down to **Generate intake document**.

Click. The system produces a single markdown document combining:

- **Worker context** — corridor (PH-HK), current stage (EXIT),
  entry count, date range
- **ILO C029 indicator coverage** — table of which indicators fired,
  how many times each
- **Detailed risk findings** — every flagged GREP rule with statute
  + reasoning + next step
- **Fee table** — every fee paid, with legality flag, with totals
  by currency, with illegal-totals separately
- **Chronological timeline** — every event grouped by stage of
  journey
- **Recommended NGO + regulator contacts** — for the PH-HK corridor:
  POEA Anti-Illegal Recruitment Branch, Mission for Migrant Workers
  HK, PathFinders HK, HELP for Domestic Workers + their phone
  numbers + URLs

Tap **Share**. Pick the destination (email to a partner NGO; Signal
to the worker's lawyer; print to PDF; save to a USB drive).

The document is **markdown** so it renders cleanly in any messenger,
email, or PDF generator.

## Step 7 — Hand off + book follow-up (5 min)

The intake document is the deliverable. Hand the worker (a printed
copy if she wants) and:

- Email a copy to your partner NGO that handles refund-claim filing
  with POEA
- Email a copy to your standing-counsel lawyer for review
- Book the worker's follow-up appointment in two weeks to track:
  - Has she filed the refund claim
  - Has the lender (the loan is independently illegal under HK Cap.
    163 §24 if the APR > 60% — ask the worker for the loan
    paperwork at the next visit)
  - Does she need shelter referral, medical referral, mental-health
    referral

## Step 8 — Close the loop in the Journal (5 min)

Back in the Journal tab:
- Add a NOTE: "Intake complete 2026-05-02. Generated NGO intake
  doc. Forwarded to Polaris-PH and Atty. Reyes. Follow-up booked
  2026-05-16."
- Add a NOTE for each handoff: "Forwarded to Polaris-PH at intake@
  polaris-pilipinas.org" / "Forwarded to Atty. Reyes at her firm
  email"

This becomes the audit trail for what your office actually did.

## Step 9 — At the end of the day

```bash
# On the Mac mini terminal
make doctor   # confirm everything healthy after a day of use
```

Backups run automatically overnight per the cron job from
[`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md#step-5--schedule-nightly-backups-10-min).

## Total time budget for this case

| Step | Time |
|---|---:|
| 1. Greet + create a case | 3 min |
| 2. Guided intake | 8 min |
| 3. Review Reports tab | 5 min |
| 4. Add structured fees | 5 min |
| 5. Start refund claims | 3 min |
| 6. Generate intake document | 2 min |
| 7. Hand off + book follow-up | 5 min |
| 8. Close the loop | 5 min |
| **Total** | **36 min** |

vs the same intake without Duecare:
- Looking up POEA MC 14-2017 manually + cross-referencing ILO
  conventions — 30 min
- Drafting a referral packet from scratch in Word — 60 min
- Researching corridor-specific NGO contacts — 15 min
- Writing the cover letter for the refund claim — 20 min

**Savings: ~2 hours per intake.** With 5 intakes a day across the
office, that's a caseworker FTE recovered for direct service.

## When to deviate from this workflow

- **Worker in active danger** — skip the wizard. Use the chat
  surface to look up the destination-country emergency hotline,
  hand the worker the number, then circle back to the structured
  intake later.
- **Mass-arrival scenario** (e.g., a returning batch of OFWs) —
  use the API (`POST /api/chat`) from a script to bulk-pre-populate
  cases, then have caseworkers triage the auto-tagged risks.
- **Worker doesn't speak English** — chat surface accepts any
  language but the GREP rules + intake wizard text are English
  only. Localization of the worker-facing surface is on the
  v0.8 roadmap.

## Related

- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — the setup that makes this workflow possible
- [`docs/considerations/multi_tenancy.md`](../considerations/multi_tenancy.md) — when you have ≥ 5 caseworkers
- [Android v0.9 APK](https://github.com/TaylorAmarelTech/duecare-journey-android/releases) — the same workflow for caseworkers in the field
- [`docs/embedding_guide.md`](../embedding_guide.md) — bring the chat surface to where the worker already is (Telegram / WhatsApp / Messenger / NGO website)
