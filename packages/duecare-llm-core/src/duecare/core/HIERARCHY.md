# Hierarchy — Core

## Breadcrumb

[Duecare] / [Core]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.core.contracts` — Typing protocols for Model, DomainPack, Task, Agent, Coordinator
- `duecare.core.schemas` — Shared Pydantic models for cross-layer data flow
- `duecare.core.enums` — Canonical enums: Capability, AgentRole, TaskStatus, Grade, Severity
- `duecare.core.registry` — Generic plugin registry used by models, domains, agents, tasks
- `duecare.core.provenance` — run_id, git_sha, config_hash - reproducibility helpers

## Depends on

- (none)

## Depended on by

- `duecare.models` — Pluggable adapters for every LLM backend, local or remote
- `duecare.models.base` — Optional ModelAdapterBase for shared adapter behavior
- `duecare.models.transformers_adapter` — HuggingFace Transformers backend (4-bit via bitsandbytes)
- `duecare.models.llama_cpp_adapter` — GGUF backend via llama-cpp-python for on-device inference
- `duecare.models.unsloth_adapter` — Unsloth FastLanguageModel backend for fine-tuning and fast inference
- `duecare.models.ollama_adapter` — Local Ollama server backend via its HTTP API
- `duecare.models.openai_compatible_adapter` — Any provider exposing the OpenAI Chat Completions schema
- `duecare.models.anthropic_adapter` — Native Claude Messages API adapter
- `duecare.models.google_gemini_adapter` — Google Gemini API adapter (separate from Gemma local adapters)
- `duecare.models.hf_inference_endpoint_adapter` — HuggingFace Inference Endpoints backend
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.domains.pack` — FileDomainPack - a filesystem-backed DomainPack implementation
- `duecare.domains.loader` — Discovery + loading of domain packs from configs/duecare/domains/
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
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
- `duecare.agents` — The 12-agent Duecare swarm
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
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.workflows.loader` — YAML -> Workflow Pydantic model
- `duecare.workflows.runner` — Executes a Workflow by walking the agent DAG
- `duecare.workflows.dag` — Topological sort, dependency resolution, parallelism
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.publishing.hf_hub` — HuggingFace Hub upload for weights + datasets
- `duecare.publishing.kaggle` — Kaggle Datasets + Models + Kernels publisher
- `duecare.publishing.reports` — Markdown report generator used by the Historian agent
- `duecare.publishing.model_card` — Generate HF Hub-compatible model cards from run metrics
- `duecare.observability` — Logging + metrics + audit trails
- `duecare.observability.logging` — structlog configuration with a PII filter
- `duecare.observability.metrics` — JSON-line metrics sink for training / eval / inference
- `duecare.observability.audit` — Append-only audit trail for anonymization + training decisions
