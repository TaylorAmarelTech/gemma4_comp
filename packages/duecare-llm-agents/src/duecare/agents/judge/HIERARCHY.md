# Hierarchy — Judge Agent

## Breadcrumb

[Duecare] / [Agents] / [Judge Agent]

## Parent

- `duecare.agents` (`src/forge/agents`)

## Siblings (same parent)

- `duecare.agents.base` — Helpers shared by all agents
- `duecare.agents.scout` — Profile the domain pack and score its completeness
- `duecare.agents.data_generator` — Synthesize probes + graded response examples using a strong teacher model
- `duecare.agents.adversary` — Mutate probes through 631 prompt-injection mutators + 126 attack chains
- `duecare.agents.anonymizer` — Hard PII gate - no raw PII passes this point
- `duecare.agents.curator` — Dedupe, stratify, split into train/val/test
- `duecare.agents.validator` — Red-team the trained model, issue the no-harm certificate
- `duecare.agents.curriculum_designer` — Cluster failures, plan the next training iteration
- `duecare.agents.trainer` — Run Unsloth + LoRA fine-tune on the curated dataset
- `duecare.agents.exporter` — Convert, quantize, publish to HF Hub + Kaggle Models
- `duecare.agents.historian` — Narrative assembly - write the run report and the Kaggle notebook
- `duecare.agents.coordinator` — Orchestrates the 12-agent swarm via a workflow DAG

## Children

- (none — this is a leaf module)

## Depends on

- `duecare.core`
- `duecare.agents.base`
- `duecare.tasks`

## Depended on by

- `duecare.agents.data_generator` — Synthesize probes + graded response examples using a strong teacher model
