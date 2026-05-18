# Full component buildout plan — Duecare platform

> Prepared: 2026-05-08  
> Scope: build every Duecare component, including parts not showcased in Kaggle.  
> Constraint: the 2026-05-18 Kaggle submission must remain stable while longer-horizon platform work proceeds.

## 0. North star

Duecare should become a Gemma 4-powered safety infrastructure platform for migrant-worker protection. The platform should serve three outcomes:

1. **Prevent exploitation before it spreads** — help platforms, recruitment marketplaces, and organizations detect illicit recruitment, coercion, scams, illegal-fee language, document-retention pressure, and other exploitation patterns earlier.
2. **Assist victims and at-risk workers** — help NGO, government, and mobile workflows intake cases, organize evidence, guide workers, draft safer responses, prepare referral paths, and support case teams.
3. **Understand what is happening and why** — help researchers, regulators, advocates, journalists, and partners see the who, what, where, when, and why behind exploitation patterns through notebooks, knowledge packs, trend signals, provenance, and shared analysis.

Those outcomes route through six canonical lanes, always in this order:

1. **Platform safety** — social media companies, job platforms, and marketplaces detecting exploitative recruitment and scam patterns.
2. **NGO & regulator** — NGOs, governments, consulates, and regulators triaging complaints, advising workers, and routing cases.
3. **Individual worker / mobile** — migrant workers getting private, localized, grounded guidance.
4. **Researcher** — researchers, evaluators, journalists, and judges benchmarking models, policies, and intervention quality.
5. **Anonymized knowledge sharing** — partners turning reviewed, sanitized facts into reusable knowledge objects without exposing raw case files.
6. **Developer / integration partner** — teams embedding Duecare into WhatsApp, Messenger, dashboards, internal tools, or custom deployments.

The system must preserve three invariants:

- **Data boundaries are explicit.** Raw worker data must not be centralized or used for training without explicit consent, anonymization, and provenance.
- **Gemma 4 is load-bearing.** Function calling, multimodal understanding, local/runtime deployment, and fine-tuning should be core to the architecture.
- **Deterministic safety stays outside the model.** Gemma reasons and explains; the harness, contacts, rubrics, and vetted knowledge packs supply auditable control.

---

## 1. Target component map

| # | Component | Product name | Primary owner | Status target |
|---:|---|---|---|---|
| 1 | Gemma 4 model runtime | Duecare Runtime | model/runtime package | Live core |
| 2 | Safety harness | Duecare Harness | chat/harness package | Live core |
| 3 | Evaluation framework | Duecare Eval | tasks/eval package | Live core |
| 4 | Knowledge exchange / safety harness connections | Duecare Exchange | core + publishing | Platform foundation |
| 5 | Continuous update agent + server | Public Information Research Monitor | agents + workflows | Platform foundation |
| 6 | Retraining / adaptation module | Duecare Trainer | models + publishing | Prototype to production |
| 7 | NGO/government chatbot channels | Duecare Channels | chat + deployment | Prototype to production |
| 8 | Worker mobile app | Duecare Mobile | mobile sibling app | Companion product |

Canonical flow:

```text
Sources and partner updates
  → Public Information Research Monitor proposes updates
  → human/curator review
  → vetted knowledge packs
  → Runtime + Harness + Eval consume packs
  → Platform safety, NGO & regulator, Individual worker / mobile, Researcher, Anonymized knowledge sharing, and Developer / integration partner use the same core
  → Trainer learns from approved anonymized failures and releases adapters
```

---

## 2. Build strategy

Do not build these as one monolith. Build them as **contract-first vertical slices**.

Each component gets:

1. a short product purpose;
2. Pydantic schemas or protocol contracts;
3. a minimal local implementation;
4. tests;
5. a demo surface or CLI;
6. a privacy/provenance gate;
7. documentation that says whether it is live, prototype, or roadmap.

Recommended sequencing:

| Phase | Goal | Components touched | Why first |
|---|---|---|---|
| A | stabilize core contracts | Runtime, Harness, Eval | prevents drift before expanding |
| B | externalize knowledge packs | Harness, Exchange, Research Monitor | makes RAG/GREP/contacts maintainable |
| C | build Trainer MVP | Trainer, Eval, Publishing | proves Gemma 4 adaptation story |
| D | build Channels MVP | Channels, Harness, Contacts | highest real-world NGO/government value |
| E | build Research Monitor service | Research Monitor, Exchange | keeps laws/contacts/current docs fresh |
| F | build production integration paths | Mobile, enterprise adapters, research workflows | expands from demo to product |

---

## 3. Component 1 — Duecare Runtime

### Purpose

Load, serve, and normalize calls to Gemma 4 variants and other comparison models across Kaggle, local desktop, cloud BYOK, Ollama, llama.cpp, and future LiteRT/mobile paths.

### Owns

- model registry;
- model loading state;
- generation config;
- output sanitization;
- streaming contract;
- runtime telemetry;
- model compatibility checks;
- local/cloud fallback selection.

### Should not own

- RAG documents;
- safety policy;
- contact routing;
- evaluation scoring;
- training data.

### MVP deliverables

- Keep current Kaggle model picker stable.
- Make `sanitize_model_output()` mandatory for every route.
- Add one model capability descriptor per model: context window, image support, function calling support, thinking template, expected load time.
- Add a cold-load diagnostic endpoint that separates download, tokenizer load, model load, adapter load, and first-token latency.

### Production deliverables

- `ModelRuntime` protocol in core/models.
- `RuntimeCapability` Pydantic model.
- `ModelLoadEvent` schema.
- Runtime registry loaded from JSON/YAML.
- llama.cpp and LiteRT compatibility exporters.
- Per-model recommended harness compression settings.

### Tests

- sanitizer regression tests;
- model registry validation;
- mock generation test;
- load-log event ordering test;
- no raw prompt logging test.

---

## 4. Component 2 — Duecare Harness

### Purpose

Provide deterministic, auditable safety scaffolding around Gemma 4: persona, GREP rules, RAG retrieval, tools/function calling, contacts, online/search, and complaint-draft support.

### Owns

- RAG corpus;
- GREP rules;
- persona/context templates;
- function-callable tools;
- contacts directory;
- complaint draft templates;
- harness trace format;
- retrieval config;
- evidence/citation graph.

### Should not own

- model weights;
- training execution;
- production channel credentials;
- raw case storage.

### MVP deliverables

- Treat Contacts as a first-class layer alongside RAG/GREP/tools.
- Add a `Report this scenario` draft flow that never auto-sends.
- Move the most volatile static copy and severity colors into shared brand/config.
- Add a `HarnessLayerSpec` registry so adding a new layer is a one-file edit.

### Production deliverables

- Move `RAG_CORPUS` into a curator-block JSON file.
- Move `GREP_RULES` into a curator-block JSON file with regex validation.
- Add vetted knowledge-pack loading with integrity checks.
- Add tenant-specific overlays: global pack + country pack + NGO/government pack.
- Add per-session harness state instead of global `app.state` recent hits.

### Tests

- curator-block validation;
- regex compile validation;
- RAG doc schema validation;
- contacts schema validation;
- complaint draft contains no raw hidden PII;
- auto-send disabled test;
- harness trace snapshot tests.

---

## 5. Component 3 — Duecare Eval

### Purpose

Evaluate model outputs, harnessed responses, chatbot behavior, fine-tuned adapters, and policy/regulatory correctness using reproducible rubrics and test suites.

### Owns

- universal rubric;
- evaluation questions;
- deterministic graders;
- LLM-as-judge hooks;
- adversarial probes;
- report generation;
- benchmark manifests;
- stock vs harnessed vs tuned comparisons.

### Should not own

- training execution;
- channel sessions;
- live user conversations;
- contact truth.

### MVP deliverables

- Lock the rubric manifest.
- Add version/count self-audit before publishing.
- Add a one-command smoke suite for app endpoints and rubric counts.
- Add a small adversarial replay panel or CLI report.

### Production deliverables

- `EvaluationRun` Pydantic schema.
- Dataset/run manifest keyed by git SHA and dataset version.
- Multi-model comparison reports.
- Regression gates for Trainer releases.
- Channel-specific safety evaluation: Messenger, web chat, SMS.

### Tests

- no stale-count drift test;
- rubric schema test;
- evaluator fallback test;
- deterministic grader snapshot test;
- evaluator agreement/disagreement tests;
- benchmark reproducibility test.

---

## 6. Component 4 — Duecare Exchange

### Purpose

Let trusted stakeholders share privacy-preserving safety knowledge without sharing raw cases: vetted rules, RAG docs, contact updates, aggregate trend signals, hashes, and anonymized examples.

### Owns

- knowledge-pack format;
- signature/verification metadata;
- provenance manifest;
- compatibility/version policy;
- anonymized aggregate signal schema;
- import/export tools;
- partner contribution workflow.

### Should not own

- raw case databases;
- private NGO records;
- model training without approval;
- live worker chats.

### MVP deliverables

- Define `KnowledgePackManifest`.
- Define pack types: `rag_docs`, `grep_rules`, `contacts`, `rubrics`, `examples`, `tools`, `jurisdictions`.
- Add local pack validation CLI.
- Add import preview: show what a pack changes before applying.

### Production deliverables

- Vetted, integrity-checked pack distribution.
- Partner contribution PR template.
- Conflict resolution when two packs update the same contact/doc/rule.
- Pack compatibility matrix by Duecare version.
- Privacy-preserving trend export for research.

### Tests

- manifest schema tests;
- signature verification tests;
- incompatible-pack rejection;
- no raw PII in pack test;
- deterministic diff output test.

---

## 7. Component 5 — Public Information Research Monitor

### Purpose

Continuously track public changes in laws, regulations, agency pages, complaint forms, hotline/contact pages, scam patterns, and NGO guidance, then propose update packs for human review. Internally this component can still use the `sentinel` package/module name, but public docs should describe it as the Public Information Research Monitor.

### Owns

- source registry;
- crawler/fetcher jobs;
- change detection;
- summarization;
- proposed knowledge-pack diffs;
- contact freshness checks;
- curator review queue;
- update audit trail.

### Should not own

- direct mutation of production packs without review;
- raw private case intake;
- auto-reporting to agencies.

### MVP deliverables

- `sources.yaml` for public URLs and contact pages.
- Planned `research-monitor check` command that fetches pages and flags changed hashes or 404s.
- A generated `proposed_updates.json` file for curator review.
- Contact freshness report for `_contacts.json`.

### Production deliverables

- Scheduled worker.
- Review dashboard.
- Automatic diff summaries.
- Watchlists by jurisdiction/corridor.
- RAG doc update suggestions.
- Vetted release after approval.

### Tests

- mock HTTP fetch tests;
- changed-hash detection;
- 404/contact stale detection;
- proposal schema validation;
- no automatic production mutation test.

---

## 8. Component 6 — Duecare Trainer

### Purpose

Tune Gemma 4 to specific use cases using approved, anonymized, provenance-tracked data and release adapters only after evaluation gates pass.

### Owns

- training recipes;
- dataset manifests;
- anonymized training splits;
- LoRA config;
- Unsloth pipeline;
- adapter registry;
- model cards;
- evaluation gates;
- export to GGUF/LiteRT where feasible.

### Should not own

- raw case data;
- live worker conversations;
- source crawling;
- official contact truth;
- production complaint sending.

### Use-case adapters

| Adapter | Target |
|---|---|
| `duecare-gemma-case-intake` | NGO/government complaint triage |
| `duecare-gemma-platform-moderation` | social/job-platform moderation |
| `duecare-gemma-worker-advisor` | worker-facing plain-language advice |
| `duecare-gemma-evaluator` | rubric/evaluator quality |
| `duecare-gemma-multimodal-docs` | screenshots, contracts, receipts, posts |
| `duecare-gemma-corridor-*` | corridor-specific law/contact/language adaptation |

### MVP deliverables

- Training manifest schema.
- Dataset builder from approved examples and rubric failures.
- One small LoRA smoke run on a tiny sample.
- Evaluation gate that compares stock vs harnessed vs tuned.
- Model card template.

### Production deliverables

- Full Unsloth recipe for Gemma 4 E4B/E2B.
- LoRA registry.
- GGUF export and quantization.
- LiteRT export pathway.
- Adapter selection policy for Channels and Mobile.
- Red-team regression gate before release.

### Hard gate

```text
raw input
  → anonymizer
  → curator approval
  → dataset manifest
  → train/val/test split
  → fine-tune
  → eval gates
  → model card
  → release
```

### Tests

- manifest schema test;
- train split has no raw PII;
- deterministic split test;
- tiny training dry-run or mocked trainer test;
- model-card completeness test;
- eval gate blocks regression.

---

## 9. Component 7 — Duecare Channels

### Purpose

Deploy Duecare through institution-owned channels so NGOs, governments, regulators, consulates, and worker organizations can advise migrant workers on platforms they already use.

### Target channels

- Facebook Messenger;
- WhatsApp Business;
- Telegram;
- Viber;
- SMS;
- web chat widget;
- government/NGO website portal;
- caseworker dashboard.

### Owns

- channel adapters;
- tenant configuration;
- consent UX;
- conversation/session state;
- handoff to human caseworker;
- complaint draft UX;
- channel-safe response formatting;
- tenant-specific RAG pack selection;
- audit log redaction.

### Should not own

- model weights;
- global laws database;
- raw long-term case management unless explicitly configured;
- automatic complaint sending;
- contact truth outside verified packs.

### MVP deliverables

- `ChannelMessage` schema.
- `ChannelAdapter` protocol.
- Web-chat adapter first, because it is easiest to demo and test locally.
- Messenger/WhatsApp adapter stubs with clear environment-variable requirements.
- Tenant config schema: language, jurisdiction, RAG packs, contacts, escalation policy.
- Complaint draft object that requires explicit user/caseworker action.

### Production deliverables

- Messenger webhook.
- WhatsApp Business webhook.
- Telegram bot adapter.
- SMS adapter.
- Human handoff queue.
- Caseworker console.
- Tenant admin page for RAG/contact packs.
- Abuse/rate limiting.
- Consent and retention controls.

### Safety boundaries

Allowed:

- answer grounded questions;
- triage complaint categories;
- suggest verified contacts;
- draft complaint text;
- open official forms;
- hand off to humans.

Not allowed by default:

- auto-submit complaints;
- auto-email agencies;
- auto-call hotlines;
- hallucinate phone numbers;
- store raw conversation content without consent;
- tell workers to confront employers or recruiters.

Canonical rule:

> Duecare drafts; the user or trusted caseworker decides.

### Tests

- channel adapter contract tests;
- webhook signature tests where applicable;
- no auto-send test;
- tenant config validation;
- redacted audit log test;
- human handoff test;
- complaint draft safety test.

---

## 10. Component 8 — Duecare Mobile

### Purpose

Give individual migrant workers a private, worker-owned assistant that can run locally where possible and avoid sending sensitive messages to central servers.

### Owns

- mobile UX;
- offline/on-device runtime where feasible;
- local encrypted storage;
- worker safety planning;
- private document/screenshot review;
- local knowledge-pack sync;
- language/corridor selection;
- optional consent-based export to NGO/caseworker.

### Should not own

- NGO tenant administration;
- central training pipeline;
- automatic reporting;
- unverified legal/contact generation.

### MVP deliverables

- Worker-safety workflow spec.
- Local-only mode design.
- Knowledge-pack sync design.
- Synthetic screenshot/document demo.
- Consent-based export format for NGO handoff.

### Production deliverables

- LiteRT/GGUF runtime integration.
- Encrypted local journal.
- Offline RAG/contact pack.
- Multilingual worker guidance.
- Panic/quick-exit UX if appropriate.
- Safe referral handoff.

### Tests

- no network in local mode test;
- encrypted storage test;
- no raw export without consent;
- knowledge-pack signature verification;
- safe language/translation regression tests.

---

## 11. Shared schemas to create first

These contracts let all components grow without coupling.

| Schema | Used by | Purpose |
|---|---|---|
| `KnowledgePackManifest` | Harness, Exchange, Research Monitor, Channels, Mobile | vetted pack metadata and integrity fields |
| `KnowledgePackDiff` | Research Monitor, Exchange | proposed update review |
| `ContactRecord` | Harness, Channels, Mobile, Research Monitor | verified routing info |
| `ComplaintDraft` | Harness, Channels, Mobile | draft-only complaint flow |
| `HarnessTrace` | Harness, Eval, Channels | auditable layer outputs |
| `EvaluationRun` | Eval, Trainer | reproducible benchmark result |
| `TrainingManifest` | Trainer, Publishing | data/provenance for adapters |
| `TenantConfig` | Channels, Exchange | NGO/government deployment config |
| `ChannelMessage` | Channels, Harness | normalized chat message |
| `ConsentReceipt` | Channels, Mobile | explicit user permission |
| `ModelAdapterCard` | Trainer, Runtime | model capability/provenance card |

Recommended location:

```text
packages/duecare-llm-core/src/duecare/core/schemas/
```

If that package is too stable to disturb before submission, create them first under:

```text
docs/schemas/*.schema.json
```

Then promote to code after the Kaggle freeze.

---

## 12. Repository implementation plan

### Milestone 1 — make the platform map canonical

Effort: 0.5 day

Deliverables:

- Add this buildout plan.
- Update architecture/component docs to the 8-component map.
- Add a `components.yaml` or `components.json` source-of-truth.
- Add a small script that renders component tables from the canonical file.

Acceptance criteria:

- one file defines the eight components;
- docs and notebook showcase can read/render from it;
- no stale 6-component wording remains in public docs.

### Milestone 2 — stabilize live core

Effort: 1-2 days

Deliverables:

- fix version/count drift in public docs and wheel metadata;
- ensure tests pass without manual `PYTHONPATH`;
- require sanitizer on every model route;
- add live deployment smoke checklist;
- freeze Kaggle-critical code path.

Acceptance criteria:

- local chat package tests pass from clean shell;
- `/api/version`, `/api/brand`, `/api/health-check` agree;
- old `21 dim` / `35 doc` / stale version strings are gone from release docs;
- Kaggle wheel version matches source.

### Milestone 3 — knowledge packs and contacts

Effort: 2-4 days

Deliverables:

- promote `_contacts.json` to validated first-class curator block;
- define `KnowledgePackManifest`;
- add local pack validation;
- add contact freshness checker;
- add draft-only complaint object.

Acceptance criteria:

- adding/updating contacts is one JSON edit plus validation;
- report flow never auto-sends;
- contacts can be used by UI, Channels, and Mobile through the same schema.

### Milestone 4 — Duecare Trainer MVP

Effort: 3-7 days for MVP; longer for production training

Deliverables:

- training manifest;
- anonymized dataset builder;
- small LoRA smoke recipe;
- evaluation gate;
- model-card template;
- adapter registry stub.

Acceptance criteria:

- a tiny training/eval path can run end-to-end or in dry-run mode;
- eval can compare stock vs tuned;
- training data is provenance-tracked and PII-gated.

### Milestone 5 — Duecare Channels MVP

Effort: 3-7 days for web-chat MVP; longer for real Messenger/WhatsApp

Deliverables:

- `ChannelAdapter` protocol;
- web-chat channel adapter;
- tenant config;
- complaint draft flow;
- human handoff stub;
- Messenger/WhatsApp webhook stubs.

Acceptance criteria:

- one web-chat tenant can load a tenant-specific RAG/contact pack;
- complaint drafts are generated but not sent;
- logs are redacted;
- channel can call the same harness as the Kaggle app.

### Milestone 6 — Public Information Research Monitor MVP

Effort: 3-5 days

Deliverables:

- source registry;
- fetch/check command;
- hash-based change detection;
- contact URL freshness report;
- proposed update file.

Acceptance criteria:

- Research Monitor can flag a changed public page without mutating production;
- proposed updates are reviewable by a human;
- no raw private data enters the Research Monitor.

### Milestone 7 — Duecare Exchange MVP

Effort: 3-5 days

Deliverables:

- pack import/export CLI;
- pack diff preview;
- compatibility metadata;
- PII scan gate;
- partner contribution instructions.

Acceptance criteria:

- a partner can submit a new RAG/contact/rule pack as one folder;
- CI validates it;
- applying it is explicit and reversible.

### Milestone 8 — Mobile integration path

Effort: multi-week

Deliverables:

- mobile knowledge-pack contract;
- local/on-device model path;
- consent-based handoff export;
- offline contact pack;
- privacy checklist.

Acceptance criteria:

- mobile can consume vetted packs;
- raw worker content stays local unless explicitly exported;
- mobile path does not depend on Kaggle or central servers.

---

## 13. Suggested package layout

Short term: avoid package explosion before the Kaggle deadline. Use docs and small modules first.

Medium term:

```text
packages/
  duecare-llm-core/          # schemas, protocols, provenance, consent
  duecare-llm-models/        # runtime adapters + trainer integration points
  duecare-llm-chat/          # harness chat UI + local demo + web chat
  duecare-llm-tasks/         # evaluation suites
  duecare-llm-agents/        # Research Monitor/update agents
  duecare-llm-workflows/     # DAGs for update/train/eval workflows
  duecare-llm-publishing/    # HF/Kaggle/model cards/knowledge pack publishing
  duecare-llm-channels/      # optional future package for Messenger/WhatsApp/etc.
  duecare-llm-trainer/       # optional future package for Unsloth/LoRA recipes
```

Do not split `channels` or `trainer` into new packages until their contracts settle. Start with modules under existing packages or a prototype folder, then extract.

---

## 14. Build order by use-case value

### 1. Platform safety

1. Runtime + Harness.
2. Platform moderation adapter in Trainer.
3. Batch moderation API.
4. Policy/evidence trace.
5. Evaluation reports.
6. Privacy-preserving trend exchange.

### 2. NGO & regulator

1. Contacts + complaint draft flow.
2. Tenant RAG packs.
3. Web-chat channel.
4. Caseworker handoff.
5. Messenger/WhatsApp adapters.
6. Research Monitor contact/law freshness checks.
7. Trainer for case-intake adapter.

### 3. Individual worker / mobile

1. Mobile/local privacy design.
2. Worker-advisor adapter.
3. Offline contacts and RAG pack.
4. Screenshot/document review.
5. Consent-based handoff.

### 4. Researcher

1. Eval manifests and reproducible runs.
2. Stock vs harnessed vs tuned comparisons.
3. Knowledge-pack versioning.
4. Public benchmark exports.
5. Multi-domain evaluation.

---

## 15. Safety and governance checklist

Every component must answer these before release:

- What raw data can it see?
- Where can data leave the device or tenant?
- Is consent required?
- Is PII logged, stored, trained on, or published?
- Does the model generate facts, or retrieve verified facts?
- Can a user or caseworker review before action?
- Is there an audit trail with hashes instead of plaintext?
- Can the component run with synthetic examples only?
- Does it fail closed if contacts/RAG/model are unavailable?

Component-specific hard stops:

| Component | Hard stop |
|---|---|
| Runtime | do not display thinking/scratchpad output |
| Harness | do not hallucinate contacts or statutes |
| Eval | do not count unreproducible numbers as results |
| Exchange | do not accept packs with raw PII |
| Research Monitor | do not auto-apply updates without review |
| Trainer | do not train on raw or unapproved cases |
| Channels | do not auto-send complaints or store chats silently |
| Mobile | do not transmit worker data without consent |

---

## 16. What to build before vs after Kaggle

### Before 2026-05-18

Build only pieces that do not destabilize the submission:

- canonical 8-component documentation;
- contacts/hotlines polish;
- complaint draft spec;
- training/adaptation spec and existing Unsloth path documentation;
- channel architecture spec;
- validation scripts for drift and contacts;
- small static or local demo surfaces if low risk.

Avoid:

- live Messenger/WhatsApp production integration;
- major package splits;
- rewriting the chat UI with a framework;
- moving all RAG/GREP into JSON unless tests are already ready;
- central server auth/multi-tenant production complexity.

### After Kaggle

Build in this order:

1. schemas and pack manifest;
2. knowledge-pack validation and import/export;
3. Trainer MVP;
4. Channels web-chat MVP;
5. Research Monitor MVP;
6. Messenger/WhatsApp/SMS adapters;
7. vetted pack distribution;
8. mobile offline pack/runtime path;
9. enterprise moderation API;
10. production deployment/security hardening.

---

## 17. Definition of done by component

| Component | MVP done when... | Production done when... |
|---|---|---|
| Runtime | mock + local + Kaggle model calls share a protocol | model capabilities, logs, exports, fallback, and sanitizer are standardized |
| Harness | layers are inspectable and contacts are first-class | RAG/GREP/contacts/tools are vetted curator packs with per-session state |
| Eval | one command validates counts/endpoints/rubrics | every model/pack release has reproducible eval manifests |
| Exchange | packs can be validated and diffed locally | partners can publish vetted packs with CI and compatibility checks |
| Research Monitor | public URL/contact changes produce proposals | scheduled review/release workflow keeps packs current |
| Trainer | tiny LoRA/dry-run path proves contracts | approved adapters ship with model cards, exports, and regression gates |
| Channels | web-chat tenant works with draft-only complaint flow | Messenger/WhatsApp/SMS/web channels support human handoff and tenant packs |
| Mobile | design and pack contract are ready | offline/private worker assistant consumes vetted packs safely |

---

## 18. Immediate next tasks

1. Create `components.yaml` as the canonical eight-component registry.
2. Add a simple renderer script that prints the component table for docs/notebooks.
3. Update public docs to stop describing the platform as only a Kaggle chat package.
4. Add `ContactRecord`, `ComplaintDraft`, `TenantConfig`, and `KnowledgePackManifest` draft schemas.
5. Add a no-network dry-run path for Trainer.
6. Add a web-chat Channels prototype that calls the existing harness without changing the Kaggle app.
7. Add Research Monitor contact freshness checks for `_contacts.json`.
8. Add an Exchange pack validator that scans for PII and schema errors.

The safe implementation rule is:

> New components may call the current live harness, but the current Kaggle harness must not depend on new components until after the submission freeze.
