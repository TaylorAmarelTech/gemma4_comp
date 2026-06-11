# Path 4 — Platform CTO pitch outline

A 20-minute pitch deck outline + supporting talking points for the
initial conversation with a platform CTO, VP of Trust & Safety,
Head of Integrity, or Head of Policy. Use the deck or the
talking-points version depending on the audience.

## The one-sentence pitch

> Your primary trafficking-detection classifier misses a specific
> class of recruitment scam that operates in 11 origin-country
> corridors. DueCare is a self-hostable specialist tier that catches
> those cases with statute-cited reasoning your policy team can
> defend.

## Slide 1 — The problem

The 11 origin-country corridors that drive global migrant-labour
trafficking (Philippines, Indonesia, Nepal, Bangladesh, Vietnam,
Cambodia, Myanmar, Sri Lanka, India, Ethiopia, Mexico) each have:

- Their own recruitment law (POEA MC 14-2017, BP2MI Reg 9/2020,
  Nepal FEA 2007, BD OEMA 2013, VN Decree 38/2020, etc.)
- Their own statutory fee caps (most are PHP 0 / IDR 0 / NPR 0 —
  employer-paid only)
- Their own destination-country counterparts (HK Cap 57/57A, UAE
  Decree 33/2021, Saudi RD M/51, Qatar Law 15/2017, KR EPS, TW
  Employment Service Act, etc.)
- Their own substance-over-form scams that evade simple keyword
  classifiers (assignment to collection agency, novated loan,
  "payment plan", "training advance", "deposit returnable on
  contract completion")

A general primary classifier optimised for English-language content
on a global firehose under-performs on these corridors. Not because
the classifier is bad — because the rubric is specialised.

The trafficking patterns themselves are well-documented (ILO,
UNODC, Polaris, IJM, GAATW, ECPAT). What does not exist as a
deployable artifact is the *intersection* of those patterns with a
small enough model to run as platform-tier secondary review.

## Slide 2 — What DueCare brings

A 4B-effective-parameter Gemma 4 fine-tune + a structured knowledge
layer:

| Component | Scale |
|-----------|-------|
| GREP detection rules (deterministic regex) | 300 across 31 categories |
| RAG knowledge documents | 227 (ILO + UN + statutes + case law + research institutes) |
| Complaint + narrative templates | 34 |
| Audience-aware personas | 22 |
| Corridor fee-cap entries | 31 |
| NGO contact bundles | 30 |
| ILO conventions referenced | 15 (C029, C087, C095, C097, C098, C100, C111, C138, C143, C181, C182, C188, C189, C190, P029) |
| Trafficking seed prompts (training set) | 74,640 |

All open source. All verifiable via
`scripts/verify_knowledge_surfaces.py`. Versioned at known commit
SHAs.

## Slide 3 — How it deploys

```
   Your primary classifier
            ↓ (escalations only)
   DueCare specialist tier ← self-hosted on your infrastructure
            ↓
   Your moderation queue + policy team
```

Single internal endpoint. Stateless. Gemma 4 E4B + LoRA weights +
knowledge pack, all loaded on a T4 / L4-class GPU node. No SaaS, no
third-party model API.

Cost: a single GPU node handles ~100K specialist calls/day.

Detail: [`04_platform_specialist_tier.md`](04_platform_specialist_tier.md).

## Slide 4 — Why now

Three things converged in 2025 to 2026:

1. **Gemma 4 small enough to self-host.** Earlier Gemma generations
   were too large for platform-scale specialist tiers. E4B is the
   first version where the math works.
2. **Migrant-labour trafficking pattern documentation reached
   maturity.** UNODC's 2022 + 2024 Global Reports + GRETA's third
   evaluation cycle + UN Special Rapporteur thematic reports + the
   ILO Global Estimates 2022 collectively pinned down the rubric
   in a way that was not formalised five years ago.
3. **Regulatory pressure.** EU CSDDD (Corporate Sustainability Due
   Diligence Directive 2024) + UK MSA Section 54 (2015, expanded
   2024) + US UFLPA (2021) + AU Modern Slavery Act 2018 collectively
   create supply-chain due-diligence obligations that platforms
   increasingly need to demonstrate. Platforms now have a regulatory
   reason to invest in specialist-tier trafficking detection.

## Slide 5 — The ask

A 60-day pilot in one corridor.

- **You provide:** 1 GPU node, 1 part-time integration engineer,
  1 part-time policy reviewer, access to ~1,000 historical
  primary-classifier escalations in the pilot corridor (no live
  enforcement during the pilot).
- **We provide:** specialist tier deployment, knowledge pack
  tuning to your pilot corridor, dashboard for your policy team
  to compare specialist verdicts against historical actions, week-
  ly check-ins.
- **You decide at week 8:** does shadow-mode performance meet your
  threshold for promotion to limited production?

No procurement commitment. No license fee. You can run the pilot
end-to-end before any conversation about steady-state support.

## Slide 6 — Risk

Honest about what could go wrong:

| Risk | Mitigation |
|------|------------|
| Model hallucinates citations | Citation matrix is BUNDLED with verbatim statute text. The model doesn't generate citations; it selects from the bundle. Verifiable by your policy team in 1 click |
| Adversarial bypass | The training set includes 74,640 seed prompts including known adversarial patterns (jailbreak, ASCII-art attack, victim-revictimization framings) |
| Specialist disagrees with your existing policy | Pilot's shadow mode catches this. Specialist is advisory only until your team approves promotion |
| Knowledge layer becomes stale | Quarterly updates, all reversible, versioned. You can pin to any version you have verified |
| Vendor risk if DueCare team disappears | MIT license, open codebase, open knowledge layer, open model. Fork the repo and continue indefinitely |

## Slide 7 — Why DueCare (vs alternatives)

| Alternative | Why it isn't enough |
|-------------|---------------------|
| Use a frontier-API model (GPT-4 / Claude / Gemini Ultra) for the specialist tier | Cost: too expensive at platform escalation volume. Data residency: content has to leave your perimeter. Auditability: you don't see the rubric the model used. |
| Fine-tune your in-house model on trafficking data | You don't have 74,640 corridor-specific seed prompts, 439 GREP rules with verified citations, 859 RAG documents with statute provenance. Building that ground truth is the actual hard part. |
| Just keep tuning the primary classifier | The primary classifier is optimised for the global firehose. Corridor-specific specialised rubrics dilute its precision on the bulk traffic |
| Wait for a regulator to mandate it | If you wait, the regulator chooses the spec and you implement to their standard. Pre-empting is cheaper |

DueCare is the only option that gives you: open source, statute-
cited reasoning, corridor-specific specialisation, small enough for
self-host at escalation scale, ready for pilot in 30 to 60 days.

## Slide 8 — Concrete next steps

1. **This week:** read [`04_platform_specialist_tier.md`](04_platform_specialist_tier.md)
   in detail. Decide which corridor for the pilot.
2. **Next week:** 30-minute scoping call. Walk through the pilot
   plan. Assign an integration engineer.
3. **Weeks 1 to 2 after kickoff:** sandbox stand-up. Integration
   round-trip working.
4. **Weeks 3 to 4:** historical-replay analysis on the pilot
   corridor.
5. **Weeks 5 to 8:** shadow-mode in production.
6. **Week 8 decision gate:** promote to limited production, or
   iterate.

## Talking points (for verbal pitch without slides)

**Opening (30 seconds):** "Your primary trafficking classifier
catches the obvious cases. It misses the ones where a Tagalog job ad
in your marketplace says 'free flight, free visa, PHP 50,000
training fee' and a worker is about to sign up for what is, under
Philippine law, an illegal recruitment scheme. We have a self-
hostable specialist tier built on Gemma 4 that catches those, with
statute-cited reasoning your policy team can defend."

**The hook (60 seconds):** "Three numbers. 300 deterministic
detection rules for the recruitment-fee schemes that ILO C181
forbids and POEA MC 14-2017 codifies. 227 statute + ILO + case-law
documents in the bundled knowledge pack, all verifiable. One GPU
node handles 100,000 specialist calls per day at about $0.005 per
inference. Pilot in 60 days, one corridor, no procurement
commitment."

**The proof (60 seconds):** "It's open source. Gemma 4 E4B with our
LoRA. You'd self-host on your infrastructure, run on your security
perimeter. Every output cites the bundled statute, so your moderator
sees not just 'this looks like trafficking' but 'this violates POEA
MC 14-2017 Sec. 3(a), here's the verbatim text.' If our team
disappears tomorrow, you can keep running this indefinitely and
fork the codebase."

**The ask (30 seconds):** "30-minute scoping call next week. Pick
the corridor. We do the rest. By week 8 your team has a real
decision to make based on shadow-mode performance against your own
historical escalations."

## Common objections + responses

**"We already do this internally."**
> Maybe. But do you have 300 deterministic GREP rules tied to ILO
> convention articles + 859 RAG documents with verbatim statute
> text + 38 corridor fee-cap entries + 36 NGO contact bundles? The
> infrastructure isn't the hard part. The ground truth is. Want to
> compare on a corridor where you suspect your current performance
> is weakest?

**"The legal risk of acting on AI output is too high."**
> The DueCare specialist tier is advisory by design. The verdict
> ships with statute citations + verbatim text. Your moderator
> decides. The model is decision-support, not the decider. This is
> a strictly better baseline than the model decisions you already
> rely on for primary classification.

**"What about regulatory takedowns we'd disagree with?"**
> The specialist tier reports indicators + suggested actions. It
> does NOT enforce. Your platform's existing transparency-reporting
> process handles regulatory takedown requests as it does today.
> The specialist tier is one input among many.

**"What if a worker on our platform is wrongly flagged?"**
> One of the specialist tier's design priorities is anti-over-
> refusal on worker-side queries. A worker asking "is this fair?"
> about their own situation gets a worker-protection persona
> response, NOT a moderation flag against the worker. The rubric
> includes a specific `victim_non_revictimization` dimension.

**"Why not just license a commercial classifier?"**
> Commercial trafficking classifiers exist (Thorn, Hive, etc.). They
> are general — not specialised on migrant labour. They are closed —
> you cannot audit the rubric. They are SaaS — your content leaves
> your perimeter. DueCare's specialist tier is open, specialised,
> and self-hosted. Different shape entirely.

**"This will be in our regulator's testimony in 2 years."**
> Probably. Which is why we offer the open knowledge pack, the
> verifiable citation matrix, and the audit-log architecture. When
> a regulator asks "how did you decide this case", you have a
> documented, statute-cited, reproducible answer.

## What to send before the meeting

1. This pitch outline
2. [`04_platform_specialist_tier.md`](04_platform_specialist_tier.md)
   — the technical integration brief
3. The link to `github.com/TaylorAmarelTech/gemma4_comp`
4. The 30-second demo video (see
   [`04_platform_pilot_demo.md`](04_platform_pilot_demo.md))

## What to ask for after the meeting

Concrete commitments:

- Named corridor for the pilot
- Named integration engineer
- Sandbox GPU node assignment
- ~1,000 historical primary-classifier escalations from the pilot
  corridor (anonymised; pre-existing internal data)
- Date for the next checkpoint (week 2 stand-up review)
