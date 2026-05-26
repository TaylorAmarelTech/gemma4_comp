# Duecare Channels — NGO / Government chatbot integrations

**Status: Roadmap.** Design target. Today's bridge:
`packages/duecare-llm-chat` already exposes the harness through a
FastAPI surface — that's the integration surface Channels would wrap with
platform adapters. No code in this repo currently sends messages on
Messenger / WhatsApp / SMS.

> A channel-deployment layer that lets trusted institutions (NGOs,
> labor ministries, consulates, regulators, worker centers, hotline
> operators, legal-aid orgs) provide Gemma 4-powered migrant-worker
> guidance through familiar messaging platforms — grounded in their
> own verified RAG documents, contacts, complaint mechanisms, and
> intake workflows.

## Why Channels is its own component

The mobile app is **worker-owned**. Channels is **institution-owned**.

| Module | Owner | User | Deployment surface |
|---|---|---|---|
| Mobile (component #8) | Duecare / worker | individual migrant worker | phone (private, on-device) |
| Channels (component #7) | NGO / government tenant | migrant workers + caseworkers | Messenger, WhatsApp, web chat, SMS, embassy portal |

Both use the same safety engine (Runtime + Harness + Eval). The
trust model differs: a worker downloading the Mobile app trusts
Duecare directly. A worker chatting with an NGO bot trusts the NGO,
which has wrapped Duecare. Channels ships with explicit
"who-you're-talking-to" disclosure on session start.

## Target channels (roadmap, in order of partner demand)

| Channel | Notes |
|---|---|
| Web chat widget | Embeddable on NGO + government websites; lowest friction |
| WhatsApp Business | Highest-reach for migrant-worker populations; needs Meta Business approval |
| Facebook Messenger | Used by recruiters too — caseworker triage usable here |
| Telegram | Strong in Eastern European / Russian-speaking corridors |
| Viber | Strong in Philippines + diaspora communities |
| SMS (Twilio / Africa's Talking) | Last-mile reach; works on any feature phone |
| Government website widget | Embassy / consulate / labor-ministry intake portals |
| NGO intake page | IFRC / IOM / IJM / Polaris / etc. existing portals |

## What the chatbot does

| Function | Description |
|---|---|
| Worker Q&A | Answers worker questions in plain language |
| Intake triage | Collects structured complaint facts |
| RAG grounding | Uses NGO / government-specific documents |
| Contact routing | Shows verified agency / NGO contacts |
| Complaint guidance | Explains how to file safely |
| Draft generation | Creates complaint / referral drafts |
| Document review | Reviews screenshots, receipts, contracts |
| Escalation | Hands off to a human caseworker |
| Safety planning | Advises against unsafe confrontation |
| Multilingual support | Tagalog, Bahasa, Nepali, Bengali, Arabic, etc. |

## Tenant knowledge pack (per-deployment)

Each NGO / government deployment has a tenant-specific knowledge pack:

```text
NGO / government chatbot tenant
│
├─ official FAQ
├─ complaint forms
├─ intake scripts
├─ jurisdiction laws
├─ contact directory (subset of _contacts.json)
├─ escalation rules (caseworker handoff thresholds)
├─ supported languages
├─ agency-specific disclaimers
├─ human handoff contacts
└─ reporting thresholds (when to flag for caseworker review)
```

Combined with the **global Duecare knowledge** (ILO conventions,
Palermo Protocol, common indicators) plus the **continuously
updated intelligence** delivered by the Public Information Research
Monitor through vetted Exchange packs.

## Complaint-mechanism boundary

### Allowed

- Explain complaint options
- Identify likely agency / NGO contacts
- Prepare a draft complaint
- Pre-fill a form (only when the form supports URL params)
- Hand off to human staff
- Let user choose whether to submit
- Save a case ID after explicit consent

### Not allowed by default

- Auto-submit complaints
- Auto-email regulators
- Auto-call hotlines
- Expose raw messages to a central server without consent
- Tell workers to confront employer / recruiter
- Hallucinate contact info
- Pretend to provide legal advice

Canonical safety phrase, used in every channel's session-start banner:

> **Duecare drafts; the user or trusted caseworker decides. Raw chats
> stay with the tenant unless explicit consent allows a handoff.**

## Architecture sketch

```text
Worker on Messenger / WhatsApp / web / SMS
        │
        ▼
   Channel Adapter        (per-channel webhook + session manager)
        │
        ▼
   Tenant Router          (loads tenant knowledge pack)
        │
        ▼
   Consent UX             (session-start: who you're talking to + safety)
        │
        ▼
   Duecare Harness        (GREP + RAG + tools — same as the chat package)
        │
        ▼
   Gemma 4 Runtime        (per-tenant model: stock or tuned via Trainer)
        │
        ▼
   Response policy        (grounded refusal, contact routing, draft gen)
        │
        ▼
   Channel Renderer       (markdown → channel-specific formatting)
        │
        ▼
   Worker reply           (or human handoff if escalation threshold met)
```

## What Channels does NOT own

- Model training (that's Trainer / component #5)
- Global laws database (that's RAG via Harness / Exchange)
- Rubrics (that's Eval / component #4)
- Raw source crawling (that's the Research Monitor / component #6)
- Official contact verification (the Research Monitor proposes; humans verify)

Channels' job is **session management + tenant config + channel
adapters + safety UX**. Everything that makes a response correct
lives upstream.

## Submission disclosure

The Kaggle submission does **not** ship Channels. Auto-deploying
Duecare on Messenger / WhatsApp without partner approval would be
unsafe — it would create the impression that the bot is an official
NGO channel when it isn't. Channels exists in this doc tree as a
**design target that partners can review**.

A live Channels deployment requires:

1. A named NGO / government tenant who owns the bot.
2. A tenant knowledge pack (FAQ + complaint forms + contacts + handoff).
3. Platform business-account approval (Meta Business / Twilio / etc.).
4. Eval pass + vetted pack pinning.
5. Disclosed safety boundaries in the session-start banner.

None of those happen at hackathon time.
