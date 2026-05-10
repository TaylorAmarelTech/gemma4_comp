# Technical documentation website page plan

This document defines the missing public technical documentation page family for duecare-ai.com.

The existing FastAPI OpenAPI route already uses `/docs`, so the public website should use `/technical-docs` or `/implementation` for human-readable technical documentation.

Recommended route: `/technical-docs`

Recommended page title: **Technical documentation and implementation templates**

## Why this page is needed

The public website currently explains the story, use cases, tools, context, and hub direction, but it does not yet give builders a clear technical map for:

- information-object templates;
- Knowledge Pack structure;
- user-generated Knowledge Pack labeling and safety review;
- GREP rule format;
- RAG document format;
- public-source crawler proposal intake;
- LLM content-safety evaluation for shared content;
- public-source update proposals;
- anonymized signal payloads;
- tool schemas;
- newsletter/email feedback processing;
- curator review states;
- testing and fine-tuning eligibility.

This page should make the project look real and implementable without exposing private benchmark data or raw PII.

## Page role

The page should be a conservative technical index, not a flashy dashboard.

It should answer:

1. What are the standard Duecare data templates?
2. How does a public-source scraper submit an update?
3. How does an NGO or platform send an anonymized signal?
4. How are tool definitions represented?
5. How do Knowledge Packs get built, signed, tested, and pulled?
6. How are user-generated shared packs labeled and safety-reviewed before download?
7. How do newsletter/email replies become structured feedback?
8. Which endpoints and schemas exist today?
9. Which parts are live, prototype, or roadmap?

## Audience

Primary audience:

- developers implementing a local/tenant Duecare deployment;
- NGOs or regulators evaluating the technical safety boundary;
- platform safety teams integrating with moderation or trust-and-safety queues;
- academic researchers verifying reproducibility;
- Kaggle judges checking that the platform is real, not just a mockup;
- future contributors adding packs, tools, schemas, or scrapers.

## Recommended page structure

### 1. Header

H1:

> Technical documentation and implementation templates.

Lead copy:

> Duecare uses simple, reviewable templates for knowledge packs, tools, public-source updates, anonymized signals, email feedback, and evaluation artifacts. The hub coordinates metadata and safe submissions; raw worker cases stay local.

Primary CTAs:

- Open API docs — `/docs`
- View Knowledge Packs — `/knowledge-packs`
- Submit safe update — `/submit-information`

### 2. Technical architecture map

Show a simple non-overlapping flow:

```text
Local / tenant deployment
  -> Local Anonymization Module
  -> Information Submission Module
  -> Duecare Hub
  -> Curator Review
  -> Knowledge Formatter
  -> Quality Testing Framework
  -> Vetted Knowledge Pack
  -> Local / tenant deployments pull updates
```

Add a second public-source flow:

```text
Public-source crawler
  -> Public-source update proposal
  -> PII / policy check
  -> Knowledge Formatter
  -> Curator Review
  -> Pack diff
  -> Regression tests
  -> Vetted pack release
```

### 3. Template catalog

Create cards or a table for each standard template.

| Template | Purpose | Source | Storage status |
|---|---|---|---|
| `KnowledgePackManifest` | Pack identity, version, sources, checksums, compatible packages. | Curator / release process | Hub metadata yes; full artifacts maybe external. |
| `RagDocument` | Public legal, NGO, policy, contact, or corridor context. | Public source or reviewed partner update | Yes if public and no raw PII. |
| `GrepRule` | Deterministic indicator rule with severity and explanation. | Pack maintainer | Yes. |
| `ToolDefinition` | Tool name, inputs, outputs, display copy, safety limits. | Maintainer / partner | Yes. |
| `CorridorFeeRecord` | Fee cap, prohibited fees, source, jurisdiction, effective date. | Public source | Yes. |
| `RegulationUpdate` | Law/policy/advisory update from a public source. | Scraper or partner URL | Yes after review. |
| `ContactUpdate` | Hotline, NGO, regulator, consulate, or complaint-channel update. | Public source / partner | Yes after verification. |
| `CasePatternObservation` | Anonymized pattern signal without names or contact details. | Local/tenant deployment | Yes only after privacy gate. |
| `ResponseRanking` | Stakeholder ranking of candidate model/tool responses. | Email feedback / form | Yes if anonymized. |
| `UserGeneratedPackProposal` | Community/shared Knowledge Pack contribution with source type, safety status, and optional contact metadata. | Contributor / partner / stakeholder | Yes after privacy gate; downloadable only after LLM evaluation and curator approval. |
| `ContentSafetyEvaluation` | LLM evaluator result for prompt injection, content attacks, PII, harmful claims, and source risk. | LLM evaluator + reviewer | Yes as review metadata. |
| `TrainingCandidate` | Approved anonymized example eligible for eval/fine-tuning review. | Curated object | Yes only after approval and provenance gate. |

### 4. Public-source crawler proposal section

This section should be prominent because it explains knowledge acquisition.

Explain:

- scraper only targets public sources;
- no private chats, private social accounts, or raw case files;
- crawler extracts public facts, source URL, timestamp, jurisdiction, pack kind, and content hash;
- crawler submits a proposal, not a direct pack change;
- a curator must approve;
- regression tests run before publishing.

Recommended subsection title:

> Public-source scraping: proposals, not automatic truth.

Show fields:

| Field | Meaning |
|---|---|
| `source_name` | Human-readable source name. |
| `source_url` | Public URL. |
| `observed_at` | Time the source was observed. |
| `proposed_pack_kind` | Target pack category. |
| `jurisdiction` | Country/region/corridor. |
| `change_summary` | Safe public-source summary. |
| `extracted_public_facts` | Structured public facts. |
| `content_hash` | Hash of fetched source content. |
| `crawler_version` | Scraper/proposal generator version. |

### 5. Hub API quick reference

Link to `/docs` for complete OpenAPI, but show the human-readable map.

Existing endpoints:

- `GET /api/health`
- `GET /api/hub/status`
- `GET /api/hub/knowledge-packs`
- `GET /api/hub/trends`
- `POST /api/hub/signals`
- `POST /api/hub/opencrawl/updates`
- `GET /api/hub/opencrawl/updates`

Planned endpoints:

- `GET /api/hub/tools`
- `GET /api/hub/packs/{pack_id}`
- `GET /api/hub/packs/{pack_id}/changelog`
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

### 6. Knowledge Pack lifecycle

Show a practical lifecycle:

```text
Draft object
  -> schema validation
  -> privacy check
  -> source/provenance check
  -> LLM content-safety evaluation for user-generated/shared content
  -> curator review
  -> pack diff
  -> Quality Testing Framework regression run
  -> signed manifest
  -> publication through hub registry
  -> local/tenant clients pull update
```

Display lifecycle states:

- `draft`
- `submitted`
- `privacy_checked`
- `llm_evaluation_pending`
- `llm_evaluated`
- `content_attack_flagged`
- `needs_review`
- `approved`
- `rejected`
- `pack_diff_created`
- `tests_running`
- `tests_passed`
- `signed`
- `published`

### 7. User-generated shared pack safety section

The technical docs page should make clear that shared/community packs are useful but risky. They are user-generated content and can be a content-attack vector if included directly in RAG, tools, prompts, or evaluation examples.

Recommended subsection title:

> User-generated packs: labeled, evaluated, then reviewed.

Required policy:

- User-generated packs must be labeled as **User-generated content** in the registry and in downloadable manifests.
- User-generated packs must pass an LLM content-safety evaluator before inclusion in a downloadable pack.
- The evaluator is a gate, not the final authority; human curator review is still required.
- User-generated content must not be promoted to official Duecare guidance without provenance checks, curator approval, and Quality Testing regression checks.
- Optional contributor contact email can be shared only with explicit consent and only in pack metadata.

Recommended flow:

```text
User-generated pack proposal
  -> schema validation
  -> PII / no-raw-case gate
  -> source/provenance check
  -> LLM content-safety evaluator
  -> prompt-injection / content-attack scan
  -> human curator review
  -> Quality Testing Framework regression run
  -> vetted downloadable pack or rejection
```

The LLM content-safety evaluator should check for:

- prompt injection hidden in documents, examples, comments, or metadata;
- instructions that try to override system prompts, GREP rules, or Safety Guidance Layer behavior;
- malicious URLs or executable instructions;
- raw PII, private case details, or unconsented contact data;
- unverifiable facts presented as authoritative;
- defamatory claims about named people or employers without public-source support;
- harmful procedural guidance;
- legal-advice overclaims;
- unsafe contact-routing changes;
- poisoned examples that could degrade model behavior.

User-generated pack manifests should include:

| Field | Meaning |
|---|---|
| `source_type` | Must be `user_generated` for shared/community contributions. |
| `review_status` | `submitted`, `llm_evaluated`, `content_attack_flagged`, `curator_approved`, or `rejected`. |
| `llm_evaluation_id` | Stable ID for the evaluator result. |
| `llm_evaluation_summary` | Short safety summary suitable for display. |
| `contains_raw_pii` | Must be `false` before download. |
| `contact_publication_consent` | Whether contributor consented to public contact metadata. |
| `contributor_public_contact_email` | Optional; only present when explicit consent is true. |
| `contributor_private_followup_id` | Optional provider/user ID for maintainer follow-up without public email display. |

Contact email policy:

- contributor contact email is optional;
- default is no public contact information;
- private follow-up email may be visible only to maintainers;
- public contact email may be included in the downloadable manifest only after explicit consent;
- contact email must never be embedded inside RAG text, GREP rules, tool instructions, or model prompts;
- public pages should distinguish contact metadata from knowledge content.

### 8. Tool schema section

Show how tools are represented.

A tool page should document:

- tool name;
- audience;
- risk boundary;
- input fields;
- output fields;
- local-only vs hub-side execution;
- Knowledge Packs used;
- citations required;
- whether output is draft-only;
- test cases.

Example tools:

- fee-cap checker;
- contact router;
- complaint draft builder;
- citation verifier;
- anonymization gate;
- pack diff reviewer.

### 9. Email feedback processing section

This section should explain the accountless engagement model.

Flow:

```text
Subscriber receives a question email
  -> subscriber replies or clicks a lightweight form link
  -> inbound email webhook receives response
  -> PII / no-raw-case gate
  -> LLM extracts structured object
  -> curator reviews
  -> approved object becomes contact update, response ranking, tool suggestion, pack proposal, or evaluation candidate
```

Make clear:

- no public account required;
- email addresses are PII and should be handled by the email service provider where possible;
- raw replies containing private case details are rejected or quarantined;
- the LLM structures replies but does not approve them;
- human review is required before publication or training use.

### 10. Privacy and safety contracts

Add a table:

| Item | Hub can store? | Notes |
|---|---:|---|
| Public URL | Yes | Must be public and sourceable. |
| Public-source facts | Yes | After validation and review. |
| Pack metadata | Yes | Include checksums/signatures. |
| User-generated pack proposal | Yes after privacy gate | Must be labeled user-generated and pass LLM safety evaluation before download. |
| LLM content-safety evaluation | Yes | Store as review metadata; not a substitute for curator approval. |
| Tool definitions | Yes | Safe if no raw case data. |
| Anonymized pattern | Yes | Must pass privacy gate. |
| Aggregate trend count | Yes | No raw records. |
| Response ranking | Yes | If prompt/response contains no raw PII. |
| Subscriber email | Prefer ESP only | Treat as operational PII. |
| Contributor public contact email | Yes only with explicit consent | Store as metadata only; never inside knowledge text or prompts. |
| Raw worker chat | No | Keep local. |
| Passport/phone/address | No | Reject or quarantine. |
| Unredacted document image | No | Local processing only unless fully redacted and consented. |

### 11. Live/prototype/roadmap status

The page should be honest.

Recommended labels:

- **Live** — implemented and test-covered in the repo or deployed hub.
- **Prototype** — implemented enough to demonstrate the workflow but not production hardening.
- **Roadmap** — planned and documented but not yet implemented.

Avoid presenting roadmap items as fully live.

## Related website pages

The technical docs page should link to:

- `/hub`
- `/knowledge-packs`
- `/shared-packs`
- `/tools-registry`
- `/submit-information`
- `/research-monitor`
- `/privacy-boundary`
- `/newsletter`
- `/developers`
- `/governance`
- `/docs`

## Top navigation impact

If navigation space is limited, use this label:

- `Docs`

But link it to `/technical-docs`, not `/docs`, because `/docs` is already OpenAPI.

Footer should include:

- Technical docs — `/technical-docs`
- API docs — `/docs`
- Schemas — `/schemas`
- Governance — `/governance`

## Implementation recommendation

Implement `/technical-docs` before deeper protected dashboards. This page gives the project immediate technical credibility and supports the video/writeup claim that the hub can host packs, tools, templates, public-source acquisition, and safe stakeholder feedback.

Minimum implementation checklist:

- route `/technical-docs`;
- nav/footer link;
- page header;
- template catalog;
- public-source crawler proposal section;
- API quick reference;
- Knowledge Pack lifecycle;
- user-generated pack safety gate;
- email feedback processing;
- privacy table;
- live/prototype/roadmap labels;
- tests asserting the page contains `public-source crawler`, `KnowledgePackManifest`, `ToolDefinition`, `ResponseRanking`, `User-generated content`, `LLM content-safety evaluator`, and `No raw case intake`.
