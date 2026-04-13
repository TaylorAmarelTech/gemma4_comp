# Hierarchy — Domains

## Breadcrumb

[Duecare] / [Domains]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.domains.pack` — FileDomainPack - a filesystem-backed DomainPack implementation
- `duecare.domains.loader` — Discovery + loading of domain packs from configs/duecare/domains/

## Depends on

- `duecare.core`

## Depended on by

- `duecare.agents.scout` — Profile the domain pack and score its completeness
