# Purpose — Models

> Pluggable adapters for every LLM backend, local or remote

## Long description

Every model backend (HF Transformers, llama.cpp, Unsloth, Ollama,
OpenAI-compatible, Anthropic, Google Gemini, HF Inference
Endpoints) lives here as a self-contained adapter. Each adapter
implements duecare.core.contracts.Model and registers itself under
a stable id in the global model_registry.

Adding a new backend is a new folder - not a refactor.

## Module id

`duecare.models`

## Kind

layer

## Status

`stub`

See `STATUS.md` for the TODO list and completion criteria.
