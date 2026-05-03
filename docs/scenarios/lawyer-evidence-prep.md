# Legal aid lawyer / paralegal — preparing a case

> **Persona.** You're a lawyer or paralegal at an immigrant
> rights / labor / human-trafficking legal aid clinic. A client
> walks in with a recruitment-fee complaint, a wage claim, or a
> trafficking allegation. You have 30-60 minutes for an initial
> consultation, then maybe a week to decide whether to file.
>
> **What this gives you.** A way to do the legal-research part of
> intake in 10 minutes instead of an hour, and to hand the case to
> co-counsel with a structured packet that already cites the
> controlling statute.

## TL;DR for a busy lawyer

| You'd normally... | With Duecare you... | Time saved |
|---|---|---|
| Look up POEA MC 14-2017 to confirm the fee cap | Type "is a 50k PHP training fee legal for PH→HK domestic worker" → get statute citation in 5s | 10 min |
| Cross-reference ILO C181 + relevant ILO indicators | The chat surface auto-cites them | 15 min |
| Draft a refund-claim cover letter from scratch | The Reports tab generates a draft you edit | 30 min |
| Write the case summary for co-counsel handoff | "Generate intake document" → markdown report | 20 min |
| Lookup the right NGO contact for shelter referral in Hong Kong | The corridor lookup returns Mission for Migrant Workers + PathFinders + HELP for DW with phones | 5 min |

Total: roughly 80 minutes saved per intake. For a clinic doing
5 intakes / week, that's a paralegal recovered.

## Before you adopt

### What it is + isn't, in lawyer terms

| It IS | It is NOT |
|---|---|
| A research assistant that knows recruitment law | A lawyer |
| A drafting tool for refund-claim cover letters | A representation |
| A pattern-recognition layer over your client's facts | An evidentiary opinion |
| A way to cite ILO conventions correctly the first time | A substitute for current statute lookup |
| A way to package an intake for co-counsel | A substitute for your professional judgment |

You verify every cited statute against the source before relying
on it in writing. The harness is faster than Google; it is not
authoritative.

### Privilege + ethics

Your client's communications with you are privileged. This means:

- **Do NOT type your client's actual identity into the chat.** Use
  composite labels ("Client A", "the worker from intake 2026-05-02").
  The chat surface is a tool you control; if it leaks, you have
  an ethics problem.
- **Do NOT type the opposing recruiter's name in a way that
  attributes a specific allegation.** Use "the recruiter from the
  Causeway Bay placement" or similar. This is the same discipline
  you already apply to case notes that may be subpoenaed.
- **The audit log records hashes, not plaintext.** But your
  device's screen, your browser cache, and the Mac mini's RAM
  during the chat are all reachable by a sufficiently determined
  adversary. Discipline matters.

The deployment shape that fits a legal aid clinic best is the
[NGO-office on-prem topology](./ngo-office-deployment.md): a Mac
mini in your office, on the office Wi-Fi, behind your office's
existing firewall. No data leaves the building.

### Bar / state-specific compliance

Most state bars have specific guidance on AI tools in client
communications. The current consensus across NY, CA, MA, FL, IL,
TX (as of 2026):

- AI tools must not replace legal judgment
- AI-generated drafts must be reviewed by a human lawyer
- Client must be informed if AI is used in their representation
- Confidential client info should not be sent to a third-party
  vendor without informed consent

The on-prem deployment satisfies the third + fourth points by
design — nothing leaves your office. The first two are workflow
discipline, same as any tool.

## A 45-minute intake with Duecare

### Minute 0-5: Greet + create a case

In the chat surface (or the Android app on your phone if you're
in the field):

- Journal tab → Add entry
- Title: "Initial intake — Client A — 2026-05-02"
- Body: brief notes on the situation (who, what, where) using
  composite labels

### Minute 5-15: Run the guided intake

The 10-question wizard captures the facts in a structured way.
You ask the questions in plain language, type the answers as
the client says them.

Each answer becomes an auto-tagged journal entry. The patterns
that fire (passport withholding, fee camouflage, debt bondage,
threats) are the basis of any complaint you might file.

### Minute 15-25: Verify the legal landscape

For each pattern that fired, the Reports tab cites:
- The controlling statute (e.g., POEA MC 14-2017 §3 for the
  PH→HK zero-fee corridor)
- The ILO convention number
- The recommended next step

Cross-check each citation against the official source. They're
typically right (the corpus is hand-curated) but you need to
confirm before relying.

### Minute 25-35: Document the fees

For every fee paid, click **Add fee payment**:
- Recipient name, type
- Amount, currency
- Purpose (as labeled by recruiter), wording recruiter used
- Payment method (cash, bank transfer, salary deduction, etc.)

The harness flags illegal fees against the corridor cap. For each
flagged fee, a "Start refund claim" button appears.

### Minute 35-40: Draft the refund-claim packet

Click "Start refund claim" on each illegal fee. The harness drafts:
- A cover letter to the controlling regulator (POEA, BMET, BP2MI,
  DoFE, BMET) with the right statute, the right amount, the
  payment date + method, and the recipient
- A delivery message ready for email / fax / WhatsApp

Edit the draft. You'll add:
- Your firm's contact info
- The specific case number you'll use internally
- Anything jurisdiction-specific the harness doesn't know

### Minute 40-45: Generate the intake packet

Reports tab → Generate intake document.

The harness produces a single markdown report combining:
- Worker context (corridor, current stage)
- ILO indicator coverage
- Detailed risk findings with statute citations
- Fee table with legality flags
- Chronological timeline by stage of journey
- Recommended NGO + regulator contacts

Hand to client + save to case file. If the case warrants co-counsel
or a partner organization, share via email / Signal.

## What's worth a cite, what to verify yourself

| Citation | Trust it as-is |
|---|---|
| ILO Convention numbers (C029, C181, C189, C095) | Yes — these don't change |
| ILO C029 indicator numbers (1-11) | Yes — canonical taxonomy |
| Country labour-recruitment statute names (POEA MC 14-2017, etc.) | Verify the section number on the regulator's website |
| Fee cap amounts (₱0 PH→HK, USD 1,850 ID→HK, etc.) | Verify with the regulator — these change |
| NGO contact phones | Verify — some change frequently |
| ILO Forced Labour Indicator descriptions | Yes — directly from ILO |
| Generic legal advice ("you should consult a lawyer") | Confirm before delivering to client |
| Specific predictions ("you'll get a refund in 90 days") | Never trust — strip from any draft |

The harness shows you the source for everything it asserts. Verify
the source before relying.

## Handing off to co-counsel

The intake document is shareable as markdown. For an experienced
co-counsel:

- They get the structured facts in 10 minutes of reading
- They see the cited statute + ILO indicator immediately
- They know which NGO + regulator to contact
- They know which fees you've drafted refund claims for

For a junior co-counsel or paralegal:

- The harness's "what this means" + "next step" sections double
  as a teaching aid
- They can run their own intakes with the same wizard

## What to do when the harness is wrong

It will be wrong. Specifically:

- A new POEA / BMET regulation isn't in the bundled corpus yet
- A specific case-law citation gets the year wrong
- A jurisdiction the harness doesn't know about (e.g., a small
  destination country) gets a fallback "consult local counsel"

When this happens:

1. Don't use the wrong citation. Cite the correct source you found.
2. File an issue at https://github.com/TaylorAmarelTech/gemma4_comp/issues
   with the prompt + the wrong response (PII redacted) + the right
   answer. The corpus gets updated.
3. If the corridor / regulator is missing entirely, you can add it
   via the [extension pack format](../extension_pack_format.md) +
   contribute back.

## Complementary tools

Duecare doesn't try to be your case management system. Common pairings:

| What you need | Tools to use alongside |
|---|---|
| Case management (calendar, conflict checks, time tracking) | Clio, MyCase, PracticePanther |
| Document automation (templates beyond refund claims) | HotDocs, Lawyaw, Documate |
| E-discovery on opposing recruiter's emails | Relativity, Logikcull |
| Translation of contract photos | DeepL Pro, Google Translate (with confidentiality precautions) |
| Witness interview transcription | Otter.ai, Trint (with informed consent) |

## When you'd skip Duecare for a particular case

- **Pure visa work** — no recruitment-fee or trafficking dimension.
  Use a visa-specific tool.
- **Civil tort outside labor** — the harness is labor + trafficking
  domain-specific.
- **Criminal defense for a client charged under recruitment law**
  — the harness's bias is toward the worker; for the recruiter's
  defense, cross-check every claim independently.

## Adjacent reads

- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — set up the office Mac mini that runs all this
- [`docs/scenarios/caseworker_workflow.md`](./caseworker_workflow.md) — what a non-lawyer caseworker uses it for
- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) — what your government counterparts do with it
- [Android v0.9 APK](https://github.com/TaylorAmarelTech/duecare-journey-android/releases) — for field-intake on a phone

## Bottom line

If you can adopt the Mac mini setup ([NGO office walkthrough](./ngo-office-deployment.md)),
you save ~80 min per intake. Cost: $250-800 hardware + 30 min/week
of an IT-comfortable colleague. ROI is one paralegal-equivalent
recovered for direct service per ~60 cases/year processed.

Adoption hurdle is the privacy discipline (composite labels, no
real PII typed) — same hurdle as any case-management tool.
