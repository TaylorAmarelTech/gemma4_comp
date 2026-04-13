# Hierarchy — Publishing

## Breadcrumb

[Duecare] / [Publishing]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.publishing.hf_hub` — HuggingFace Hub upload for weights + datasets
- `duecare.publishing.kaggle` — Kaggle Datasets + Models + Kernels publisher
- `duecare.publishing.reports` — Markdown report generator used by the Historian agent
- `duecare.publishing.model_card` — Generate HF Hub-compatible model cards from run metrics

## Depends on

- `duecare.core`

## Depended on by

- `duecare.agents.exporter` — Convert, quantize, publish to HF Hub + Kaggle Models
