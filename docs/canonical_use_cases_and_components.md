# Canonical outcomes, lanes, and plain-language component architecture

> Status: human-readable companion to the machine-readable public messaging
> contract at [`configs/duecare/canonical_messaging.yaml`](../configs/duecare/canonical_messaging.yaml).
> Rule: change the config first when outcomes, lanes, component names,
> counts, or sensitive-data wording change; then update rendered docs and run
> `scripts/validate_public_messaging.py`.

## 1. Three outcomes

1. **Prevent exploitation before it spreads** — help organizations and platforms stop illicit recruitment activity through screening and review support.
2. **Assist victims and at-risk workers** — support NGO, government, and worker-controlled workflows with grounded intake, routing, and mobile guidance.
3. **Understand what is happening and why** — help researchers and stakeholders map the who, what, where, when, and why through reproducible evidence.

## 2. Exact users / lanes

### 1. Platform safety

**Who:** Trust and safety teams at social media companies, job platforms, marketplaces, recruitment boards, and other services where risky recruitment content appears.

**What they need:** Detect exploitative recruitment posts, ads, direct messages, recruiter profiles, and scam patterns before workers are harmed.

**What Duecare does for them:** Scores content for risk, explains why a post was flagged, shows which rules and sources were used, routes high-risk items to reviewers, and shares only anonymized pattern signals with the central hub.

**Public-facing wording:** "Platform safety teams use Duecare to screen risky recruitment content, support reviewers, and share anonymized abuse patterns without exposing private messages."

### 2. NGO & regulator

**Who:** NGOs, caseworkers, legal-aid groups, consulates, labor ministries, labor inspectors, regulators, and authorized enforcement partners.

**What they need:** Triage messages and documents, explain rights and options, find trusted contacts, draft complaint materials, and update corridor-specific knowledge.

**What Duecare does for them:** Provides grounded drafts, contact routing, complaint-channel context, jurisdiction and corridor facts, case summaries, and knowledge-pack update tools. Duecare drafts; a trusted human decides.

**Public-facing wording:** "NGO & regulator users use Duecare to turn complex messages, documents, and public rules into reviewable guidance, referrals, and draft complaint materials."

### 3. Individual worker / mobile

**Who:** Migrant workers and prospective migrant workers using a trusted chat, mobile, web, or local tool. OFWs are one demo persona, not the only audience.

**What they need:** Private, plain-language help understanding suspicious job offers, contracts, recruiter messages, fee demands, document retention, threats, and next steps.

**What Duecare does for them:** Runs a private or trusted mobile/chat experience that checks risks, explains warning signs, cites relevant contacts or rights information, and avoids sending raw messages to the public hub.

**Public-facing wording:** "Individual worker / mobile users use Duecare to understand suspicious messages or documents privately, with localized warning signs and trusted next-step resources."

### 4. Researcher

**Who:** Academic researchers, public-interest researchers, evaluators, auditors, Kaggle judges, and model-safety teams studying reproducible behavior.

**What they need:** Reproducible prompts, text and image examples, evaluation rules, model comparisons, ablations, and provenance.

**What Duecare does for them:** Provides benchmark prompts, response rubrics, rule-based and LLM-based evaluation, notebook outputs, model cards, and versioned knowledge packs.

**Public-facing wording:** "Researchers use Duecare to reproduce model behavior, compare safety interventions, and audit every claim from source artifacts."

### 5. Developer / integration partner

**Who:** Developers, technical partners, IT teams, and integration owners embedding Duecare into moderation tools, NGO systems, mobile clients, dashboards, or custom workflows.

**What they need:** APIs, Docker/runtime paths, pack schemas, client snippets, version pinning, integration examples, and local validation commands.

**What Duecare does for them:** Provides the runtime, APIs, knowledge-pack registry, submission endpoints, setup guides, and reusable components needed to embed Duecare inside their own channels.

**Public-facing wording:** "Developer / integration partners use Duecare to embed the harness, packs, APIs, and examples into their own prevention, assistance, or research workflows."

## 3. Language rules

Use these names exactly:

1. Platform safety
2. NGO & regulator
3. Individual worker / mobile
4. Researcher
5. Developer / integration partner

Avoid using these as top-level user labels:

- "social platforms" as a standalone label; use **Platform safety**.
- "enterprise" as a top-level audience; say **Platform safety deployment** if the customer is a platform.
- "worker-side" as a top-level lane; use **Individual worker / mobile**.
- "researchers" alone in summary lists; use **Researcher**.
- "NGO dashboard" alone when regulators are included; use **NGO & regulator**.
- "custom integration" alone as a lane; use **Developer / integration partner**.

Technical nicknames such as Runtime, Harness, Eval, and Exchange can remain internal package names, but public pages should use plain-language component names.

## 4. Technical components, grouped by what they do

### Group A — Private decision-support experience

These components run in a local, tenant-owned, or trusted deployment. They are what users experience when they ask Duecare to review a post, message, document, or case bundle.

| Plain-language component | Technical nickname | What it does | What it displays | Communicates with |
|---|---|---|---|---|
| Gemma 4 Model Layer | Runtime | Loads and calls Gemma 4 models for classification, explanation, summarization, multimodal reading, and draft generation. | Model choice, response text, latency/status, model card links. | Safety Guidance Layer; Quality Testing Framework; Fine-Tuning Module. |
| Safety Guidance Layer | Gemma 4 Harness | Wraps Gemma 4 with persona settings, GREP rules, RAG, tools, online search, and imports so answers are grounded and traceable. | Fired rules, retrieved sources, tool results, imported evidence, prompt trace, final draft. | Gemma 4 Model Layer; Knowledge Packs; Quality Testing Framework; Deployment Package. |
| Channel and Deployment Package | Self-contained deployment module | Packages the model, safety layer, knowledge packs, configuration UI, API endpoint, and webhook-ready service for platform, NGO, regulator, or chat deployments. | Setup wizard, tenant settings, endpoint URL, webhook/API instructions, health checks, audit trace. | Platform systems; NGO chat channels; Safety Guidance Layer; Information Submission Module. |

Safety Guidance Layer subcomponents:

| Subcomponent | What it does | What it displays |
|---|---|---|
| Persona | Sets the response stance for the audience, such as platform reviewer, NGO caseworker, worker chat, or researcher. | Active persona and response policy. |
| GREP rules | Fast deterministic checks for risk language and known patterns. | Rule names, matches, severity, explanation. |
| RAG | Retrieves laws, contacts, corridor context, policies, and guidance. | Retrieved documents, snippets, citations, confidence. |
| Tools | Runs structured lookups such as corridor fees, contact routing, fee-cap checks, and complaint draft builders. | Tool name, inputs, outputs, citations. |
| Online search | Optional live public-source lookup for current public facts. | Search query, fetched source, extracted public facts. |
| Import | Accepts files, screenshots, text snippets, or structured evidence. | Imported item type, parsed text, extracted fields, safety warnings. |

### Group B — Knowledge and data formats

These components define what Duecare knows and how that knowledge travels between local deployments and the central server.

| Plain-language component | Technical nickname | What it does | What it displays | Communicates with |
|---|---|---|---|---|
| Knowledge Packs | Pack registry | Versioned bundles of GREP data, RAG documents, contacts, defined tools, corridor fees, regulations, examples, and policies. | Pack name, version, jurisdiction, source list, change log, download/pull instructions. | Safety Guidance Layer; Quality Testing Framework; Central Knowledge Server. |
| Knowledge Format Templates | Schemas | Defines the standard shapes for RAG entries, GREP rules, tools, contacts, fee tables, law updates, case observations, and response rankings. | Template documentation, required fields, examples, validation errors. | Knowledge Formatter; Anonymization Module; Stakeholder Response Formatter. |
| Information Objects | Filled templates | Actual structured facts, observations, fee records, regulation updates, public-source findings, or stakeholder response rankings. | Object type, sanitized summary, source/provenance, review status. | Anonymization Module; Information Submission Module; Central Knowledge Server. |
| Knowledge Formatter | Standardizer | Converts scraped public content or submitted observations into validated knowledge objects and pack updates. | Side-by-side raw public text, extracted fields, confidence, proposed pack diff. | Research Monitor; Stakeholder Response Formatter; Central Knowledge Server. |

Examples of information objects:

- `CorridorFeeRecord`: allowed fees, prohibited fees, jurisdiction, source, effective date.
- `RegulationUpdate`: law or policy change, source URL, affected corridor, review status.
- `CasePatternObservation`: anonymized pattern such as "passport handoff + recruitment deposit".
- `ToolDefinition`: tool name, inputs, outputs, safety boundary, display text.
- `ResponseRanking`: prompt, candidate responses, stakeholder ranking from worst to best.

### Group C — Sensitive data handling and submission

Do not explain this area with a shorthand label. Use full sentences:

- Raw worker chats, case files, IDs, contact details, and private documents stay on the worker device or trusted NGO hardware unless an authorized user explicitly creates a sanitized submission.
- Sensitive PII is anonymized by the local Gemma 4 workflow before anything is submitted to the public hub.
- The server runs a second PII detector that rejects raw-PII submissions before storage and redacts detector-class PII in admin/debug views.
- The public hub stores public-source facts, vetted pack metadata, anonymized aggregate signals, hash receipts, and consented contact metadata — not raw case narratives, phone numbers, passports, addresses, or private documents.

| Plain-language component | Technical nickname | What it does | What it displays | Communicates with |
|---|---|---|---|---|
| Local Anonymization Module | Anonymizer | Runs locally or inside a trusted tenant. It asks Gemma 4 and deterministic detectors to convert sensitive content into structured, anonymized information objects. | Redaction summary, blocked PII categories, sanitized object preview, local hash receipt. | Safety Guidance Layer; Information Objects; Information Submission Module. |
| Information Submission Module | Submitter | Sends only anonymized objects, public-source updates, aggregate counts, or vetted pack proposals to the central server. | Consent checkbox, submission payload preview, receipt ID, review status. | Local Anonymization Module; Central Knowledge Server. |

Hard rule:

> The public server receives anonymized signals, public-source facts, vetted pack metadata, hash receipts, and consented contact metadata — not raw worker chats, phone numbers, addresses, passports, private documents, or personal case narratives.

### Group D — Central server, public website, and shared intelligence

These components run on the hosted duecare-ai.com service or an institution-owned server.

| Plain-language component | Technical nickname | What it does | What it displays | Communicates with |
|---|---|---|---|---|
| Central Knowledge Server | duecare-ai.com hub | Receives anonymized submissions, stores review queues, publishes pack metadata, and serves website/API pages. | Public homepage, use-case pages, API docs, pack registry, anonymized trend summaries, review queue. | Information Submission Module; Knowledge Packs; Newsletter Module; Stakeholder Engagement Module. |
| Public Information Research Monitor | Public-source crawler | Searches public sources for new laws, advisories, trends, negative news, platform policies, and other relevant public facts. | Source list, crawler status, extracted public facts, proposed updates, freshness warnings. | Online search tools; Knowledge Formatter; Central Knowledge Server. |
| Newsletter and Alert Module | Digest sender | Proactively summarizes reviewed anonymized patterns and public facts for subscribed NGOs, regulators, researchers, and authorized partners. | Subscriber settings, digest preview, topic filters, send log. | Central Knowledge Server; Knowledge Packs; Stakeholder Engagement Module. |
| Stakeholder Engagement Module | Feedback collector | Contacts subscribers on a regular cadence to ask for response rankings, new observations, useful tools, and updated public information. | Survey prompts, ranking forms, observation forms, participation status. | Newsletter Module; Stakeholder Response Formatter; Central Knowledge Server. |
| Stakeholder Response Formatter | Feedback standardizer | Converts stakeholder survey answers into structured information objects or reviewable knowledge proposals. | Sanitized response summary, extracted fields, target template, validation issues. | Stakeholder Engagement Module; Knowledge Formatter; Central Knowledge Server. |

### Group E — Testing, training, and model improvement

These components decide whether a change is safe and whether a tuned model is good enough to ship.

| Plain-language component | Technical nickname | What it does | What it displays | Communicates with |
|---|---|---|---|---|
| Quality Testing Framework | Eval | Tests model and safety-layer behavior with example prompts, image prompts, rule-based scoring, LLM-based judging, regression checks, and model comparisons. | Scorecards, pass/fail gates, worst-to-best examples, model comparison tables, provenance. | Gemma 4 Model Layer; Safety Guidance Layer; Knowledge Packs; Fine-Tuning Module. |
| Fine-Tuning Module | Trainer | Fine-tunes or adapts Gemma 4 using approved, anonymized, provenance-tracked examples and stakeholder rankings. | Dataset manifest, training run status, evaluation gate result, model card, release artifact links. | Quality Testing Framework; Anonymization Module; Gemma 4 Model Layer; Knowledge Packs. |

## 5. How the components communicate

### Local or tenant deployment path

```text
User input or platform content
  -> Channel and Deployment Package
  -> Safety Guidance Layer
  -> Knowledge Packs + Tools + optional Online Search
  -> Gemma 4 Model Layer
  -> Safety Guidance Layer trace + final draft
  -> User, reviewer, caseworker, or researcher
```

### Privacy-preserving sharing path

```text
Local deployment sees sensitive content
  -> Local Anonymization Module creates a sanitized Information Object
  -> Information Submission Module sends only the sanitized object
  -> Central Knowledge Server stores it for review
  -> Knowledge Formatter turns approved items into Knowledge Pack updates
  -> Quality Testing Framework validates the update
  -> Clients pull the new versioned Knowledge Pack
```

### Public-source research path

```text
Public Information Research Monitor searches public sources
  -> Knowledge Formatter extracts structured public facts
  -> Central Knowledge Server review queue
  -> Human curator approval
  -> Knowledge Pack update
  -> Quality Testing Framework regression gate
  -> Published pack metadata and client updates
```

### Stakeholder engagement path

```text
Newsletter and Alert Module sends reviewed digest or ranking request
  -> Stakeholder Engagement Module collects rankings / observations / tools
  -> Stakeholder Response Formatter validates and structures responses
  -> Central Knowledge Server review queue
  -> Knowledge Formatter creates pack proposals or training examples
  -> Quality Testing Framework and Fine-Tuning Module consume approved data
```

### Fine-tuning path

```text
Approved anonymized examples + response rankings
  -> Fine-Tuning Module
  -> Tuned Gemma 4 adapter or model artifact
  -> Quality Testing Framework gate
  -> Model card + release artifact
  -> Channel and Deployment Package can opt in to the new model
```

## 6. Demos are separate from technical components

Demos are proof surfaces. They combine components for a judge, partner, or stakeholder. They are not the architecture itself.

| Demo surface | What it proves | Components shown |
|---|---|---|
| Kaggle chat playground | Gemma 4 plus Safety Guidance Layer behavior is visible and reproducible. | Gemma 4 Model Layer; Safety Guidance Layer; Knowledge Packs; Quality Testing Framework. |
| duecare-ai.com website | Central coordination, public story, pack registry, anonymized signal intake, and API docs exist. | Central Knowledge Server; Information Submission Module; Knowledge Packs; use-case pages. |
| Platform safety demo | A platform can screen recruitment content before workers see it. | Channel and Deployment Package; Safety Guidance Layer; Quality Testing Framework. |
| NGO & regulator demo | A caseworker or regulator can turn messages/documents into grounded, reviewable drafts. | Channel and Deployment Package; Safety Guidance Layer; Contacts; Knowledge Packs. |
| Individual worker / mobile demo | A worker can privately check a message or document and see trusted next steps. | Gemma 4 Model Layer; Safety Guidance Layer; Local Anonymization Module; mobile/local package. |
| Researcher demo | A researcher can rerun prompts, compare outputs, and verify claims. | Quality Testing Framework; Knowledge Packs; Gemma 4 Model Layer; Fine-Tuning Module. |
| Developer / integration partner demo | A technical team can embed Duecare into its own product or workflow. | Channel and Deployment Package; APIs; Knowledge Packs; Central Knowledge Server. |

## 7. Suggested website page names

- `/platform-safety` — Platform safety setup and integration.
- `/ngo-regulators` — NGO & regulator setup and trust boundary.
- `/individual-worker-mobile` — private chat and mobile guidance flow.
- `/researcher` — reproducibility, prompts, notebooks, and model comparisons.
- `/developers` — API, Docker, pack, schema, and integration-partner setup.
- `/knowledge-packs` — pack registry, templates, pull instructions.
- `/submit-information` — anonymized submission flow and consent boundary.
- `/research-monitor` — public-source research and crawler-style update proposals.
- `/stakeholder-engagement` — response ranking, observations, and subscriber feedback.

## 8. One-sentence architecture summary

Duecare combines Gemma 4, a safety guidance layer, versioned knowledge packs, privacy-preserving submissions, public-source research, stakeholder feedback, testing, and fine-tuning so Platform safety, NGO & regulator, Individual worker / mobile, Researcher, and Developer / integration partner lanes can use the same trusted core without centralizing raw worker data.
