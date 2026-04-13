# Hierarchy — Adversarial Multi-Turn Task

## Breadcrumb

[Duecare] / [Tasks] / [Adversarial Multi-Turn Task]

## Parent

- `duecare.tasks` (`src/forge/tasks`)

## Siblings (same parent)

- `duecare.tasks.base` — Helpers shared by all tasks (fresh_task_result, etc.)
- `duecare.tasks.guardrails` — Response policy guardrails - refusal quality, citations, redirects
- `duecare.tasks.anonymization` — PII detection and redaction quality
- `duecare.tasks.classification` — Multi-label classification against the domain taxonomy
- `duecare.tasks.fact_extraction` — Structured fact extraction (entities, amounts, dates, citations)
- `duecare.tasks.grounding` — Evidence grounding - does the model cite verified domain evidence?
- `duecare.tasks.multimodal_classification` — Classify a document from a photograph using the model's vision head
- `duecare.tasks.tool_use` — Correct use of domain tools via native function calling
- `duecare.tasks.cross_lingual` — Guardrails in non-English languages (Tagalog, Nepali, Arabic, Bahasa, Spanish)

## Children

- (none — this is a leaf module)

## Depends on

- `duecare.core`
- `duecare.tasks.base`
- `duecare.agents.adversary`

## Depended on by

- (none)
