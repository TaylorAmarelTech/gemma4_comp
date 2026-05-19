# Duecare Hub / public coordination server website plan

This document describes the missing public website section for the hosted Duecare service: the main server that coordinates shared knowledge, tools, packs, public-source research, stakeholder submissions, and partner updates without centralizing raw worker case data.

Use this when implementing the next duecare-ai.com page family.

## Naming

Use these names consistently:

- **Public name:** Duecare Hub
- **Architecture name:** Central Knowledge Server
- **Deployment name:** Duecare Hub / public coordination server

Do not describe the hub as a raw case-management system, emergency reporting portal, or live legal-advice server. It is coordination infrastructure.

Core framing:

> Centralized knowledge. Decentralized data boundaries.

> Duecare drafts; the user or trusted caseworker decides.

> No raw case intake.

## One-sentence description

The Duecare Hub is a CPU-only public coordination server that hosts knowledge-pack metadata, tool definitions, public-source update proposals, anonymized pattern signals, stakeholder feedback workflows, review queues, API docs, and digest/alert infrastructure while keeping raw worker messages, private case files, phone numbers, passports, and addresses out of the central system.

## What the hub does

### 1. Hosts public project and verification pages

The hub is the public proof surface for the platform layer. It explains the product, the privacy boundary, the use cases, the live API shape, and the pack/tool ecosystem.

It should show:

- what Duecare is;
- who it serves;
- which parts are live, prototype, or roadmap;
- what can be verified by judges and partners;
- how local/tenant deployments connect without leaking raw cases.

### 2. Publishes knowledge-pack metadata

The hub should expose a discoverable registry of versioned Knowledge Packs.

Knowledge Packs include:

- RAG documents;
- GREP rules;
- contacts and complaint channels;
- tool definitions;
- corridor fee records;
- jurisdiction rules;
- policy examples;
- evaluation rubrics;
- approved training/evaluation examples.

The hub does not need to store every heavy artifact directly. It can publish versioned metadata that points to GitHub releases, Kaggle datasets, Hugging Face artifacts, object storage, or package versions.

Each pack should display:

- pack ID;
- title;
- kind;
- version;
- status;
- source type: official, partner-reviewed, public-source, or user-generated;
- jurisdictions / corridors;
- source list;
- changelog;
- checksum or signature;
- content-safety evaluation status;
- compatible Duecare package versions;
- pull/download instructions;
- privacy status: contains no raw PII.

User-generated shared Knowledge Packs need extra labeling and review. They must never look like official Duecare guidance unless a maintainer has promoted them through the full review process.

Required labels for user-generated packs:

- **User-generated content**;
- not legal advice;
- not an emergency service;
- review status;
- source/provenance status;
- LLM content-safety evaluation status;
- human curator status;
- date reviewed;
- contact-sharing status.

Optional contributor contact metadata is allowed only with explicit consent. The contributor should be able to choose:

1. no public contact information;
2. private follow-up email visible only to maintainers;
3. public contact email included in the downloadable pack manifest.

Contact emails are PII. They must not be inserted into RAG text, GREP rules, or model prompts. If a contributor chooses public sharing, the email belongs only in pack metadata such as `contributor_public_contact_email`, with a separate `contact_publication_consent=true` field and a clear warning that the email will be distributed with the pack.

### 3. Hosts a tool registry

The hub should explain and eventually serve tool definitions that local or tenant deployments can import.

Tools include:

- fee-cap checker;
- complaint draft builder;
- contact router;
- citation verifier;
- anonymization gate;
- pack diff reviewer;
- public-source update validator;
- stakeholder response ranking form.

Each tool should display:

- what the tool does;
- who uses it;
- required inputs;
- outputs;
- safety boundary;
- example payload;
- related Knowledge Packs;
- whether it is local-only, hub-side, or both.

### 4. Accepts privacy-preserving submissions

The hub should provide structured intake for information that is safe to centralize.

Allowed submission types:

- public-source URL update;
- anonymized pattern observation;
- aggregate trend count;
- contact or hotline update;
- tool suggestion;
- response ranking;
- knowledge-pack correction;
- user-generated Knowledge Pack proposal;
- synthetic demo example;
- registered partner proposal.

Disallowed submission types:

- raw worker chat;
- personal case narrative;
- phone number;
- email address inside submitted content, except optional contributor contact metadata with explicit sharing consent;
- passport, visa, national ID, or case ID;
- home address;
- unredacted document image;
- private accusation about a named person or employer unless already in a public verified source.

All public forms should include an explicit no-raw-case consent checkbox.

### 5. Runs the inbound privacy gate

The hub must treat every inbound text field as untrusted.

Inbound flow:

```text
Submission or crawler proposal
  -> PII / policy check
  -> accepted, rejected, or quarantined
  -> structured information object
  -> curator review
  -> pack proposal, digest item, or training/evaluation candidate
```

The hub should store hashes and sanitized summaries, not prohibited raw PII.

### 6. Evaluates user-generated content before pack inclusion

To reduce content attacks, shared content and user-generated Knowledge Pack proposals must pass an LLM content-safety evaluator before they can be included in any downloadable pack or public registry.

Required gate:

```text
User-generated pack proposal
  -> schema validation
  -> PII / no-raw-case gate
  -> source/provenance check
  -> LLM content-safety evaluator
  -> content-attack and prompt-injection scan
  -> human curator review
  -> Quality Testing Framework regression check
  -> vetted downloadable pack or rejection
```

The LLM evaluator should check for:

- prompt injection or hidden instructions aimed at downstream models;
- attempts to override the Safety Guidance Layer;
- malicious URLs or suspicious executable instructions;
- unverifiable claims presented as facts;
- raw PII or private case details;
- defamatory claims about named people or employers without public-source support;
- harmful procedural guidance;
- legal-advice overclaims;
- manipulative or misleading contact-routing changes;
- poisoned examples intended to degrade model behavior.

No user-generated contribution becomes downloadable by default. Downloadable shared packs need explicit status fields:

- `source_type="user_generated"`;
- `review_status="llm_evaluated" | "curator_approved" | "rejected"`;
- `llm_evaluation_id`;
- `llm_evaluation_summary`;
- `human_curator_id` or public maintainer alias when applicable;
- `contains_raw_pii=false`;
- `contact_publication_consent=true | false`;
- `contributor_public_contact_email` only when explicitly consented.

The website should show these labels beside every user-generated pack and repeat that Duecare is hosting a reviewed contribution, not certifying it as official legal guidance.

### 7. Coordinates outbound anonymized sharing

Local, mobile, NGO, regulator, or platform deployments may send only sanitized information objects to the hub.

Outbound flow:

```text
Sensitive local content
  -> Local Anonymization Module
  -> Information Submission Module
  -> anonymized object / aggregate signal / public-source proposal
  -> Duecare Hub receipt and review state
```

The website should make this visible with a simple diagram.

### 8. Facilitates public-source knowledge acquisition

The hub is where public-source research proposals land.

Sources include:

- labor ministry pages;
- consulate advisories;
- NGO advisories;
- public court or policy documents;
- ILO / UN / government reports;
- platform policy pages;
- public news about recruitment scams or corridor changes.

The Public Information Research Monitor can find sources, but humans approve pack changes.

Research flow:

```text
Public source found
  -> extracted public facts
  -> source hash and URL
  -> Knowledge Formatter proposal
  -> curator review
  -> Quality Testing Framework regression check
  -> vetted Knowledge Pack update
```

### 9. Maintains curator and review queues

The hub should eventually support protected review workflows for trusted maintainers.

Queues include:

- anonymized signal review;
- public-source update review;
- contact freshness review;
- user-generated pack safety review;
- LLM evaluator findings review;
- tool proposal review;
- pack diff review;
- stakeholder ranking review;
- approved-example review for testing or fine-tuning.

Public pages can show aggregate queue counts and sample synthetic records; protected pages should show real review controls.

### 10. Distributes reviewed updates

After approval, the hub publishes updates outward.

Distribution methods:

- pack registry page;
- API endpoints;
- versioned manifests;
- changelog pages;
- newsletter / alert digest;
- webhook notifications;
- package release notes;
- Kaggle / GitHub / Hugging Face links.

### 11. Runs email-only stakeholder engagement

Stakeholder engagement should be email-first and accountless. Do not build a general signup, password, profile, or community-login system for the public hub unless a later partner requirement forces it.

Recommended model:

```text
Visitor subscribes by email
  -> double opt-in / consent confirmation
  -> Duecare sends periodic question emails and reviewed digests
  -> subscriber replies by email or clicks a lightweight form link
  -> inbound email webhook receives the response
  -> PII / no-raw-case gate
  -> LLM extracts structured feedback
  -> human curator reviews
  -> approved information becomes a pack proposal, tool suggestion, contact update, response ranking, alert topic, or evaluation candidate
```

The LLM can draft and process the engagement loop, but it should not be the final approver.

LLM-supported tasks:

- draft newsletter questions from pack gaps, new public-source updates, and evaluation failures;
- adapt questions for Platform safety, NGO & regulator, Individual worker / mobile, Researcher, Developer / integration partner, and hub operators;
- classify inbound replies into allowed information-object types;
- detect likely raw case material or PII and quarantine it;
- summarize safe observations;
- extract public-source URLs, contact corrections, tool suggestions, and response rankings;
- create proposed Knowledge Pack diffs;
- produce curator-ready review cards.

Human-required tasks:

- approve outgoing question campaigns;
- approve or reject proposed pack diffs;
- decide whether a response is safe to store;
- verify contact and legal updates;
- approve any object before it becomes a training or evaluation candidate.

Email engagement should ask for structured, safe feedback, not raw stories. Example prompts:

- "Which of these three draft responses is safest and clearest for your jurisdiction? Rank A, B, C."
- "Is this hotline or complaint channel still current? If not, reply with a public URL."
- "Which warning sign is missing from this corridor pack? Please describe the pattern without names, phone numbers, or private case details."
- "Does this fee-cap explanation match the public rule in your corridor? Send a public source if available."
- "What tool would make this workflow more useful: fee check, contact routing, complaint draft, citation check, or something else?"

Email addresses are operational contact data and must be handled as PII. Prefer storing raw subscriber emails in a dedicated email service provider with double opt-in, unsubscribe links, suppression lists, and access controls. If the Duecare Hub stores subscriber state, store only the minimum required fields, avoid logging addresses, and use hashes or provider IDs in public/debug views.

### 12. Feeds testing and fine-tuning safely

The hub is upstream of model improvement, not an uncontrolled training-data sink.

Only approved, anonymized, provenance-tracked objects should become:

- evaluation prompts;
- regression tests;
- knowledge-pack examples;
- stakeholder response rankings;
- fine-tuning candidates.

The website should explicitly show that Quality Testing gates pack updates and Fine-Tuning outputs before release.

## Pages to implement

### P0 — minimum public hub story

These pages make the Duecare Hub / public coordination server understandable for judges and partners.

| Route | Page | Purpose | Primary content |
|---|---|---|---|
| `/hub` | Duecare Hub overview | Explains the hosted server and why it exists. | Centralized knowledge / decentralized privacy; what the hub does; what it never stores; flow diagram; links to APIs and registries. |
| `/mission` | Mission statement | Explains the human purpose, three outcomes, six lanes, privacy boundary, and what Duecare does not do. | Mission statement, problem framing, six-lane overview, composite character, privacy boundary, partner ecosystem wording. |
| `/knowledge-packs` | Knowledge Pack registry | Shows packs as first-class hosted assets. | Pack cards, versions, status, source types, privacy status, pull instructions, changelog links. |
| `/shared-packs` | User-generated shared packs | Clearly labels community/user-generated packs and shows safety review status before download. | User-generated content labels, LLM evaluation summary, curator status, source/provenance notes, optional public contributor contact metadata. |
| `/tools-registry` | Tool registry | Shows hosted/importable tools. | Tool cards, input/output schemas, local-vs-hub boundary, safety notes, example payloads. |
| `/submit-information` | Share information safely | Explains and implements safe submission categories. | Public-source URL form; anonymized pattern form; contact update form; response ranking form; no-raw-case consent gate. |
| `/research-monitor` | Public Information Research Monitor | Explains knowledge acquisition from public sources. | Source categories, crawler/proposal flow, freshness checks, human review, public-source crawler proposal examples. |
| `/privacy-boundary` | Hub privacy boundary | Makes the trust boundary explicit. | Outbound anonymization, inbound anonymization, disallowed data, hash receipts, review states. |
| `/newsletter` | Email newsletter and questions | Accountless subscription page for stakeholder engagement. | Email-only subscription, consent language, topic choices, question examples, unsubscribe promise, no-raw-case warning. |
| `/technical-docs` | Technical documentation and templates | Documents implementation templates, public-source crawler proposal shape, pack lifecycle, tool schemas, API quick reference, and safe feedback processing. | Template catalog, scraper proposal fields, Knowledge Pack lifecycle, tool schemas, email feedback flow, privacy table, live/prototype/roadmap labels. |

### P1 — partner and maintainer workflows

These pages make the hub feel like real infrastructure, not just a landing page.

| Route | Page | Purpose | Primary content |
|---|---|---|---|
| `/review-queue` | Curator review queue | Protected or synthetic-public view of pending proposals. | Proposed updates, risk flags, source hashes, approve/reject/request changes states. |
| `/pack-diffs` | Pack diff reviewer | Shows how proposed public facts become pack updates. | Before/after diffs, affected jurisdictions, tests to rerun, signature status. |
| `/content-safety-review` | Content safety review | Shows how user-generated content is screened before pack inclusion. | LLM evaluator findings, prompt-injection checks, PII checks, curator decisions, rejection reasons. |
| `/alerts` | Newsletter and alerts | Shows reviewed digest archives and subscription options. | Topic filters, corridor filters, digest previews, alert types, no raw case reminders. |
| `/email-feedback` | Email feedback model | Explains how replies are LLM-processed without accounts. | Email reply workflow, PII gate, LLM extraction, curator review, allowed response types. |
| `/developers` | Developer integration guide | Helps local/tenant deployments connect to the hub. | API quickstart, endpoint list, webhook shape, pack pull examples, SDK/package links. |
| `/governance` | Curation and release policy | Explains who approves what and when. | Roles, review gates, signature policy, training-data eligibility, audit log policy. |

### P2 — deeper product surface

These can wait until the P0/P1 hub story is clear.

| Route | Page | Purpose | Primary content |
|---|---|---|---|
| `/pack-builder` | Knowledge Pack builder | Guided workflow for creating a new pack. | Template selector, source list, validation, preview, submit for review. |
| `/schemas` | Information object schemas | Documents standard objects. | `RegulationUpdate`, `CorridorFeeRecord`, `CasePatternObservation`, `ToolDefinition`, `ResponseRanking`. |
| `/training-candidates` | Approved improvement candidates | Shows safe path from submissions to eval/fine-tuning. | Approved objects, provenance, anonymization status, evaluation gate status. |
| `/status` | Service and registry status | Human-readable health/status page. | API health, storage status, pack freshness, queue counts, last release. |
| `/changelog` | Hub and pack changelog | Central timeline of reviewed changes. | Releases, pack versions, public-source updates, model/eval changes. |

## Recommended top-level navigation

Keep the top navigation conservative. Suggested top nav:

- Demo
- Mission
- Use cases
- Hub
- Packs
- Tools
- Docs
- Newsletter
- Submit
- Developers
- Live hub

Put secondary pages in the footer:

- Privacy
- Technical docs
- Research Monitor
- Alerts
- Governance
- Contact
- API docs

## Homepage hub section

The homepage needs a short section titled **What the Duecare Hub does**.

Recommended copy:

> The Duecare Hub is the shared coordination layer. Local, mobile, NGO, regulator, platform, and research deployments keep sensitive material where it belongs. The hub hosts public knowledge-pack metadata, tool definitions, API docs, anonymized pattern signals, public-source update proposals, review queues, and alert digests. It does not centralize raw cases.

Add four plain cards:

1. **Host packs and tools** — publish versioned metadata and pull instructions.
2. **Label shared contributions** — mark user-generated packs clearly and show review/evaluation status before download.
3. **Collect safe updates** — accept public-source facts and anonymized patterns.
4. **Evaluate content attacks** — run user-generated pack proposals through an LLM safety evaluator, content-attack scan, and curator review.
5. **Review before release** — route submissions through privacy and curator gates.
6. **Ask better questions by email** — send targeted newsletter questions and process replies into safe review objects.
7. **Distribute improvements** — ship vetted pack updates, alerts, tests, and training candidates.

## API and data model expansion

The current hub API shape can grow in phases.

Existing useful endpoints:

- `GET /api/hub/status`
- `GET /api/hub/knowledge-packs`
- `GET /api/hub/trends`
- `POST /api/hub/signals`
- `POST /api/hub/opencrawl/updates`
- `GET /api/hub/opencrawl/updates`

Suggested new endpoints:

- `GET /api/hub/tools`
- `GET /api/hub/packs/{pack_id}`
- `GET /api/hub/packs/{pack_id}/changelog`
- `GET /api/hub/shared-packs`
- `POST /api/hub/shared-packs/proposals`
- `POST /api/hub/shared-packs/{proposal_id}/llm-evaluation`
- `POST /api/hub/contact-updates`
- `POST /api/hub/response-rankings`
- `POST /api/hub/tool-suggestions`
- `POST /api/hub/newsletter/subscribe`
- `POST /api/hub/newsletter/inbound-reply`
- `GET /api/hub/newsletter/issues`
- `GET /api/hub/review-queue`
- `POST /api/hub/review-queue/{proposal_id}/decision`
- `GET /api/hub/schemas`
- `GET /api/hub/alerts/latest`

## What should be centralized vs local

| Data / function | Central hub? | Local / tenant deployment? | Notes |
|---|---:|---:|---|
| Public law/advisory URL | Yes | Yes | Safe if source is public. |
| Pack metadata | Yes | Yes | Publish checksums/signatures. |
| Pack content | Maybe | Yes | Can be linked from GitHub/Kaggle/HF/object storage. |
| User-generated pack proposal | Yes, after privacy gate | Yes | Must be labeled user-generated and pass LLM content-safety evaluation before download. |
| Optional contributor public contact email | Yes, only with explicit consent | Optional | PII; store only as metadata, never inside RAG/tool/prompt text. |
| Tool definitions | Yes | Yes | Tool execution can remain local. |
| Raw worker chat | No | Yes | No raw case intake. |
| Passport / phone / address | No | Yes, only if trusted and necessary | Never centralize. |
| Anonymized pattern | Yes | Yes | Must pass privacy gate. |
| Aggregate counts | Yes | Yes | Useful for trends without raw records. |
| Response rankings | Yes, if anonymized | Yes | Useful for testing/fine-tuning. |
| Subscriber email address | Prefer ESP only | No | Operational PII; use double opt-in, unsubscribe, access controls, and avoid logs. |
| Newsletter reply text | Only after privacy gate | Yes | LLM extracts safe objects; raw replies with PII are rejected or quarantined. |
| Fine-tuning examples | Only if approved/anonymized | Yes | Require provenance and evaluation gates. |
| Curator decisions | Yes | Optional | Needed for audit/release trace. |

## Video demo framing

The hub should appear in the video as the shared intelligence layer:

1. A local or tenant deployment detects a risky pattern.
2. Raw content stays local.
3. The Local Anonymization Module creates a safe object.
4. The Information Submission Module sends it to the Duecare Hub.
5. The hub shows a receipt, review state, and aggregate trend.
6. The hub sends an email question to subscribed stakeholders about a safe, structured issue.
7. An LLM turns replies into reviewable contact updates, response rankings, or tool suggestions.
8. A user-generated shared pack proposal is labeled as user-generated and routed through the LLM content-safety evaluator.
9. A public-source update is proposed through the Research Monitor.
10. A curator approves a pack diff.
11. A vetted Knowledge Pack update becomes available to every deployment.

This makes the hub visible without pretending it is a full case-management system.

## Implementation rule

Do not build hub pages as a flashy dashboard. Build them as conservative public documentation plus simple live proofs: registry tables, safe forms, status cards, review-state examples, and OpenAPI links.
