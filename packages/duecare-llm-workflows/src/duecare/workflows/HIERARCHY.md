# Hierarchy — Workflows

## Breadcrumb

[Duecare] / [Workflows]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.workflows.loader` — YAML -> Workflow Pydantic model
- `duecare.workflows.runner` — Executes a Workflow by walking the agent DAG
- `duecare.workflows.dag` — Topological sort, dependency resolution, parallelism

## Depends on

- `duecare.core`
- `duecare.agents`

## Depended on by

- `duecare.agents.coordinator` — Orchestrates the 12-agent swarm via a workflow DAG
