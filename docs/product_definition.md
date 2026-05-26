# Duecare — canonical product definition

> **Duecare is a Gemma 4-powered safety infrastructure platform for
> migrant-worker protection. It combines local and tuned Gemma
> models, deterministic safety harnesses, grounded RAG, evaluation
> rubrics, privacy-preserving knowledge exchange, continuous law /
> contact intelligence, institution-deployed chatbot channels, and
> worker-facing mobile assistance so platform safety teams, NGOs,
> regulators, individual workers, researchers, and integration partners
> can prevent exploitation, assist victims and at-risk workers, and
> understand what is happening and why.**

Shorter:

> **Duecare is a private AI safety platform for migrant-worker
> protection: tuned Gemma 4 models, grounded safety harnesses,
> reproducible evaluation, continuously updated knowledge,
> NGO / government workflows, worker-facing mobile assistance, and
> developer integration paths.**

This is **not** an OFW-specific product. Filipino overseas workers are
one important population (and the demo persona for the Kaggle
notebook), but the actual user category is **migrant workers
globally**.

---

## Canonical three outcomes and six lanes

Lead mission/demo/intro copy with the three outcomes:

1. **Prevent exploitation before it spreads.**
2. **Assist victims and at-risk workers.**
3. **Understand what is happening and why.**

Use this exact lane order everywhere in the repository, website, video,
writeup, and notebooks when summarizing Duecare audiences:

Plain-language component naming and communication flow are maintained
in [`canonical_use_cases_and_components.md`](canonical_use_cases_and_components.md).

1. **Platform safety** — social media companies, job platforms, and
        marketplaces need scalable detection of exploitative recruitment
        content. Surface: moderation API, risk scoring, reviewer dashboard,
        policy audit trace, anonymized pattern signals.
2. **NGO & regulator** — NGOs, government bodies, consulates, and
        labor regulators need case analysis, triage, referral, and grounded
        summaries. Surface: case-analysis console, contact routing, report
        drafts, audit/export, vetted knowledge-pack updates.
3. **Individual worker / mobile** — migrant workers need private help
        understanding suspicious offers, messages, documents, and recruiter
        pressure. Surface: mobile app, private checker, offline support,
        official contacts, localized rights guidance.
4. **Researcher** — academic researchers, evaluators, Kaggle
        judges, and auditors need reproducible safety benchmarks and model
        evaluation. Surface: evaluation harness, rubrics, notebooks, model
        comparison, domain packs.
5. **Anonymized knowledge sharing** — reviewers and partners need to
        convert sanitized, consent-aware facts into reusable knowledge
        objects without moving raw case files into the public hub.
        Surface: local anonymization, submission receipts, curator review,
        and vetted pack updates.
6. **Developer / integration partner** — developers, technical partners,
        and IT teams need APIs, Docker, pack schemas, examples, and client
        snippets. Surface: setup guides, endpoints, package installs,
        integration templates, and validation commands.

Older phrases map to the canonical names as follows:

| Older phrase | Canonical phrase |
|---|---|
| Social platforms, enterprise moderation, job marketplaces | **Platform safety** |
| NGOs, government bodies, consulates, regulators | **NGO & regulator** |
| Mobile/private checker, worker-facing app | **Individual worker / mobile** |
| Researchers, evaluators, Kaggle judges, reproducibility | **Researcher** |
| Knowledge exchange, anonymized sharing, signal exchange | **Anonymized knowledge sharing** |
| Developers, IT teams, custom integrations | **Developer / integration partner** |

OFWs are a demo persona. Migrant workers globally is the category.

---

## Public component names

```text
Duecare Platform
│
├─ Gemma 4 Model Layer                 [Live]
├─ Safety Guidance Layer               [Live]
├─ Knowledge Packs                     [Live]
├─ Quality Testing Framework           [Partial]
├─ Local Anonymization Module          [Prototype]
├─ Information Submission Module       [Prototype]
├─ Central Knowledge Server            [Prototype]
├─ Public Information Research Monitor [Roadmap]
├─ Knowledge Formatter                 [Prototype]
├─ Stakeholder Engagement Module       [Roadmap]
├─ Newsletter and Alert Module         [Roadmap]
├─ Fine-Tuning Module                  [Prototype]
└─ Channel and Deployment Package      [Prototype]
```

Older internal names map to these public names: Runtime means Gemma 4
Model Layer; Harness means Safety Guidance Layer; Eval means Quality
Testing Framework; Exchange means Central Knowledge Server plus
Information Submission; Sentinel means Public Information Research
Monitor; Trainer means Fine-Tuning Module; Channels means Channel and
Deployment Package.

The **live core** for the Kaggle submission is Gemma 4 Model Layer +
Safety Guidance Layer + Knowledge Packs + Quality Testing Framework
(partial). Fine-Tuning is the appendix-notebook prototype. The mobile
app is a sibling-repo proof for Individual worker / mobile. The central server,
research monitor, stakeholder engagement, newsletter, and channel
deployment modules are prototype / roadmap targets — their absence does
not block the live demo.

### 1. Gemma 4 Model Layer

Model layer, not the whole product.

**Responsibilities:** generate plain-language explanations · summarize
case facts · classify risk patterns · interpret screenshots and
documents when multimodal is enabled · support local / private
deployment · provide different model sizes for different surfaces.

**Model tiers:**

| Tier | Best use |
|---|---|
| Gemma 4 E2B | mobile / on-device / low-resource worker checker |
| Gemma 4 E4B | NGO / government dashboard baseline |
| Gemma 4 26B / 31B | research, server-side eval, deeper reasoning |
| Fine-tuned Gemma | domain-specialized migrant-worker safety model |
| Multimodal Gemma | document screenshots, job ads, contracts, chat shots |

**Separation of concern:** Gemma is the language and reasoning engine
inside a deterministic safety system. The harness owns policy, rules,
and evidence. Gemma does not invent laws, contacts, or policy.

### 2. Safety Guidance Layer

The core product. The current Kaggle submission is the first working
implementation of this component.

**Responsibilities:** detect risk · retrieve context · structure
evidence · ground model responses · prevent unsafe or ungrounded
output · produce audit traces · provide deterministic, inspectable
reasoning support around Gemma.

**Submodules:**

| Submodule | Purpose |
|---|---|
| Anonymizer | Strip / generalize PII before storage or sharing |
| GREP / rule engine | Fast deterministic risk-signal detection (100+ rules) |
| RAG database | Laws, regulations, NGO guidance, pattern briefs (50+ docs + citation graph) |
| Tool layer | Fee calculators, jurisdiction lookup, corridor checks, and backing-table rows |
| Contacts directory | Official help channels, NGOs, regulators, consulates |
| Prompt / context builder | Converts signals + RAG into model context |
| Response policy | Bounds model behavior; no unsafe advice |
| Trace / audit layer | Shows why the system flagged something |
| Case summary layer | Produces reviewable intake notes |

For every user group, the harness is the "why should I trust this?"
layer. It turns Gemma from a chatbot into an **auditable
decision-support system**.

### 3. Central Knowledge Server and Information Submission

This is what makes Duecare more than a static app. **Hub scaffolded
at [duecare-ai.com](https://duecare-ai.com)** — code in this repo at
[`apps/duecare-ai.com/`](../apps/duecare-ai.com/), deployed to Render
via the repo-root `render.yaml`. The hub exposes
`POST /api/hub/signals` (anonymized pattern-signal intake with a
raw-PII rejector), `GET /api/hub/knowledge-packs` (knowledge-pack
metadata listing), `GET /api/hub/trends` (aggregate counters), and
`GET /api/hub/status`. The vetted-pack format + partner-discoverable
index are roadmap; the *shape* of the proposal-and-distribution
surface is live so partners can review the contract before
participating.

**Shared object types:**

| Shared object | Example |
|---|---|
| `RagDocumentProposal` | New regulation, labor advisory, court case, NGO report |
| `GrepRuleProposal` | New coded recruitment scam phrase |
| `RubricDimensionProposal` | New scoring criterion (e.g. contract substitution) |
| `ContactUpdateProposal` | Updated regulator hotline / complaint form |
| `AnonymizedCaseSignal` | "3 cases this month mention passport deposit + TikTok recruiter" |
| `EvaluationResult` | Model X failed 17 / 50 domestic-worker fee-manipulation prompts |
| `CorridorPatternUpdate` | New PH → Gulf recruitment pattern |
| `PolicyChangeNotice` | New law / regulation affects scoring |

**Privacy default:** The Central Knowledge Server does **not** collect raw case data.

```text
raw case
  ↓ local anonymizer
redacted signal / aggregate pattern / hashed provenance
  ↓ explicit partner opt-in
Central Knowledge Server
  ↓ human + automated validation
vetted knowledge pack
  ↓ pulled by clients
local harness update
```

**Sharing-protocol invariants:** no raw PII · no raw worker chats by
default · all submissions have provenance · every update has
contributor type + review status · every published pack is versioned
and integrity-checked · clients can pin versions · sensitive cases stay local
unless explicitly consented and anonymized.

> **Local cases create anonymized signals; public / verified sources
> create shared knowledge.** Continuously updating becomes dangerous if
> it becomes centralized surveillance.

### 4. Quality Testing Framework

The research and quality-control layer.

**Responsibilities:** define dimensions · score model responses ·
compare models · validate new rules / RAG docs before release ·
prevent regressions · produce reproducible benchmark artifacts ·
support academic researchers and Kaggle judges.

**Submodules:** Universal rubric · domain-specific
rubrics (trafficking, labor rights, tax evasion, financial crime,
etc.) · evaluation questions (LLM-judge templates) · regression tests
(prevent old failures from returning) · model comparison (Gemma vs
other models, stock vs harnessed) · ablation tests (without RAG,
without GREP, without fine-tune) · benchmark notebooks · governance
checks (validate every new domain-pack release).

**Role in the platform:** Eval gates changes from the continuous
update system. The agent **proposes**; Eval decides whether the
proposal is safe enough to ship.

### 5. Duecare Trainer — model adaptation / retraining pipeline

**Prototype (active A-00 pathway).** The preconfigured pipeline at
`kaggle/A-00-omni-experiment-workbench/` is the active reference
implementation for synthetic rows, LoRA smoke training, checkpoint/resume,
adapter save/load, and report exports; full multi-tenant Trainer service is
post-hackathon.

> A privacy-preserving model-adaptation pipeline that converts
> validated, anonymized case knowledge into task-specific Gemma 4
> adapters for moderation, case analysis, research evaluation, and
> worker assistance.

**Adapter targets:** `duecare-gemma-evaluator` (LLM-judge,
prototype) · `duecare-gemma-worker-advisor` · `duecare-gemma-case-intake` ·
`duecare-gemma-platform-moderation` · `duecare-gemma-multimodal-docs` ·
corridor-specific adapters (`-corridor-ph-hk`, `-corridor-id-sa`,
etc.) · `duecare-gemma-research-assistant` (last six all roadmap).

**Hard rule — PII gate:**

```text
raw data → Anonymizer → curator validation → dataset builder
        → training (Unsloth LoRA) → Eval framework → release
```

No raw PII may enter the training set. Anonymizer's audit log
stores `sha256(original)`, never plaintext.

**Why this matters across user groups:** NGOs adapt models to their
intake workflow; governments adapt to local regulations; platforms
adapt to moderation policy; worker apps use smaller tuned models
offline; researchers reproduce stock-vs-harnessed-vs-tuned behavior
with provenance.

**Composes with the Harness, does not replace it.** A tuned model
gives better baseline behavior; the Harness gives grounded,
auditable, policy-controlled behavior. A judge or auditor inspects
every layer regardless of which model loaded. Full architecture:
[`architecture/duecare_trainer.md`](architecture/duecare_trainer.md).

### 6. Public Information Research Monitor — continuous-update agent + server

**Hub scaffolded; autonomous crawler is roadmap.** The
proposal-intake endpoint lives at
`POST /api/hub/opencrawl/updates` on the public hub
([duecare-ai.com](https://duecare-ai.com), code at
[`apps/duecare-ai.com/`](../apps/duecare-ai.com/)) for public-source
crawler-style proposals. The autonomous crawler that
*fills* that endpoint with continuously-discovered candidates is
post-hackathon. When built, the crawler tracks laws, regulations,
public reports, NGO guidance, platform abuse patterns, and partner
feedback, then proposes vetted updates to Duecare's rules, RAG
corpus, rubrics, contacts, and evaluation sets.

**Agent functions:** law / regulation tracker · NGO / stakeholder
tracker · contact verifier (flags stale phone / email / form URLs) ·
RAG proposer · GREP proposer · rubric proposer · research-pack
builder · release manager (builds vetted versioned packs after
approval).

**Human-in-the-loop is mandatory.** The research monitor never auto-updates
production safety behavior:

```text
crawler / agent finds update
        ↓
proposal object
        ↓
automated validation
        ↓
human curator review
        ↓
Quality Testing Framework regression suite
        ↓
vetted pack release
        ↓
clients pull update
```

**Tiered access:**

| Actor | Submit | Approve | Publish |
|---|---:|---:|---:|
| Individual migrant worker | optional anonymized feedback | no | no |
| NGO partner | yes | maybe (own jurisdiction) | no / global limited |
| Government / regulator | yes | maybe (official contacts/laws) | no / global limited |
| Researcher | yes | benchmark / RAG proposals | no / global limited |
| Maintainer | yes | yes | yes |

### 7. Channel and Deployment Package

**Roadmap.** Design target. Today's bridge: the chat package's
FastAPI surface is the integration surface Channels would wrap with
platform-specific adapters. No code in this repo currently sends
messages on Messenger / WhatsApp / SMS.

> A channel-deployment layer that lets trusted institutions (NGOs,
> labor ministries, consulates, regulators, worker centers, hotline
> operators, legal-aid orgs) provide Gemma 4-powered migrant-worker
> guidance through familiar messaging platforms — grounded in their
> own verified RAG documents, contacts, complaint mechanisms, and
> intake workflows.

**Mobile is worker-owned. Channel deployments are institution-owned.** Both use
the same safety engine (Gemma 4 Model Layer + Safety Guidance Layer + Quality Testing Framework); the trust model
differs. A worker downloading the Mobile app trusts Duecare
directly. A worker chatting with an NGO bot trusts the NGO, which
has wrapped Duecare. Channels ships with explicit
"who-you're-talking-to" disclosure on session start.

**Target channels (in order of partner demand):** web chat widget ·
WhatsApp Business · Facebook Messenger · Telegram · Viber · SMS
(Twilio / Africa's Talking) · government website widget · NGO
intake page (IFRC / IOM / IJM / Polaris / etc.).

**Tenant knowledge pack** per deployment combines global Duecare
knowledge (ILO, Palermo, common indicators) + jurisdiction
knowledge (local laws, complaint procedures) + institution
knowledge (FAQ, intake scripts, escalation rules, human handoff
contacts) + live updates from the research monitor via vetted Exchange packs.

**Complaint-mechanism boundary** is the same as the chat package
and Mobile: explain options, identify likely contacts, prepare a
draft, hand off to humans, **let the user submit**. Auto-submit /
auto-email / auto-call / raw-message-to-server / hallucinated
contact info / pretending-to-give-legal-advice are all banned by
default. Canonical safety phrase used in every channel's
session-start banner:

> **Duecare drafts; the user or trusted caseworker decides. Raw chats
> stay with the worker or tenant unless explicit consent allows a handoff.**

**Submission disclosure.** The Kaggle submission does NOT ship
Channels. Auto-deploying on Messenger / WhatsApp without partner
approval would create the impression that the bot is an official
NGO channel when it isn't. Live deployment requires a named NGO
tenant + business-account approval + Eval-gated tenant pack. Full
architecture: [`architecture/duecare_channels.md`](architecture/duecare_channels.md).

### 8. Duecare Mobile — worker-facing private checker

The worker-facing product. Global migrant-worker focused, **not
OFW-specific**.

A first implementation already exists in the sibling repo
[`duecare-journey-android`](https://github.com/TaylorAmarelTech/duecare-journey-android)
v0.9.0 with MediaPipe LiteRT on-device Gemma 4 E2B, encrypted
SQLCipher journal, ILO indicators, and corridor packs. The roadmap
items below are improvements to that existing app.

**Modules:**

| Module | Purpose |
|---|---|
| Private checker | Paste / screenshot suspicious job offer or message |
| On-device Gemma | Local inference for privacy |
| Offline packs | Laws, contacts, warning signs by country / corridor |
| Multimodal scanner | Read job ads, contracts, screenshots |
| Risk explanation | Plain-language red flags |
| Trusted help | Official contacts and NGOs |
| Draft report | User-reviewed complaint / referral draft |
| Safety mode | "Do not confront recruiter / employer" guidance |
| Localization | Tagalog, Bahasa Indonesia, Nepali, Arabic, Hindi, Bengali, etc. |

**Critical boundaries:**

- Do not auto-report.
- Do not tell workers to confront abusers.
- Do not expose raw messages.
- Do not store sensitive content by default.
- Do not hallucinate contact info.
- Do not pretend to provide legal advice.

The mobile app's framing line:

> **"This is a private risk check and resource guide. You decide
> what to do next."**

---

## How the six canonical lanes map to the eight components

| Component | Platform safety | NGO & regulator | Individual worker / mobile | Researcher | Anonymized knowledge sharing | Developer / integration partner |
|---|---|---|---|---|---|---|
| Runtime | classify / explain posts | summarize cases | private explanations | compare models | sanitize candidate facts | embed model service |
| Harness | moderation risk trace | intake triage | warning signs | inspectable pipeline | reviewable knowledge-object flow | reusable API layer |
| Exchange | share anonymized abuse patterns | submit field signals | receive updated packs | publish domain packs | primary lane | integrate safe submissions |
| Eval | policy QA / model QA | quality control | hidden safety guard | primary tool | PII and provenance gate | regression gate |
| Trainer | moderation adapter | agency-specific adapter | smaller local model | tuned model studies | approved sanitized examples only | BYO adapter path |
| Research monitor | track new scam patterns | update laws / contacts | keeps app current | benchmark updates | candidate source context | public-source proposal API |
| Channels | platform notices | primary deployment | Messenger / WhatsApp help | study artifact | reviewer submission surface | integration target |
| Mobile | not primary | referral companion | primary worker-owned app | deployment study | opt-in aggregate signals | app integration pattern |

Every component serves multiple audiences.

---

## Separation-of-concerns rules

1. **Models do not own truth.** Gemma generates and reasons; it does
   not invent laws, contacts, or policy. Trusted data comes from RAG
   packs, contact packs, rule packs, and reviewed proposals.
2. **The update agent proposes; humans approve.** The research monitor does not
   silently mutate production safety behavior.
3. **Raw cases stay local.** Exchange shares anonymized signals, not
   raw worker narratives.
4. **Contacts are deterministic.** Contacts come from verified data,
   not model output.
5. **Evaluation gates every update.** New rules / docs / rubrics
   run through regression tests before release.
6. **Mobile app consumes vetted packs.** The app pulls versioned,
   offline-compatible safety packs.

---

## High-level diagram

```text
                               Public + partner sources
                 laws, regulations, NGO docs, contacts, case learnings
                                             │
                                             ▼
                         Public Information Research Monitor
                  crawl → propose → validate → human review → release
                                             │
                                             ▼
                              Vetted Duecare Knowledge Packs
               RAG docs | GREP rules | contacts | rubrics | eval prompts
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        ▼                                    ▼                                    ▼
 Fine-Tuning Module           Safety Guidance Layer        Channel and Deployment Package
 LoRA + GGUF + LiteRT         GREP + RAG + tools + tests    Messenger / WhatsApp / web
        │                                    │                                    │
        └────────────────────────────────────┼────────────────────────────────────┘
                                             ▼
                                   Gemma 4 Model Layer
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      ▼                      ▼                      ▼
              Platform safety          NGO & regulator       Individual worker / mobile
                                             │
                                             ▼
                                     Quality Testing Framework
                              reproducibility, regressions, benchmarks
```

---

## What this means for the current Kaggle submission

The Kaggle submission is **the first working implementation of the
Safety Guidance Layer**, running on the **Gemma 4 Model Layer**, with
a partial **Quality Testing Framework** baked in and a **Fine-Tuning
Module** prototype shipped through the DueCare Fine-tuning and Evaluation.

### Real now

- **Gemma 4 Model Layer** — Gemma 4 model selector across local and cloud/BYOK targets, output sanitizer.
- **Safety Guidance Layer** — 100+ GREP rules, 50+ document RAG, function-calling tools, and contact packs.
- **Quality Testing Framework** (partial) — multi-dimension rubric + adversarial suite + multiple grade modes.
- **Contacts directory** — curated entries for regulators, NGOs, embassies, and hotlines.
- **Synthetic multimodal evidence** — bundled CC0 images + structured-post JSONs.
- **Kaggle live proof path** — active kernels: exploration workbench,
  live demo, and A-00 Fine-tuning and Evaluation proof material.

### Prototype / appendix / near-term

- **Fine-Tuning Module** — active `kaggle/A-00-omni-experiment-workbench/` runs synthetic row generation, Unsloth LoRA smoke training, checkpoint/resume, adapter save/load, four-arm comparison, combined judging, and report exports. Adapter targets are scoped; multi-tenant fine-tuning service is post-hackathon.
- **NGO / government RAG packs** — `_contacts.json` curator-block pattern is the bridge. Tenant-specific packs are post-hackathon.
- **Complaint draft workflows** — `/static/hotlines.html` + `/api/contacts` produce `mailto:` drafts. Channel-specific UX (Messenger / WhatsApp) is roadmap.

### Roadmap

- **Central Knowledge Server and Information Submission** — privacy-preserving vetted-pack distribution. Today's bridge: curator-block PRs reviewed by humans.
- **Public Information Research Monitor** — continuous public-source update server. Today's bridge: `scripts/v141_validate_contacts.py` is a read-only HEAD-pinger seed.
- **Channel and Deployment Package** — Messenger / WhatsApp / web / SMS / embassy-portal adapters. Today's bridge: the chat package's FastAPI surface is the integration surface; no live channel deployment.
- **Individual worker / mobile app** v1.0 — Duecare Journey v0.9.0 ships today; v1.0 consumes vetted packs, expands multimodal screenshot scanner, expands corridor coverage.

This is a strong "real now + scalable vision" story: **functional
core today, credible platform vision tomorrow.** The Kaggle submission
ships the live core (Gemma 4 Model Layer + Safety Guidance Layer +
Quality Testing Framework + Contacts) and an appendix prototype
(Fine-Tuning Module); the Central Knowledge Server, Public Information
Research Monitor, and Channel and Deployment Package are
documented design targets that partners can review without confusion
about what's running today vs. what's planned.
