# User paths

DueCare has one component ecosystem, not six separate products. Each path below
uses the same core ideas: sensitive material is handled in a local or trusted
deployment, Gemma 4 and the harness create reviewable evidence, and only
sanitized fact objects, evidence edges, benchmark rows, aggregate signals, or
pack updates are shared outward.

Use this page as the public chooser. The detailed component vocabulary lives in
[Canonical use cases and components](canonical_use_cases_and_components.md).

## Pick your path

| User path | What you are trying to do | Start here |
|---|---|---|
| I am on a platform safety team | Screen recruitment posts, ads, profiles, and messages before workers are harmed. | [Platform safety](scenarios/enterprise_pilot.md) |
| I am an NGO, caseworker, regulator, or legal-aid reviewer | Review cases, documents, messages, referrals, and corridor evidence with a human decision maker in control. | [Caseworker workflow](scenarios/caseworker_workflow.md) |
| I am a migrant worker or prospective worker | Check suspicious offers, contracts, fees, document requests, threats, or recruiter messages privately. | [Worker self-help](scenarios/worker-self-help.md) |
| I am a researcher, evaluator, or auditor | Reproduce model behavior, inspect evidence traces, compare safety interventions, and audit claims from source artifacts. | [Researcher analysis](scenarios/researcher-analysis.md) |
| I am sharing anonymized knowledge | Turn reviewed local evidence into sanitized objects that can improve shared packs without exposing workers. | [Information sharing architecture](information_sharing_architecture.md) |
| I am a developer or integration partner | Install packages, call APIs, embed components, or connect DueCare to another review workflow. | [Embedding guide](embedding_guide.md) |

## What stays local

Raw worker chats, case files, IDs, contact details, screenshots, private
documents, secrets, and volatile legal claims stay inside the worker device,
Kaggle session, NGO machine, regulator workstation, or tenant-owned deployment
unless an authorized user deliberately exports or submits a sanitized object.

## What can be shared

Reviewed deployments can share safe objects: sanitized fact objects, evidence
edges, risk-signal counts, benchmark rows, public-source proposals, hash
receipts, and knowledge-pack updates. The public hub and GitHub Pages are for
coordination, onboarding, documentation, and versioned knowledge. They are not a
raw case-file warehouse.

## How the paths work together

1. A local node reviews sensitive material with Gemma 4, deterministic rules,
   retrieval, tools, and activity traces.
2. A reviewer approves the useful facts, citations, graph edges, or benchmark
   rows.
3. The local anonymization workflow removes PII and private narrative detail.
4. The shared hub accepts only sanitized objects, public-source updates, hash
   receipts, aggregate signals, or vetted metadata.
5. Approved updates return to other nodes as versioned packs, examples,
   benchmark rows, or safer default rules.

That network effect is the point: many local deployments can see recruitment
abuse and trafficking patterns together without centralizing the raw worker
material that created those signals.
