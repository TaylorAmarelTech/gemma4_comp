# Hierarchy — Unsloth Adapter

## Breadcrumb

[Duecare] / [Models] / [Unsloth Adapter]

## Parent

- `duecare.models` (`src/forge/models`)

## Siblings (same parent)

- `duecare.models.base` — Optional ModelAdapterBase for shared adapter behavior
- `duecare.models.transformers_adapter` — HuggingFace Transformers backend (4-bit via bitsandbytes)
- `duecare.models.llama_cpp_adapter` — GGUF backend via llama-cpp-python for on-device inference
- `duecare.models.ollama_adapter` — Local Ollama server backend via its HTTP API
- `duecare.models.openai_compatible_adapter` — Any provider exposing the OpenAI Chat Completions schema
- `duecare.models.anthropic_adapter` — Native Claude Messages API adapter
- `duecare.models.google_gemini_adapter` — Google Gemini API adapter (separate from Gemma local adapters)
- `duecare.models.hf_inference_endpoint_adapter` — HuggingFace Inference Endpoints backend

## Children

- (none — this is a leaf module)

## Depends on

- `duecare.core`
- `duecare.models.base`

## Depended on by

- `duecare.agents.trainer` — Run Unsloth + LoRA fine-tune on the curated dataset
