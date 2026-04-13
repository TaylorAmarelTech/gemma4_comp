# Hierarchy — Historian Agent

## Breadcrumb

[Duecare] / [Agents] / [Historian Agent]

## Parent

- `duecare.agents` (`src/forge/agents`)

## Siblings (same parent)

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
- `duecare.agents.coordinator` — Orchestrates the 12-agent swarm via a workflow DAG

## Children

- (none — this is a leaf module)

## Depends on

- `duecare.core`
- `duecare.agents.base`
- `duecare.publishing.reports`

## Depended on by

- (none)
