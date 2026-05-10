# Mission statement page plan

This document defines the public mission statement page for duecare-ai.com.

Recommended route: `/mission`

Recommended page title: **Mission statement**

## Why this page matters

The website needs one page that explains the human purpose of Duecare before visitors enter the technical details. This page supports the impact story, the video narrative, partner trust, and judge readability.

The mission page should be simple, direct, and serious. It should not read like startup marketing or a grant abstract.

## One-sentence mission

Duecare AI exists to help workers, trusted organizations, platforms, regulators, and researchers recognize exploitation risks earlier, act with better information, and improve shared safety knowledge without centralizing raw private case data.

## Short mission statement

> Duecare AI turns Gemma 4 into privacy-preserving safety infrastructure for migrant-worker protection. It helps people and institutions identify risky recruitment patterns, ground responses in public rules and trusted knowledge, draft safer next steps, and share reviewed improvements through a central hub without exposing raw worker messages or private case files.

## Compact tagline options

Use one primary tagline, not all of them.

1. **Centralized knowledge. Decentralized privacy.**
2. **Better safety guidance without raw case intake.**
3. **Shared intelligence for migrant-worker protection. Private data stays local.**
4. **Gemma 4 safety infrastructure for workers, reviewers, regulators, and researchers.**

Recommended primary tagline:

> Centralized knowledge. Decentralized privacy.

## Three outcomes and five-lane framing

The mission page should lead with the three outcomes:

1. **Prevent exploitation before it spreads** — help organizations and platforms stop illicit recruitment activity through screening and review support.
2. **Assist victims and at-risk workers** — support NGO, government, and worker-controlled workflows with grounded intake, routing, and mobile guidance.
3. **Understand what is happening and why** — help researchers and stakeholders map the who, what, where, when, and why through reproducible evidence.

It should also introduce the five website-facing lanes in this order:

1. **Platform safety** — help platforms screen risky recruitment posts, ads, messages, and recruiter patterns before harm spreads.
2. **NGO & regulator** — help trusted organizations and public agencies triage information, route people to complaint channels, and draft reviewable guidance.
3. **Individual worker / mobile** — help workers privately understand suspicious offers, contracts, fees, threats, and document-retention risks.
4. **Researcher** — help researchers and judges reproduce prompts, evaluations, model behavior, and pack provenance.
5. **Developer / integration partner** — help teams embed Duecare into moderation tools, NGO systems, mobile apps, dashboards, and custom workflows.

This page can explain that the five lanes are the public navigation model, while the Duecare Hub is the shared coordination layer that helps all of them improve.

## Required safety language

Use these exact phrases:

> Privacy is non-negotiable.

> No raw case intake.

> Duecare drafts; the user or trusted caseworker decides.

> Centralized knowledge. Decentralized privacy.

## Page structure

### 1. Hero

Eyebrow:

> Mission

H1:

> Better safety guidance without centralizing private case data.

Lead:

> Duecare AI uses Gemma 4, safety guidance, Knowledge Packs, public-source research, and careful review workflows to help migrant workers and trusted institutions identify exploitation risks earlier while keeping sensitive details local.

Primary CTAs:

- See the five lanes — `/use-cases`
- Explore the hub — `/hub`
- Read technical docs — `/technical-docs`

### 2. The problem

Plain-language copy:

> Risky recruitment does not appear in one place. It appears in job posts, messages, contracts, fee demands, agency promises, document requests, threats, and constantly changing corridor rules. The people closest to the risk often have the least time, least legal support, and strongest privacy needs.

Key bullets:

- recruitment risks move across platforms, agencies, borders, and languages;
- public rules and complaint channels change;
- generic chatbots can be ungrounded or unsafe;
- sensitive worker details cannot be centralized casually;
- NGOs, regulators, platforms, and researchers need shared evidence without shared raw cases.

### 3. The mission

Recommended copy:

> Duecare's mission is to make trustworthy safety guidance easier to run, easier to audit, and safer to improve. The system combines Gemma 4 with deterministic rules, retrieval, tools, public-source updates, anonymization, evaluation, and human review. The goal is not to replace caseworkers, lawyers, regulators, or worker judgment. The goal is to give them better drafts, better context, better tests, and safer ways to share what they learn.

### 4. What Duecare does

Use five cards:

1. **Find risk signals** — flags recruitment fees, document retention, coercion, suspicious promises, and unsafe model behavior.
2. **Ground responses** — uses Knowledge Packs, contacts, rules, citations, and tools before drafting guidance.
3. **Protect privacy** — keeps raw worker content local and uses anonymized objects for shared learning.
4. **Improve shared knowledge** — turns public-source updates and reviewed stakeholder feedback into versioned pack updates.
5. **Prove behavior** — uses reproducible prompts, scorecards, notebooks, and evaluation gates to show what works.

### 5. What Duecare does not do

This section is important for trust.

Use a clear card or table:

| Duecare does not... | Instead... |
|---|---|
| replace caseworkers, lawyers, or regulators | it drafts reviewable guidance and context. |
| operate as an emergency service | it routes to trusted public resources and complaint channels. |
| centralize raw worker chats or case files | it keeps sensitive material local and shares only safe objects. |
| automatically report people or employers | it prepares drafts; humans decide. |
| treat scraped public data as automatic truth | it creates proposals that require review. |
| claim to prevent trafficking by itself | it supports earlier recognition, safer routing, and better shared knowledge. |

### 6. Five lanes

Use the five-lane order:

#### Platform Safety

Platforms can screen recruitment posts, ads, direct messages, and recruiter patterns, then route high-risk content to reviewers and share only anonymized trend signals.

#### NGO & regulator

Trusted organizations can use grounded drafts, complaint-channel context, contact routing, and public-source Knowledge Packs while keeping sensitive case details in their own systems.

#### Individual worker / mobile

Workers can privately check suspicious offers, fees, contracts, threats, and document-retention requests through a local, mobile, web, or trusted chat experience.

#### Researcher

Researchers and judges can reproduce prompts, compare model behavior, inspect scorecards, and verify claims from source artifacts.

#### Developer / integration partner

Developers and technical partners can embed Duecare into moderation tools, NGO systems, mobile apps, dashboards, and custom workflows through APIs, Docker, packs, schemas, and examples.

### 7. Human story section

Use one clearly labeled composite character.

Example:

> Maria is a composite migrant worker. She receives a job offer that promises high pay but asks for a recruitment deposit, a passport handoff, and vague salary deductions. Duecare should not ask Maria to upload her whole life to a public server. Instead, a private chat or trusted caseworker deployment can help identify warning signs, explain public resources, and create a reviewable next-step draft. If the pattern is useful for other workers, only an anonymized signal or public-source update reaches the hub.

Keep the label **composite** visible.

### 8. Partner ecosystem section

Mention real organizations carefully as examples of the kinds of institutions the system is designed to support or route toward, not as claimed partners unless a partnership is real.

Safe wording:

> The ecosystem is designed to complement the work of public-interest and worker-protection institutions such as Polaris, IJM, ECPAT, POEA, BP2MI, HRD Nepal, consulates, labor ministries, and local NGOs. Duecare does not replace these organizations; it helps make guidance, routing, and shared knowledge safer and more reproducible.

### 9. Privacy promise

Recommended copy:

> Privacy is non-negotiable. The hub is for shared knowledge, not raw case intake. Local and trusted deployments may process sensitive messages or documents, but the central server should receive only public-source facts, aggregate counts, anonymized pattern signals, reviewed feedback, vetted pack metadata, and approved examples.

Include the bidirectional privacy gate:

```text
Outbound: local/tenant deployment -> anonymization -> safe object -> hub
Inbound: public/source/submission -> privacy check -> structured object -> review -> publication candidate
```

### 10. Closing statement

Recommended copy:

> Duecare's mission is not to make one chatbot. It is to build reusable safety infrastructure: a way for Gemma 4 deployments to stay grounded, private, testable, and continuously improved across Platform safety, NGO & regulator, Individual worker / mobile, Researcher, and Developer / integration partner lanes.

## Navigation placement

Recommended top nav if space allows:

- Mission
- Demo
- Use cases
- Hub
- Packs
- Docs
- Newsletter
- Live hub

If top nav is crowded, put Mission in the first footer column and link it from the homepage hero.

## Implementation checklist

- Add route `/mission`.
- Add nav or homepage CTA link.
- Add footer link.
- Include the four required privacy phrases.
- Include three outcomes and five-lane framing.
- Include a clearly labeled composite character.
- Include what Duecare does not do.
- Include partner ecosystem wording without claiming partnerships.
- Include links to `/use-cases`, `/hub`, `/technical-docs`, `/privacy-boundary`, and `/demo`.
- Add tests asserting the page contains `Mission`, `Privacy is non-negotiable`, `No raw case intake`, `Developer / integration partner`, and `composite`.

## Tone rules

Use:

- clear;
- serious;
- direct;
- human;
- grounded;
- modest claims.

Avoid:

- savior language;
- overpromising;
- legal-advice claims;
- emergency-service framing;
- claimed partnerships that do not exist;
- jargon before the human problem is clear.
