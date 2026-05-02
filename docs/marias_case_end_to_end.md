# Maria's case — end to end through the Duecare ecosystem

> **What this is.** A composite case (named "Maria" — labeled
> as composite throughout the writeup + video) traced through
> every layer of the Duecare ecosystem. Use this for the writeup,
> the video voice-over, NGO-pitch decks, journalist briefings,
> and the educator workshops. Every step is enabled by code that
> ships today.
>
> **How to read.** Each section is one persona's slice of the
> case. Read top to bottom for the full narrative. Read just one
> section for that persona's view. Cross-references in
> `[brackets]` point to the docs that go deeper.

## Day -90 — Maria decides to go

**Composite background.** Maria, 24, from a town outside Cebu. Two
kids; parents helping with care. Wants to work in Hong Kong as a
domestic helper. Cousin's friend introduced her to a recruiter
who showed a POEA license number.

The recruiter says: ₱50,000 for "training fee," ₱10,000 medical,
₱2,000 admin. Total ₱62,000. Plus the recruiter introduces her to
a lender who'll cover ₱80,000 at 5% per month interest, paid back
through her future salary.

This is a textbook PH-HK fee-camouflage + debt-bondage pattern.
The published Philippine law (POEA Memorandum Circular 14-2017 §3)
says the placement fee for Filipino domestic workers going to
Hong Kong is ₱0. The fees Maria is being asked to pay are recoverable.

Maria doesn't know this.

## Day -90 — Maria installs Duecare Journey

**Persona path:** [`docs/scenarios/worker-self-help.md`](scenarios/worker-self-help.md)

Maria's brother shows her a TikTok recommending Duecare Journey.
She installs the v0.9 APK from GitHub Releases on her Android phone:

```
https://github.com/TaylorAmarelTech/duecare-journey-android/releases
```

She runs the **guided intake** — 10 questions, ~8 minutes:
- Recruiter name (uses "Maria from XYZ Manpower" as a label, not a real name)
- POEA license number she was shown
- Fees paid + currency + payment method
- Loan terms
- Whether she signed a contract (yes, in English)
- Wage promised (HKD 4,870/month per contract; recruiter said HKD 4,500)
- Where her passport is now (with her, not yet given to anyone)
- Destination employer + address (incomplete — she'll find out on
  arrival)
- Communication freedom (recruiter takes her phone in evenings
  before departure)
- Threats received (recruiter said: if she quits her employer in
  HK, she'll be "blacklisted" and never work overseas again)

She taps **Reports**. The Reports tab shows:

- **Critical risks (3):** debt-bondage pattern, communication
  restriction, intimidation/threats
- **High risks (2):** fee-camouflage (₱62k charged on a zero-fee
  corridor), wage discrepancy (contract HKD 4,870 vs verbal HKD 4,500)
- **ILO indicators fired:** #2 (intimidation), #4 (debt bondage),
  #6 (isolation), #9 (deception), #4 (financial-fraud-shaped fee
  camouflage)
- **Statute citations:** POEA MC 14-2017 §3 (zero placement fee),
  ILO C181 Art. 7, ILO C189 Art. 9 + 10
- **Recommended NGO contacts** for PH-HK corridor: Mission for
  Migrant Workers HK, PathFinders HK, HELP for Domestic Workers

Maria taps **Generate intake document**. The app produces a
markdown packet with everything above plus a chronological
timeline + drafted refund-claim cover letter.

She doesn't share the packet yet — she's still going. But now she
knows what's documented + has the receipts ready.

## Day 0 — Maria arrives in HK

Her HK employer (the Wong household, Causeway Bay) takes her
passport "for safekeeping" the first night. Maria opens her Duecare
app, takes a quick photo of her now-empty passport pouch, and
adds a Journal entry: *"2026-05-02. Mr. Wong took my passport
'for safekeeping' tonight. Said I'll get it back when I leave HK
in 2 years."*

The auto-tagger fires the `passport-withholding` GREP rule. The
Reports tab now shows ILO indicator #8 (retention of identity
documents) — the most primary forced-labour indicator.

Within 90 days, Maria has 23 journal entries documenting:
- Salary deductions to the lender (HKD 1,000/month against the loan)
- The Wong household keeping her phone weekdays (only Sundays
  available for calls home)
- 14-hour workdays with no statutory rest day
- The Wong's threat (Mrs. Wong's): "If you quit, the agency in
  Manila will take your house deposit."

Each entry auto-tags. The Reports tab now shows 9 of 11 ILO
indicators firing. The intake document is now substantial.

## Day 90 — Mission for Migrant Workers HK contact

Sundays are Maria's only free time. She visits the Worldwide House
mall in Central HK, where MfMW HK runs a drop-in counselling
centre. She shows the caseworker her phone.

**Persona path:** [`docs/scenarios/caseworker_workflow.md`](scenarios/caseworker_workflow.md)

The caseworker, Anna, runs MfMW HK's Mac mini in the office.
She opens Duecare on the office workstation:

```bash
http://duecare.local
```

(Their Mac mini was deployed per
[`docs/scenarios/ngo-office-deployment.md`](scenarios/ngo-office-deployment.md)
two months earlier.)

Anna creates a journal entry: *"2026-08-04. Walk-in: Worker A. PH-HK
domestic-worker placement. Claims passport withholding + wage
deduction + threats. Has comprehensive prior journal entries from
her own phone."*

She asks Maria to share her phone's intake document via QR code
(generated by tapping Share → Local network in the app). Anna's
workstation receives the markdown packet.

The caseworker reviews:
- 23 journal entries with timestamps + matched patterns
- 8 fee payments documented (originally ₱62k + 8 months of HKD
  1k loan deductions = ~HKD 8k recoverable)
- 9 of 11 ILO indicators fired
- Drafted refund-claim cover letter (PH-side regulator: POEA,
  controlling statute: MC 14-2017 §3)

The Reports tab on Anna's workstation now reflects the consolidated
case. She generates a fresh intake document with both Maria's
own entries + her own caseworker notes added.

The whole intake takes 45 minutes. Without Duecare, the same intake
+ legal research would have taken 3+ hours.

## Day 91 — Lawyer review

Anna emails the markdown intake document (with Maria's name
redacted to "Worker A") to the standing-counsel lawyer at the
Hong Kong-based legal aid clinic.

**Persona path:** [`docs/scenarios/lawyer-evidence-prep.md`](scenarios/lawyer-evidence-prep.md)

The lawyer, Atty. Yu, has Duecare deployed at her clinic too
(same Mac mini topology). She:

1. Imports the intake markdown
2. Reviews the cited statutes (POEA MC 14-2017 §3, ILO C181 Art. 7,
   ILO C189 Art. 9 + 10) against her own legal references — they're
   correct
3. Edits the drafted refund-claim cover letter with:
   - Her firm's reference number
   - The specific POEA case-type code
   - Details of the ₱62k initial fee + the ~HKD 8k loan deductions
4. Cross-checks the cited NGO contacts (HK Labour Department, MfMW HK,
   PathFinders HK) against her own referral relationships

Total prep time: ~30 minutes (vs ~2 hours without Duecare).

She tells Anna: yes, this is filable. The refund-claim packet
goes to POEA Anti-Illegal Recruitment Branch (case opened
2026-08-05) + a parallel labour-tribunal claim filed at HK Labour
Department for the wage-deduction issue.

## Day 95 — POEA opens the investigation

**Persona path:** [`docs/scenarios/regulator-pattern-analysis.md`](scenarios/regulator-pattern-analysis.md)

POEA Anti-Illegal Recruitment Branch in Manila has Duecare deployed
at unit-level (their procurement reviewed it 6 months earlier per
[`docs/scenarios/it-director.md`](scenarios/it-director.md)).

Their case officer pastes Maria's narrative into POEA's deployment.
The harness fires the same patterns + cites the same statutes.
The case officer triages the case to the priority queue
(critical-severity flags + clearly-documented fees).

The case officer also runs the same recruiter's name (the actual
recruiter, not Maria's composite label, which is now in POEA's
internal case-management system) against POEA's history. Three
prior complaints in the past 6 months for fee-camouflage on the
PH-HK corridor against the same recruiter.

This is the lead enforcement officers had been looking for. The
recruiter's POEA license is suspended pending investigation.

## Day 120 — ILO Bangkok aggregate signal

**Persona path:** [`docs/scenarios/ilo-iom-regional.md`](scenarios/ilo-iom-regional.md)

POEA contributes weekly aggregate counts to a regional federation
(via the [cross-NGO trends federation](cross_ngo_trends_federation.md)
protocol). Maria's case shows up only as +1 in the week-2026-W31
PH-HK passport-withholding bucket — no PII attached.

ILO Bangkok's regional aggregator receives PH-HK + ID-HK + NP-SA
weekly counts from 23 contributing organizations (NGOs +
regulators). Their dashboard shows: passport-withholding hits up
40% across the PH-HK corridor in 6 of the past 8 weeks.

ILO publishes a regional advisory: *"Emerging pattern of
passport-withholding + fee-camouflage in the PH-HK domestic-worker
corridor. Recommended actions: enforcement against named
recruiters, public-information campaign through POLO-HK consulate,
review of bilateral agreement renewal terms."*

The advisory updates the bundled GREP rule pack to add a new
pattern matching the specific recruiter's fee-disclosure language
that POEA's enforcement uncovered. The new rule packs ships as a
signed extension pack to all participating NGOs + the Android
v0.10 release.

## Day 145 — Refund + recruiter shutdown

POEA's investigation completes. The recruiter:
- Loses their PRA license
- Is ordered to refund all worker payments from the past 18
  months (estimated 87 workers, ~₱5.4M total)
- Faces criminal referral for illegal recruitment

Maria's specific refund (₱62k initial + HKD 8k loan deductions)
is processed within 90 days of the order. She gets it ~Day 235
of her original journey.

Without Duecare:
- Maria might not have known the fees were illegal at all
- Even if she did, she'd have spent 30+ hours on legal research
- Without contemporaneous documentation, her case would be
  weaker
- The pattern wouldn't have been visible to POEA until many more
  workers reported

With Duecare:
- ~2 hours of caseworker + lawyer time on her individual case
- Pattern visible to POEA within 4 months of corridor activity
- Rule pack updated for next workers in the same corridor
- ~87 workers benefit from the same enforcement action

## Day 200 — Journalist coverage

**Persona path:** [`docs/scenarios/journalist-investigation.md`](scenarios/journalist-investigation.md)

A Filipino-American journalist covering migrant labor reads ILO
Bangkok's regional advisory. She emails MfMW HK to ask for case
details. MfMW HK refers her to Duecare's
[`docs/press_kit.md`](press_kit.md) for project background.

The journalist:
- Reproduces the +56.5pp lift number from `docs/harness_lift_report.md`
  on her own laptop using the [researcher walkthrough](scenarios/researcher-analysis.md)
- Interviews 3 NGO directors (composite quotes from Anna's
  organization + 2 others); cites their MfMW HK / Polaris / IJM
  affiliations
- Interviews 1 worker (Maria, with her consent and on her own
  terms)
- Cross-references the cited statutes against the official sources

Her published story includes the ILO Bangkok advisory as the
hook + the worker's voice as the human core + the technical
methodology in the sidebar. The story leads to renewed scrutiny
of the PH-HK domestic-worker recruitment pipeline.

## Day 250 — Researcher's published rubric

**Persona path:** [`docs/scenarios/researcher-analysis.md`](scenarios/researcher-analysis.md)

A migration-studies researcher at a Manila university adopts
Duecare for an independent study. She:

- Hand-grades a new 50-prompt rubric specific to the kafala system
  (a different domain — Maria's case is PH-HK, but the kafala
  rubric serves the PH-SA + ID-SA corridors)
- Runs Gemma 4 + Duecare against her rubric (lift: +52pp on
  ILO C189 indicator citations specifically)
- Publishes her paper citing
  `(git_sha=eece564, dataset_version=v3, model_revision=google/gemma-4-e2b-it@main)`

Her paper informs the next round of bilateral agreement review
between the Philippines and Saudi Arabia.

## Day 365 — Enterprise adoption

**Persona path:** [`docs/scenarios/enterprise_pilot.md`](scenarios/enterprise_pilot.md)

A major recruitment platform serving the SE Asia → Middle East
corridor adopts Duecare's classifier as a content-moderation layer
for their job-ad posting flow. Job ads with critical-severity
patterns get auto-flagged for human review before publication.

The recruiter who originally took Maria's money — now operating
under a different shell company — tries to post job ads on the
platform. Each is auto-flagged. The platform's T&S team
investigates and bans the operator.

This is a year after Maria's intake. She doesn't know about it,
but the loop closed.

## What just happened, summarized

In 365 days, the same harness logic powered:
- An individual worker's self-protection on her own phone
- A caseworker's intake at an NGO drop-in centre
- A lawyer's refund-claim drafting
- A regulator's per-recruiter pattern detection
- A supra-national regional advisory
- A journalist's story
- A researcher's published paper
- An enterprise platform's content moderation

Every layer used Gemma 4. Every layer used the same GREP rules
+ RAG corpus + tool registry + ILO indicators. **No single
component was custom-built per layer** — the same code, deployed
in different topologies, served eight different roles.

That's the ecosystem.

## What this case is NOT

Honest framing:

- ❌ "Duecare prevents trafficking." It surfaces the legal
  landscape faster + connects the data flows that make
  enforcement + protection more effective.
- ❌ "Duecare guarantees a refund." It drafts the claim; legal
  + regulatory processes determine outcomes.
- ❌ "All cases follow this exact arc." Most don't — workers
  may not adopt the app; NGOs may not have Duecare deployed;
  regulators may not act. The arc above is the well-tooled best
  case.
- ❌ "This is a real worker named Maria." Maria is a labeled
  composite character throughout the writeup + video, drawn from
  patterns documented in published cases (Polaris 2024 typology,
  Anti-Slavery International 2024 report on Lebanese kafala,
  POEA enforcement records). Composite framing keeps real workers'
  identities protected.

## How to use this in your work

For the **writeup**: lift the Day-90 + Day-120 sections as the
emotional + technical core.

For the **video**: the Day-0 (Maria looks at her phone), Day-90
(the NGO drop-in centre), and Day-120 (the ILO regional
advisory) are the three visual beats that carry the arc. Keep
voiceover under 30 seconds per beat.

For an **NGO pitch deck**: Day-90 + Day-120 + Day-145
demonstrate the operational case for adoption.

For a **journalist brief**: Day-200 + the data flow diagram
in [`docs/ecosystem_overview.md`](ecosystem_overview.md) are
the right materials.

For an **educator's lesson plan**: the full arc as a discussion
case — what would happen if Duecare didn't exist? What would
happen if Duecare existed but no NGO adopted it? What would
happen if every NGO adopted it? See
[`docs/educator_resources.md`](educator_resources.md) for
specific question sets.

## Adjacent reads

- [Ecosystem overview](ecosystem_overview.md) — the architectural view this narrative animates
- [Press kit](press_kit.md) — facts + quotes + suggested story angles
- [Cross-NGO trends federation](cross_ngo_trends_federation.md) — the privacy contract for the Day-120 aggregate signal
- [Scenarios index](scenarios/README.md) — the persona walkthroughs Maria's case touches
