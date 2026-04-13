# Hierarchy — Models

## Breadcrumb

[Duecare] / [Models]

## Parent

- `duecare` (`src/forge`)

## Siblings (same parent)

- `duecare.core` — Contracts, schemas, enums, registries - imported by every other layer
- `duecare.domains` — Pluggable domain packs (taxonomy + evidence + rubric)
- `duecare.tasks` — Capability tests runnable against any (Model, DomainPack) pair
- `duecare.agents` — The 12-agent Duecare swarm
- `duecare.workflows` — DAG orchestration - workflow YAML loader, runner, scheduler
- `duecare.publishing` — HF Hub, Kaggle Datasets + Models, reports, model cards
- `duecare.observability` — Logging + metrics + audit trails

## Children

- `duecare.models.base` — Optional ModelAdapterBase for shared adapter behavior
- `duecare.models.transformers_adapter` — HuggingFace Transformers backend (4-bit via bitsandbytes)
- `duecare.models.llama_cpp_adapter` — GGUF backend via llama-cpp-python for on-device inference
- `duecare.models.unsloth_adapter` — Unsloth FastLanguageModel backend for fine-tuning and fast inference
- `duecare.models.ollama_adapter` — Local Ollama server backend via its HTTP API
- `duecare.models.openai_compatible_adapter` — Any provider exposing the OpenAI Chat Completions schema
- `duecare.models.anthropic_adapter` — Native Claude Messages API adapter
- `duecare.models.google_gemini_adapter` — Google Gemini API adapter (separate from Gemma local adapters)
- `duecare.models.hf_inference_endpoint_adapter` — HuggingFace Inference Endpoints backend

## Depends on

- `duecare.core`

## Depended on by

- (none)
