# Component — `duecare-llm-models`

> **Status: shipped.** 8 adapters, 22 tests passing, wheel built,
> installed from the wheel.

## What it is

Eight pluggable model adapters, all implementing the `duecare.core.Model`
protocol. Every backend that DueCare supports ships as its own folder
inside this package. Adding a new backend is a new folder — not a
refactor.

## Adapters shipped

| Id | Folder | Use case |
|---|---|---|
| `transformers` | `transformers_adapter/` | Any HF-hosted causal LM, 4-bit via bitsandbytes |
| `llama_cpp` | `llama_cpp_adapter/` | GGUF files via llama-cpp-python (primary runtime for the DueCare demo) |
| `unsloth` | `unsloth_adapter/` | Unsloth FastLanguageModel for fast inference + fine-tune |
| `ollama` | `ollama_adapter/` | Local Ollama server via stdlib urllib (no extra deps) |
| `openai_compatible` | `openai_compatible_adapter/` | Any provider with the OpenAI chat schema: OpenAI, DeepSeek, Together, Groq, Fireworks, OpenRouter, Mistral |
| `anthropic` | `anthropic_adapter/` | Claude Messages API |
| `google_gemini` | `google_gemini_adapter/` | Hosted Gemini via google-generativeai |
| `hf_inference_endpoint` | `hf_inference_endpoint_adapter/` | Any HF Inference Endpoint |

Every adapter is registered in `model_registry` on import. Tool Search
loads adapter schemas lazily, so you can `pip install duecare-llm-models`
without pulling in torch, transformers, unsloth, or llama-cpp-python.

## Install

```bash
# Base (no heavy ML deps)
pip install duecare-llm-models

# With specific backends (extras)
pip install 'duecare-llm-models[transformers]'  # + transformers + torch + bitsandbytes
pip install 'duecare-llm-models[unsloth]'        # + unsloth + peft + trl
pip install 'duecare-llm-models[llama-cpp]'      # + llama-cpp-python
pip install 'duecare-llm-models[ollama]'         # + ollama client
pip install 'duecare-llm-models[openai]'         # + openai client (optional; stdlib works too)
pip install 'duecare-llm-models[anthropic]'      # + anthropic client (optional)
pip install 'duecare-llm-models[google]'         # + google-generativeai
pip install 'duecare-llm-models[hf-endpoint]'    # + huggingface_hub
pip install 'duecare-llm-models[all]'            # everything
```

## Quick start

```python
from duecare.core import ChatMessage
from duecare.models.openai_compatible_adapter import OpenAICompatibleModel

m = OpenAICompatibleModel(
    model_id="gpt-4o-mini",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
)

result = m.generate([
    ChatMessage(role="user", content="Hello, DueCare."),
])

print(result.text)
print(f"Tokens: {result.tokens_used}, Latency: {result.latency_ms}ms")
```

Every adapter exposes the same `Model` protocol. You can swap one line
and target a different backend without changing any downstream code.

## Design decisions

### 1. Lazy imports of heavy dependencies

`transformers`, `unsloth`, `llama-cpp-python`, and `google-generativeai`
are imported **inside** the adapter's `_load()` method, not at module
import time. This means:

- `import duecare.models` takes milliseconds on any Python environment
- `TransformersModel` instances can be constructed without torch installed
- Trying to `generate()` without the extra installed raises a clean
  `ImportError` with install instructions

### 2. Stdlib for OpenAI-compatible + Ollama

Both use `urllib.request` from the stdlib, not the `openai` or `ollama`
Python clients. This means `duecare-llm-models` (base) has no runtime
dependencies beyond `duecare-llm-core` — you can hit OpenAI, DeepSeek,
Ollama, or any OpenAI-compatible provider from a bare install.

### 3. `ModelAdapterBase` is optional

Adapters can subclass `ModelAdapterBase` for shared retry/logging/
latency behavior, or they can implement the `Model` protocol
directly. The protocol is duck-typed — inheritance is a convenience,
not a requirement.

## Tests

22 tests, all passing:

- Registration: all 8 adapters register cleanly on package import
- Protocol conformance: every adapter is an `isinstance(m, Model)`
- Construction: every adapter can be instantiated without crashing
- Missing-extra errors: adapters raise `ImportError` with clear
  install instructions when their extra is missing
- Mocked generate(): `OpenAICompatibleModel.generate()` is exercised
  end-to-end with a mocked `urllib.request.urlopen` and asserts
  correct request body, response parsing, and tool-call extraction

## Status

- [x] 8 adapters implemented
- [x] 22 tests passing
- [x] Wheel built
- [x] Installed + smoke-tested
- [x] Registered in `configs/duecare/models.yaml` with 10 models (Gemma 4 E2B/E4B, GPT-OSS, Qwen, Llama, Mistral, DeepSeek, GPT-4o-mini, Claude Haiku, Gemini)

## License

MIT.
