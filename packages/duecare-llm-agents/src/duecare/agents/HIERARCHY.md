# Hierarchy — Agents

## Breadcrumb

[Duecare] / [Agents]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.agents.base` — Helpers shared by all agents
- `duecare.agents.scout` — Profile the domain pack and score its completeness
- `duecare.agents.data_generator` — Synthesize probes + graded response examples using a strong teacher model
- `duecare.agents.adversary` — Mutate probes through 631 prompt-injection mutators + 126 attack chains
- `duecare.agents.anonymizer` — Hard PII gate - no raw PII passes this point
- `duecare.agents.curator` — Dedupe, stratify, split into train/val/test
- `duecare.agents.judge` — Score model outputs against the domain rubric in 4 modes
- `duecare.agents.validator` — Red-team the trained model, issue the no-harm certificate
- `duecare.agents.curriculum_designer` — Cluster failures, plan the next training iteration
- `duecare.agents.trainer` — Run Unsloth + LoRA fine-tune on the curated dataset
- `duecare.agents.exporter` — Convert, quantize, publish to HF Hub + Kaggle Models
- `duecare.agents.historian` — Narrative assembly - write the run report and the Kaggle notebook
- `duecare.agents.coordinator` — Orchestrates the 12-agent swarm via a workflow DAG

## Depends on

- `duecare.core`
- `duecare.tasks`

## Depended on by

- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.workflows.runner` — Executes a Workflow by walking the agent DAG
