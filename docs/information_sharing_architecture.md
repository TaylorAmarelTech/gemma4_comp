# Information Sharing Architecture

DueCare is built around a simple rule: sensitive material is processed where it
is owned, while only reviewed and anonymized intelligence can move between
deployments.

## Purpose

The architecture lets many local nodes improve shared knowledge without
centralizing raw worker case data. A node can be a Kaggle session, an NGO office
machine, a platform safety deployment, a regulator workstation, a mobile client,
or a researcher environment. Each node can run Gemma 4, harness layers, document
review, graph extraction, search safety, and anonymization locally.

When a user chooses to share, DueCare converts reviewed local outputs into
portable objects: sanitized facts, evidence edges, public-source proposals,
aggregate signals, hash receipts, benchmark rows, or pack updates.

## Local Node Responsibilities

| Responsibility | What Happens Locally |
|---|---|
| Review source material | The node handles messages, documents, screenshots, contracts, receipts, IDs, and case notes. |
| Generate drafts | Gemma 4 and the safety guidance layer produce summaries, questions, citations, risk notes, and graph edges. |
| Verify evidence | Reviewers inspect citations, evidence quotes, uncertainty, and graph links before promotion. |
| Anonymize | The local workflow redacts PII and converts approved outputs into sanitized objects. |
| Decide consent | The submitting user or organization chooses what can be shared, attributed, aggregated, or kept private. |

## Shared Object Types

| Object | Use |
|---|---|
| `CasePatternObservation` | Sanitized pattern such as fee pressure, document control, threats, false promises, or repeated recruiter language. |
| `EvidenceEdge` | Reviewed relationship between entities, documents, payments, events, locations, or journey stages. |
| `RegulationUpdate` | Public-source legal or policy update with source URL, jurisdiction, effective date, and review status. |
| `CorridorFeeRecord` | Public or vetted fee rule for a corridor, sector, visa path, or recruitment stage. |
| `ContactMetadataUpdate` | Consented or public-source update to contact metadata, never raw private contact logs. |
| `BenchmarkRow` | Anonymized or synthetic prompt/evidence row for reproducible model and harness evaluation. |
| `PackProposal` | Proposed change to a versioned knowledge pack, with provenance and curator notes. |

## Hub Responsibilities

The public hub coordinates shared intelligence. It should store public-source
facts, vetted pack metadata, anonymized aggregate signals, hash receipts,
curation status, and consented contact metadata.

It should not store raw worker chats, phone numbers, addresses, passports,
private documents, unredacted screenshots, or personal case narratives.

| Hub Function | Purpose |
|---|---|
| Intake validation | Reject payloads that look like raw PII or private case narratives. |
| Review queue | Hold sanitized proposals until a curator or trusted reviewer approves them. |
| Pack registry | Publish versioned knowledge packs that local nodes can pull and verify. |
| Audit receipts | Record hashes, timestamps, source references, and review state. |
| Aggregate signals | Show corridor, sector, and pattern-level trends only after threshold and consent checks. |
| Evaluation artifacts | Publish benchmark rows, scorecards, and reproducibility metadata. |

## Sharing Flow

| Step | Description |
|---|---|
| 1. Local review | A local node reviews source material and builds drafts, graph edges, citations, and risk notes. |
| 2. Human approval | A reviewer decides which outputs are accurate enough to promote. |
| 3. Local anonymization | PII and private narrative details are removed before anything leaves the node. |
| 4. Submission | The node submits a sanitized object, aggregate signal, public-source proposal, or hash receipt. |
| 5. Server validation | The hub rejects raw PII and routes accepted objects into a review queue. |
| 6. Curation | Curators approve, reject, merge, or request more evidence. |
| 7. Pack update | Approved objects become knowledge-pack updates, benchmark rows, or aggregate trend data. |
| 8. Reuse | Other nodes pull the updated packs and benefit from the improved shared intelligence. |

## User Mapping

| User Path | Information Sharing Role |
|---|---|
| Platform safety | Shares anonymized abuse-pattern signals and public policy updates from review queues. |
| NGO & regulator | Shares reviewed, sanitized case patterns and corridor evidence without uploading raw case files. |
| Individual worker / mobile | Shares only worker-approved notes, intake drafts, or anonymized signals. |
| Researcher | Shares reproducible benchmark artifacts, source audits, and evaluation metadata. |
| Anonymized knowledge sharing | Operates the redaction, consent, curation, and pack-proposal path. |
| Developer / integration partner | Embeds the same object schemas and validation boundaries into external systems. |

## Related Pages

- [Canonical use cases and components](canonical_use_cases_and_components.md)
- [Anonymization policy](anonymization_policy.md)
- [Submission labeling policy](submission_labeling_policy.md)
- [Knowledge object taxonomy](adr/007-knowledge-object-taxonomy.md)
- [Knowledge module schema](knowledge_module_schema.md)
