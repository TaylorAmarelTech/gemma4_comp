# Hierarchy — Tasks

## Breadcrumb

[Duecare] / [Tasks]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.tasks.base` — Helpers shared by all tasks (fresh_task_result, etc.)
- `duecare.tasks.guardrails` — Response policy guardrails - refusal quality, citations, redirects
- `duecare.tasks.anonymization` — PII detection and redaction quality
- `duecare.tasks.classification` — Multi-label classification against the domain taxonomy
- `duecare.tasks.fact_extraction` — Structured fact extraction (entities, amounts, dates, citations)
- `duecare.tasks.grounding` — Evidence grounding - does the model cite verified domain evidence?
- `duecare.tasks.multimodal_classification` — Classify a document from a photograph using the model's vision head
- `duecare.tasks.adversarial_multi_turn` — Resistance to Crescendo / FITD / Role Chain multi-turn attacks
- `duecare.tasks.tool_use` — Correct use of domain tools via native function calling
- `duecare.tasks.cross_lingual` — Guardrails in non-English languages (Tagalog, Nepali, Arabic, Bahasa, Spanish)

## Depends on

- `duecare.core`

## Depended on by

- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.agents.judge` — Score model outputs against the domain rubric in 4 modes
