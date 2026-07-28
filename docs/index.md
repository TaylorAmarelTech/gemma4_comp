---
hide:
  - navigation
  - toc
---

# DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection

DueCare is open-source software that helps platforms, NGOs, regulators,
researchers, developers, and worker-support deployments spot recruitment
fraud, illegal fees, coercive control, and trafficking risk earlier. Gemma 4 is
the reasoning engine, but the strength comes from the component ecosystem
around it: workbenches, harnesses, knowledge packs, search guards,
anonymization gates, graph extraction, evaluation, benchmarks, and a public hub
that can exchange only safe, reviewed objects.

The same pattern is intentionally reusable beyond migrant-worker protection.
The
[Capability-Gap Harness and Network Blueprint](architecture/capability_gap_blueprint.md)
shows how to replace the domain pack while preserving the evidence, harness,
evaluation, human-governance, public-network, and agent-operations contracts.
<!-- audit-allow:drift reason: maps a legacy compatibility name to canonical server automation -->
It also maps Hermes, the legacy OpenClaw-compatible server-automation role,
orchestration, sharing, and a container-friendly deployment target without
claiming that the current agents autonomously contact or rate people.

## The ecosystem idea

DueCare is not a single chatbot. It is a set of components designed to
talk to each other through shared fact objects, evidence edges,
versioned packs, traces, and exports. A document review can feed
Knowledge Extraction. Knowledge Extraction can feed Search and
evaluation. Search results pass through safety and verification before
they become context. Anonymization & Sharing is the consent gate before
anything leaves a local node.

The strongest use case is a network of trusted local nodes. A worker,
NGO office, regulator, platform team, or researcher can process raw
case material locally. DueCare helps turn that material into reviewed
fact objects, evidence edges, and risk-pattern summaries. Raw worker
files stay where they belong. Only explicitly reviewed, redacted, and
anonymized facts or aggregate signals move outward.

When many local nodes share those safe fact objects, the ecosystem can
see recruitment-abuse and trafficking patterns that no single office
can see alone: repeated fee requests, passport-retention clauses,
corridor-specific false promises, and cross-case signals that justify
stronger prevention, investigation, and worker support.

The Render public hub is the reference website for this ecosystem story:
[duecare-ai.com](https://duecare-ai.com/). Its source lives in
[`apps/duecare-ai.com`](https://github.com/TaylorAmarelTech/gemma4_comp/tree/master/apps/duecare-ai.com),
so Pages documentation, Kaggle surfaces, and the public website can be
reviewed against the same repo.

## Public URLs

| Surface | URL | Role |
|---|---|---|
| **Main server website / public hub** | [duecare-ai.com](https://duecare-ai.com/) | Render-hosted FastAPI site and coordination service. It shows the public product story, serves hub APIs, and accepts only public-source proposals, vetted pack metadata, anonymized aggregate signals, hash receipts, and consented contact metadata. |
| **Read-only continuity site** | [tayloramareltech.github.io/duecare-ai-site](https://tayloramareltech.github.io/duecare-ai-site/) | Independent backend-free copy of the 51 public website routes and five allowlisted snapshots. State-changing controls and mutable APIs are disabled; Render and production DNS remain active. |
| **GitHub source repo** | [github.com/TaylorAmarelTech/gemma4_comp](https://github.com/TaylorAmarelTech/gemma4_comp) | Source of truth for the monorepo: Kaggle kernels, packages, docs, Render website source, scripts, validation gates, and GitHub Actions. |
| **GitHub Pages docs** | [tayloramareltech.github.io/gemma4_comp](https://tayloramareltech.github.io/gemma4_comp/) | Static MkDocs documentation generated from `docs/`. This is the easiest route for onboarding, install guides, scenarios, architecture, reproducibility notes, and judge-facing review pages. |

## Choose Your User Path

DueCare uses the same six lanes as the public hub at
[duecare-ai.com](https://duecare-ai.com/). They are roles in one ecosystem, not
separate products: content moderation, case analysis, worker support,
research, anonymized knowledge sharing, and custom API implementations all use
the same Gemma 4-centered safety stack.

| User Path | What You Need | Where To Start |
|---|---|---|
| **I am on a platform safety team** | Screen risky recruitment posts, ads, profiles, and messages before workers are harmed. | [Enterprise pilot](scenarios/enterprise_pilot.md), [Deployment guide](deployment_enterprise.md), and the content screening API. |
| **I am an NGO, caseworker, regulator, or legal-aid reviewer** | Turn messages, documents, and public rules into grounded drafts, referrals, complaint materials, and corridor updates. | [Caseworker workflow](scenarios/caseworker_workflow.md), [NGO office deployment](scenarios/ngo-office-deployment.md), and [Regulator pattern analysis](scenarios/regulator-pattern-analysis.md). |
| **I am a migrant worker or prospective worker** | Understand suspicious offers, contracts, recruiter messages, fee demands, document retention, threats, and next steps privately. | [Worker self-help](scenarios/worker-self-help.md) and the [DueCare Journey Android releases](https://github.com/TaylorAmarelTech/duecare-journey-android/releases). |
| **I am a researcher, evaluator, or auditor** | Reproduce model behavior, compare safety interventions, inspect pack hashes, and audit every claim from source artifacts. | [Publication readiness](PUBLICATION_READINESS.md), [Researcher analysis](scenarios/researcher-analysis.md), [Reproducibility](reproducibility.md), and [A-00 proof path](FOR_PEER_REVIEW.md#a-00-proof-path). |
| **I am sharing anonymized knowledge** | Convert reviewed local evidence into sanitized fact objects that improve shared packs without centralizing raw worker case data. | [Anonymization policy](anonymization_policy.md), [Submission labeling policy](submission_labeling_policy.md), the workbench Anonymization & Sharing page, and the [civil-society outreach loop](https://duecare-ai.com/outreach) (contribute by replying to an email). |
| **I am a developer or integration partner** | Embed DueCare into moderation tools, NGO systems, mobile clients, dashboards, or custom workflows. | [Install guide](install.md), [Embedding guide](embedding_guide.md), [OpenAPI spec](openapi.yaml), and [Client connect](https://duecare-ai.com/client-connect). |

## Deployment And Use Cases

The same components can be assembled for different operating contexts.
Each deployment keeps the sensitive-data boundary explicit.

| Use Case | Local Components | Shared Components |
|---|---|---|
| **Platform safety deployment** | Content screening API, GREP rules, corridor packs, risk explanations, queue-ready review payloads, and moderation audit traces. | Anonymized pattern signals and vetted pack updates. |
| **NGO & regulator office deployment** | Local case-bundle review, citation-backed summaries, referral drafts, graph extraction, document review, and caseworker-controlled exports. | Reviewed public facts, sanitized observations, pack proposals, and aggregate corridor trends. |
| **Individual worker / mobile deployment** | Trusted mobile or chat experience, private notes, local guidance, evidence organization, and worker-controlled sharing. | Only worker-approved notes, intake drafts, or sanitized signals. |
| **Researcher deployment** | Reproducible prompts, model comparisons, rule and LLM judging, optional community benchmark runs, and A-00 training/evaluation artifacts. | Versioned scorecards, model cards, evaluation metadata, and pack hashes. |
| **Anonymized knowledge sharing deployment** | Local redaction, PII checks, consent-aware metadata, fact-object review, evidence-edge review, and hash receipts. | Sanitized fact objects, aggregate signals, vetted pack proposals, benchmark rows, and rejected-submission receipts. |
| **Developer / integration deployment** | FastAPI routes, package modules, schemas, Docker/runtime examples, client snippets, and local validation scripts. | Public APIs, docs, pack registry, release artifacts, and integration examples. |

## Information Sharing Architecture

DueCare is designed for many local nodes to learn from each other
without becoming one raw case-data warehouse.

| Stage | Component | Output | Boundary |
|---|---|---|---|
| **Local review** | Workbench, mobile app, or tenant deployment | Drafts, citations, graph edges, review decisions, and local audit traces. | Raw chats, case files, IDs, screenshots, and private documents stay local. |
| **Local anonymization** | Anonymization & Sharing workflow | Sanitized fact object, aggregate signal, public-source proposal, or hash receipt. | Reviewer consent and redaction happen before upload. |
| **Hub intake** | duecare-ai.com public hub | Review queue entry, validation result, and submission receipt. | Server-side PII checks reject raw private case content. |
| **Curation** | Curator and civil-society review | Vetted pack update, contact metadata update, benchmark row, or rejected proposal. | Human review is required before shared knowledge becomes reusable. |
| **Reuse** | Local nodes pulling updated packs | Better rules, citations, examples, and evaluation artifacts in future local deployments. | Shared intelligence returns as versioned packs, not as exposed case narratives. |

**Outreach planning and intake.** The
[civil-society outreach page](https://duecare-ai.com/outreach) detects knowledge
that needs field verification (a corridor fee cap, an emerging payment rail, or
a statute change), matches opted-in topic profiles, and drafts a specific
question. The public hub stores only an address hash, so it cannot send the
draft: a curator must resolve the hashes against a separately owned, consented
address book before using an organization-owned mailer. Human-sent replies can
be vetted through the PII gate and folded into *prioritized context*
and *candidate grading dimensions*. No contact, reply, or human rating is
claimed merely because the planning API is available.

Read the focused [Information Sharing Architecture](information_sharing_architecture.md)
page for the object types, trust boundary, and hub/local responsibilities.
For a shorter public explanation, read
[Gemma 4 for Networked Knowledge Sharing Without Centralizing PII](gemma_networked_knowledge_sharing.md).
For copy-ready Kaggle discussion copy with a title and opening paragraph, use
[Copy-ready Kaggle Post: DueCare Networked Knowledge Sharing](kaggle_post_networked_knowledge_sharing.md).
For the final competition closeout, new architecture/evaluation work, and
post-grading node-first hosting decision, use the
[copy-ready final Kaggle post](kaggle_final_closeout_post.md).

## Source verification

Recruitment-fraud drafts are only as trustworthy as the entities behind them, so
DueCare grounds them in real public records. The **entity-intelligence pipeline**
verifies recruiters, employers, and their beneficial owners against **34 official
government registries** — licensed-recruiter lists, fishing-vessel and money-lender
registers, sanctions and debarment lists, and GLEIF / OpenOwnership corporate
ownership — drawn from a **1,111-source** catalogue spanning 95 countries and 18
industries, alongside **532** migrant worker-support organisations (helplines,
shelters, legal aid, unions) for referral. It is **propose-only**: resolved records
are staged for curator review, never auto-merged, and kept strictly separate from
the trafficking knowledge layer.

Judges can browse the live registry map, licence ledger, and connector status at
[duecare-ai.com/source-verification](https://duecare-ai.com/source-verification);
the full per-source map and connector reference live in the
[Entity-intelligence pipeline](entity_intelligence_pipeline.md) doc.

## Core Components

| Component | Purpose |
|---|---|
| **Gemma 4 model layer** | Local reasoning, classification, summarization, multimodal reading, and draft generation. |
| **Safety guidance layer** | Persona, GREP rules, retrieval, tools, imports, search verification, and traceable response assembly. |
| **Knowledge packs** | Versioned rules, citations, contacts, corridor facts, tool definitions, examples, and evaluation data. |
| **Local anonymization module** | Converts reviewed sensitive material into redacted fact objects or aggregate signals before sharing. |
| **Central knowledge server** | Hosts public docs, APIs, vetted pack metadata, anonymized aggregate signals, and review queues. |
| **Quality and training layer** | Reproducible evaluation, A-00 proof runs, benchmark artifacts, and optional Gemma 4 adaptation. |
| **Entity-intelligence pipeline** | Propose-only verification of recruiters, employers, and their owners against 34 official government registries; feeds curator-reviewed pack updates. See [Entity-intelligence pipeline](entity_intelligence_pipeline.md) and the live [source-verification page](https://duecare-ai.com/source-verification). |

## Run Or Verify

| Goal | Start |
|---|---|
| **Try the workbench** | Open [DueCare App on Kaggle](https://www.kaggle.com/code/taylorsamarel/duecare-app), run it, and open the Cloudflare URL. |
| **Take over maintenance** | Start with the tracked [Claude Code handoff](CLAUDE_CODE_HANDOFF.md), run the [successor pickup rehearsal](SUCCESSOR_REHEARSAL.md), use the [Maintainer handoff](MAINTAINER_HANDOFF.md), then follow the dated [30-day transition plan](PROJECT_TRANSITION_PLAN.md). |
| **Check public project status** | Open the website [Project status & handoff](https://duecare-ai.com/project-status), then verify its receipts against [Publication readiness](PUBLICATION_READINESS.md). |
| **Publish the final Kaggle update** | Use the exact [copy-ready closeout post](kaggle_final_closeout_post.md), keeping its zero-result Kimi/Gemini and zero-human-rating boundaries unchanged. |
| **Transition after competition grading** | Follow the event-triggered [Post-Competition Hosting Transition](POST_COMPETITION_HOSTING_TRANSITION.md): keep Render live through grading, then move durable presentation to Pages and retain node deployment paths. |
| **Review closeout decisions** | Read the dated [11-item closeout receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md), then use the zero-item [Deferred work register](DEFERRED_WORK.md) only if a stated reopen condition is met. |
| **Review the proof path** | Start with the model-free [Publication readiness](PUBLICATION_READINESS.md) gate, then use [For Judges and Reviewers](FOR_PEER_REVIEW.md) and the active A-00 proof path. |
| **Plan a provider-backed run** | Keep calls at zero until the [provider-budget contract](PROVIDER_BUDGETING.md) has a frozen run ID, token/cash caps, and reviewed pricing. |
| **Inspect the frozen Kimi/Gemini campaign** | Read the [campaign readiness receipt](research/model_failure_run_readiness.md); it plans deterministic grading, a Gemini cross-family contextual judge, and a separately labeled Kimi self-judge, but currently has zero completed calls. |
| **Replicate the architecture in another domain** | Start with the [Capability-Gap Harness and Network Blueprint](architecture/capability_gap_blueprint.md), then define a new versioned domain pack and claim boundary. |
| **Install locally** | Use [Install](install.md) and [Local deployment](deployment_local.md). |
| **Embed in another system** | Use [Embedding guide](embedding_guide.md), [OpenAPI spec](openapi.yaml), and [Deployment enterprise](deployment_enterprise.md). |
| **Audit claims** | Use [Reproducibility](reproducibility.md), [Notebook guide](notebook_guide.md), and the validation commands linked there. |

## Sensitive Data Boundary

- Raw worker chats, case files, IDs, contact details, and private documents
  stay on the worker device, Kaggle session, trusted NGO machine, or
  tenant-owned deployment unless an authorized user creates a sanitized object.
- Sensitive PII is anonymized by the local workflow before anything is
  submitted to the public hub.
- The public server receives public-source facts, vetted pack metadata,
  anonymized aggregate signals, hash receipts, and consented contact metadata.
- The public server should not receive raw worker chats, phone numbers,
  addresses, passports, private documents, or personal case narratives.

Read the [threat model](considerations/THREAT_MODEL.md) and
[submission labeling policy](submission_labeling_policy.md) for the detailed
trust boundary.

---

*Built for the [Google Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
(Safety & Trust track), submitted 2026-05-18.*
