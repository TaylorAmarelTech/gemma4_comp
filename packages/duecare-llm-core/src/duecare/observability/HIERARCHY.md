# Hierarchy — Observability

## Breadcrumb

[Duecare] / [Observability]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards

## Children

- `duecare.observability.logging` — structlog configuration with a PII filter
- `duecare.observability.metrics` — JSON-line metrics sink for training / eval / inference
- `duecare.observability.audit` — Append-only audit trail for anonymization + training decisions

## Depends on

- `duecare.core`

## Depended on by

- (none)
