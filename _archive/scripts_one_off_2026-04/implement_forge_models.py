#!/usr/bin/env python3
"""implement_forge_models.py - Write real implementations for duecare-llm-models.

Populates all 8 model adapters in duecare-llm-models. Adapters are:

  - TransformersModel   (HF Transformers, lazy-import)
  - LlamaCppModel       (llama-cpp-python, lazy-import, GGUF)
  - UnslothModel        (Unsloth FastLanguageModel, lazy-import)
  - OllamaModel         (local Ollama server, uses httpx or stdlib urllib)
  - OpenAICompatibleModel (real, usable with OpenAI/DeepSeek/Together/Groq)
  - AnthropicModel      (Anthropic Messages API)
  - GoogleGeminiModel   (google-generativeai, lazy-import)
  - HFInferenceEndpointModel (HF Inference Endpoints HTTP)

All adapters register themselves in duecare.models.model_registry and
raise clean NotImplementedError / ImportError messages when their
optional dependency isn't installed. The OpenAICompatibleModel is
*actually functional* using urllib from the stdlib, so it's usable
without installing any extras.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


FILES: dict[str, str] = {

    "packages/duecare-llm-models/src/forge/models/__init__.py": '''"""duecare.models - pluggable adapters for every LLM backend.

Every adapter implements duecare.core.contracts.Model and registers itself
under a stable id in model_registry. Importing this package triggers all
built-in adapters to self-register.
"""

from duecare.core.registry import Registry
from duecare.core.contracts import Model

# Global model-adapter registry.
model_registry: Registry = Registry(kind="model")

# Import all built-in adapter modules so they register on import.
# Each adapter handles its own optional-dependency imports internally
# (the adapter module may raise ImportError at call time, but not at
# import time).
from .base import base as _base_module  # noqa: F401,E402
from .transformers_adapter import adapter as _transformers_adapter  # noqa: F401,E402
from .llama_cpp_adapter import adapter as _llama_cpp_adapter  # noqa: F401,E402
from .unsloth_adapter import adapter as _unsloth_adapter  # noqa: F401,E402
from .ollama_adapter import adapter as _ollama_adapter  # noqa: F401,E402
from .openai_compatible_adapter import adapter as _openai_compatible_adapter  # noqa: F401,E402
from .anthropic_adapter import adapter as _anthropic_adapter  # noqa: F401,E402
from .google_gemini_adapter import adapter as _google_gemini_adapter  # noqa: F401,E402
from .hf_inference_endpoint_adapter import adapter as _hf_inference_endpoint_adapter  # noqa: F401,E402

from .base.base import ModelAdapterBase

__all__ = ["model_registry", "Model", "ModelAdapterBase"]
''',

    "packages/duecare-llm-models/src/forge/models/base/__init__.py": '''"""Optional ModelAdapterBase helper for adapter implementations."""

from .base import ModelAdapterBase, unsupported

__all__ = ["ModelAdapterBase", "unsupported"]
''',

    "packages/duecare-llm-models/src/forge/models/base/base.py": '''"""Base helpers for Model adapters.

Adapters may subclass ModelAdapterBase for shared behavior (logging,
retries, healthcheck defaults) but they are not required to - the Model
protocol is duck-typed.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import NoReturn

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.observability.logging import get_logger

log = get_logger("duecare.models")


def unsupported(feature: str, backend: str) -> NoReturn:
    """Raise a consistent NotImplementedError for missing adapter features."""
    raise NotImplementedError(
        f"The {backend!r} adapter does not support {feature!r}. "
        f"Pick a different adapter or file an issue."
    )


class ModelAdapterBase(ABC):
    """Optional base class for Model adapters. Not required - the Model
    protocol is duck-typed - but subclassing gives you:

      - a consistent `id` convention
      - an auto-populated `latency_ms` field on every GenerationResult
      - a default healthcheck that returns True after a first successful
        generate() call
    """

    id: str
    display_name: str
    provider: str
    capabilities: set[Capability]
    context_length: int

    def __init__(self) -> None:
        self._last_generate_ms: int = 0
        self._healthy: bool = False

    @abstractmethod
    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult: ...

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        images: list[bytes] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs,
    ) -> GenerationResult:
        start = time.perf_counter()
        try:
            result = self._generate_impl(
                messages=messages,
                tools=tools,
                images=images,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            self._healthy = True
        except Exception as e:
            log.error("generate failed for %s: %s", self.id, e)
            raise
        result.latency_ms = int((time.perf_counter() - start) * 1000)
        self._last_generate_ms = result.latency_ms
        return result

    def embed(self, texts: list[str]) -> list[Embedding]:
        unsupported("embed", self.provider)

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id,
            healthy=self._healthy,
            details={"last_generate_ms": self._last_generate_ms},
        )
''',

    "packages/duecare-llm-models/src/forge/models/transformers_adapter/__init__.py": '''"""HuggingFace Transformers adapter."""

from .adapter import TransformersModel

__all__ = ["TransformersModel"]
''',

    "packages/duecare-llm-models/src/forge/models/transformers_adapter/adapter.py": '''"""HuggingFace Transformers adapter.

Loads any HF-hosted causal LM with optional 4-bit quantization via
bitsandbytes. Widest model coverage of any adapter.

The `transformers` / `torch` / `bitsandbytes` dependencies are imported
lazily so that `duecare-llm-models` can be installed without pulling in
the full ML stack. If you try to call `generate()` without the extras
installed, you get a clean ImportError with install instructions.
"""

from __future__ import annotations

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("transformers")
class TransformersModel(ModelAdapterBase):
    """HuggingFace Transformers adapter. Lazy-imports torch + transformers."""

    provider = "transformers"

    def __init__(
        self,
        model_id: str,
        display_name: str | None = None,
        load_in_4bit: bool = True,
        device: str = "auto",
        capabilities: set[Capability] | None = None,
        context_length: int = 8192,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"transformers:{model_id}"
        self.display_name = display_name or model_id
        self.load_in_4bit = load_in_4bit
        self.device = device
        self.capabilities = capabilities or {Capability.TEXT, Capability.FINE_TUNABLE}
        self.context_length = context_length
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch  # noqa: F401
            from transformers import (  # type: ignore
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[transformers] is required for TransformersModel. "
                "Install with: pip install 'duecare-llm-models[transformers]'"
            ) from e

        kwargs: dict = {"device_map": self.device}
        if self.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig  # type: ignore
                kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype="bfloat16",
                    bnb_4bit_quant_type="nf4",
                )
            except ImportError:
                # bitsandbytes not installed - fall back to fp16
                pass

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        self._load()
        assert self._tokenizer is not None and self._model is not None

        # Build chat prompt via the tokenizer's chat template
        chat = [{"role": m.role, "content": m.content} for m in messages]
        prompt = self._tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)

        out = self._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        completion_ids = out[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(completion_ids, skip_special_tokens=True)

        return GenerationResult(
            text=text,
            finish_reason="stop",
            prompt_tokens=int(inputs["input_ids"].shape[1]),
            completion_tokens=int(completion_ids.shape[0]),
            tokens_used=int(inputs["input_ids"].shape[1] + completion_ids.shape[0]),
            model_id=self.id,
            model_version="",
        )

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id,
            healthy=self._model is not None,
            details={"loaded": self._model is not None},
        )
''',

    "packages/duecare-llm-models/src/forge/models/llama_cpp_adapter/__init__.py": '''"""llama.cpp GGUF adapter."""

from .adapter import LlamaCppModel

__all__ = ["LlamaCppModel"]
''',

    "packages/duecare-llm-models/src/forge/models/llama_cpp_adapter/adapter.py": '''"""llama.cpp adapter via llama-cpp-python.

Loads a GGUF file and runs inference on CPU or GPU. Primary runtime for
the fine-tuned Duecare model in the live demo.
"""

from __future__ import annotations

from pathlib import Path

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("llama_cpp")
class LlamaCppModel(ModelAdapterBase):
    """GGUF backend via llama-cpp-python. Lazy-imports the library."""

    provider = "llama_cpp"

    def __init__(
        self,
        model_path: Path | str,
        display_name: str | None = None,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        capabilities: set[Capability] | None = None,
    ) -> None:
        super().__init__()
        self.model_path = Path(model_path)
        self.id = f"llama_cpp:{self.model_path.stem}"
        self.display_name = display_name or self.model_path.stem
        self.context_length = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.capabilities = capabilities or {Capability.TEXT, Capability.EMBEDDINGS}
        self._llm = None

    def _load(self) -> None:
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[llama-cpp] is required for LlamaCppModel. "
                "Install with: pip install 'duecare-llm-models[llama-cpp]'"
            ) from e

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"GGUF model file not found: {self.model_path}"
            )

        self._llm = Llama(
            model_path=str(self.model_path),
            n_ctx=self.context_length,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        self._load()
        assert self._llm is not None

        chat = [{"role": m.role, "content": m.content} for m in messages]
        response = self._llm.create_chat_completion(
            messages=chat,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response["choices"][0]
        usage = response.get("usage", {})

        return GenerationResult(
            text=choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tokens_used=usage.get("total_tokens", 0),
            model_id=self.id,
            raw=response,
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        self._load()
        assert self._llm is not None
        results: list[Embedding] = []
        for text in texts:
            emb_data = self._llm.create_embedding(text)["data"][0]["embedding"]
            results.append(
                Embedding(
                    text=text,
                    vector=list(emb_data),
                    dimension=len(emb_data),
                    model_id=self.id,
                )
            )
        return results

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id,
            healthy=self.model_path.exists(),
            details={"path": str(self.model_path), "loaded": self._llm is not None},
        )
''',

    "packages/duecare-llm-models/src/forge/models/unsloth_adapter/__init__.py": '''"""Unsloth adapter."""

from .adapter import UnslothModel

__all__ = ["UnslothModel"]
''',

    "packages/duecare-llm-models/src/forge/models/unsloth_adapter/adapter.py": '''"""Unsloth adapter - fast local inference + fine-tune.

Wraps Unsloth's FastLanguageModel. Used by the Trainer agent for Gemma 4
LoRA fine-tunes.
"""

from __future__ import annotations

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("unsloth")
class UnslothModel(ModelAdapterBase):
    """Unsloth FastLanguageModel wrapper. Lazy-imports unsloth + torch."""

    provider = "unsloth"

    def __init__(
        self,
        model_id: str,
        display_name: str | None = None,
        max_seq_length: int = 4096,
        load_in_4bit: bool = True,
    ) -> None:
        super().__init__()
        self.id = f"unsloth:{model_id}"
        self.display_name = display_name or model_id
        self.model_id = model_id
        self.max_seq_length = max_seq_length
        self.load_in_4bit = load_in_4bit
        self.context_length = max_seq_length
        self.capabilities = {Capability.TEXT, Capability.FINE_TUNABLE}
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from unsloth import FastLanguageModel  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[unsloth] is required for UnslothModel. "
                "Install with: pip install 'duecare-llm-models[unsloth]'"
            ) from e

        self._model, self._tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.model_id,
            max_seq_length=self.max_seq_length,
            load_in_4bit=self.load_in_4bit,
        )
        FastLanguageModel.for_inference(self._model)

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        self._load()
        assert self._tokenizer is not None and self._model is not None

        chat = [{"role": m.role, "content": m.content} for m in messages]
        prompt = self._tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        out = self._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        completion_ids = out[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(completion_ids, skip_special_tokens=True)

        return GenerationResult(
            text=text,
            finish_reason="stop",
            prompt_tokens=int(inputs["input_ids"].shape[1]),
            completion_tokens=int(completion_ids.shape[0]),
            tokens_used=int(inputs["input_ids"].shape[1] + completion_ids.shape[0]),
            model_id=self.id,
        )

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id, healthy=self._model is not None
        )
''',

    "packages/duecare-llm-models/src/forge/models/ollama_adapter/__init__.py": '''"""Ollama adapter."""

from .adapter import OllamaModel

__all__ = ["OllamaModel"]
''',

    "packages/duecare-llm-models/src/forge/models/ollama_adapter/adapter.py": '''"""Ollama adapter - local Ollama server via HTTP API.

Uses stdlib urllib so there's no hard dependency on httpx or the ollama
Python client.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("ollama")
class OllamaModel(ModelAdapterBase):
    """Talks to a local Ollama server at http://localhost:11434 by default."""

    provider = "ollama"

    def __init__(
        self,
        model_id: str,
        display_name: str | None = None,
        host: str = "http://localhost:11434",
        timeout: float = 300.0,
    ) -> None:
        super().__init__()
        self.id = f"ollama:{model_id}"
        self.display_name = display_name or model_id
        self.model_id = model_id
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.context_length = 8192
        self.capabilities = {
            Capability.TEXT,
            Capability.EMBEDDINGS,
            Capability.FUNCTION_CALLING,
        }

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self.host}{path}"
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if tools:
            body["tools"] = [t.to_openai() for t in tools]

        response = self._post("/api/chat", body)
        message = response.get("message", {})

        return GenerationResult(
            text=message.get("content", ""),
            finish_reason=response.get("done_reason", "stop"),
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
            tokens_used=response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            model_id=self.id,
            raw=response,
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        results: list[Embedding] = []
        for text in texts:
            resp = self._post("/api/embeddings", {"model": self.model_id, "prompt": text})
            vec = resp.get("embedding", [])
            results.append(
                Embedding(
                    text=text,
                    vector=list(vec),
                    dimension=len(vec),
                    model_id=self.id,
                )
            )
        return results

    def healthcheck(self) -> ModelHealth:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                _ = resp.read()
            return ModelHealth(
                model_id=self.id, healthy=True, details={"host": self.host}
            )
        except Exception as e:
            return ModelHealth(
                model_id=self.id,
                healthy=False,
                details={"host": self.host, "error": str(e)},
            )
''',

    "packages/duecare-llm-models/src/forge/models/openai_compatible_adapter/__init__.py": '''"""OpenAI-compatible adapter (OpenAI, DeepSeek, Together, Groq, Fireworks, OpenRouter, ...)."""

from .adapter import OpenAICompatibleModel

__all__ = ["OpenAICompatibleModel"]
''',

    "packages/duecare-llm-models/src/forge/models/openai_compatible_adapter/adapter.py": '''"""OpenAI-compatible adapter.

Covers OpenAI, DeepSeek, Together, Groq, Fireworks, OpenRouter, Mistral
(via la-platforme), and any other provider that exposes the OpenAI chat
completions API. Uses stdlib urllib so no hard dependency on openai or
httpx.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
    ToolCall,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("openai_compatible")
class OpenAICompatibleModel(ModelAdapterBase):
    """OpenAI-compatible adapter.

    Works with any provider that exposes POST /v1/chat/completions with
    the standard OpenAI schema. Set `base_url` and `api_key_env` per
    provider.
    """

    provider = "openai_compatible"

    def __init__(
        self,
        model_id: str,
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        display_name: str | None = None,
        capabilities: set[Capability] | None = None,
        context_length: int = 128_000,
        timeout: float = 120.0,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.id = f"openai_compat:{self.base_url}:{model_id}"
        self.display_name = display_name or model_id
        self.capabilities = capabilities or {
            Capability.TEXT, Capability.FUNCTION_CALLING
        }
        self.context_length = context_length
        self.timeout = timeout

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env!r} is not set. "
                f"Set it to your API key for {self.display_name}."
            )
        return key

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key()}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTP {e.code} from {url}: {body_text[:500]}"
            ) from e

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = [t.to_openai() for t in tools]
            body["tool_choice"] = kwargs.get("tool_choice", "auto")

        response = self._post("/chat/completions", body)

        choice = response["choices"][0]
        message = choice.get("message", {})
        text = message.get("content") or ""

        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    name=fn.get("name", ""),
                    arguments=args,
                    call_id=tc.get("id"),
                )
            )

        usage = response.get("usage", {})
        return GenerationResult(
            text=text,
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tokens_used=usage.get("total_tokens", 0),
            tool_calls=tool_calls,
            model_id=self.id,
            model_version=response.get("model", ""),
            raw=response,
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        response = self._post(
            "/embeddings",
            {"model": self.model_id, "input": texts},
        )
        return [
            Embedding(
                text=text,
                vector=list(item["embedding"]),
                dimension=len(item["embedding"]),
                model_id=self.id,
            )
            for text, item in zip(texts, response.get("data", []))
        ]

    def healthcheck(self) -> ModelHealth:
        try:
            _ = self._api_key()
            return ModelHealth(
                model_id=self.id,
                healthy=True,
                details={"base_url": self.base_url, "api_key_set": True},
            )
        except RuntimeError as e:
            return ModelHealth(
                model_id=self.id,
                healthy=False,
                details={"error": str(e)},
            )
''',

    "packages/duecare-llm-models/src/forge/models/anthropic_adapter/__init__.py": '''"""Anthropic (Claude) adapter."""

from .adapter import AnthropicModel

__all__ = ["AnthropicModel"]
''',

    "packages/duecare-llm-models/src/forge/models/anthropic_adapter/adapter.py": '''"""Anthropic (Claude) adapter.

Uses the native Anthropic Messages API (not the OpenAI-compatible proxy)
via stdlib urllib.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
    ToolCall,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("anthropic")
class AnthropicModel(ModelAdapterBase):
    """Native Claude Messages API adapter."""

    provider = "anthropic"

    def __init__(
        self,
        model_id: str,
        api_key_env: str = "ANTHROPIC_API_KEY",
        display_name: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"anthropic:{model_id}"
        self.display_name = display_name or model_id
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.base_url = "https://api.anthropic.com/v1"
        self.context_length = 200_000
        self.capabilities = {
            Capability.TEXT,
            Capability.VISION,
            Capability.LONG_CONTEXT,
            Capability.FUNCTION_CALLING,
        }

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env!r} is not set."
            )
        return key

    def _post(self, path: str, body: dict) -> dict:
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key(),
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTP {e.code} from {self.base_url}{path}: {body_text[:500]}"
            ) from e

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        # Anthropic separates system from messages
        system_parts = [m.content for m in messages if m.role == "system"]
        user_assistant = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": user_assistant,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_parts:
            body["system"] = "\\n\\n".join(system_parts)
        if tools:
            body["tools"] = [t.to_anthropic() for t in tools]

        response = self._post("/messages", body)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                        call_id=block.get("id"),
                    )
                )

        usage = response.get("usage", {})
        return GenerationResult(
            text="".join(text_parts),
            finish_reason=response.get("stop_reason", "end_turn"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            tool_calls=tool_calls,
            model_id=self.id,
            model_version=response.get("model", ""),
            raw=response,
        )

    def healthcheck(self) -> ModelHealth:
        try:
            _ = self._api_key()
            return ModelHealth(
                model_id=self.id,
                healthy=True,
                details={"base_url": self.base_url, "api_key_set": True},
            )
        except RuntimeError as e:
            return ModelHealth(
                model_id=self.id, healthy=False, details={"error": str(e)}
            )
''',

    "packages/duecare-llm-models/src/forge/models/google_gemini_adapter/__init__.py": '''"""Google Gemini API adapter."""

from .adapter import GoogleGeminiModel

__all__ = ["GoogleGeminiModel"]
''',

    "packages/duecare-llm-models/src/forge/models/google_gemini_adapter/adapter.py": '''"""Google Gemini API adapter.

Uses google-generativeai for hosted Gemini models. Separate from the
Gemma local adapters (those go through transformers / unsloth / llama.cpp).
"""

from __future__ import annotations

import os

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("google_gemini")
class GoogleGeminiModel(ModelAdapterBase):
    """Hosted Gemini API via google-generativeai. Lazy-imports the library."""

    provider = "google_gemini"

    def __init__(
        self,
        model_id: str,
        api_key_env: str = "GOOGLE_API_KEY",
        display_name: str | None = None,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"google_gemini:{model_id}"
        self.display_name = display_name or model_id
        self.api_key_env = api_key_env
        self.context_length = 1_000_000
        self.capabilities = {
            Capability.TEXT,
            Capability.VISION,
            Capability.AUDIO,
            Capability.LONG_CONTEXT,
            Capability.FUNCTION_CALLING,
            Capability.EMBEDDINGS,
        }
        self._client = None

    def _load(self):
        if self._client is not None:
            return
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[google] is required for GoogleGeminiModel. "
                "Install with: pip install 'duecare-llm-models[google]'"
            ) from e

        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env!r} is not set."
            )
        genai.configure(api_key=key)
        self._client = genai.GenerativeModel(self.model_id)

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        self._load()
        assert self._client is not None

        # Combine messages into a single prompt since the basic SDK
        # is text-in / text-out
        prompt_parts: list[str] = []
        for m in messages:
            prompt_parts.append(f"{m.role}: {m.content}")
        prompt = "\\n".join(prompt_parts)

        response = self._client.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        text = response.text if hasattr(response, "text") else ""

        return GenerationResult(
            text=text,
            finish_reason="stop",
            model_id=self.id,
        )

    def healthcheck(self) -> ModelHealth:
        try:
            key = os.environ.get(self.api_key_env)
            return ModelHealth(
                model_id=self.id,
                healthy=bool(key),
                details={"api_key_set": bool(key)},
            )
        except Exception as e:
            return ModelHealth(
                model_id=self.id, healthy=False, details={"error": str(e)}
            )
''',

    "packages/duecare-llm-models/src/forge/models/hf_inference_endpoint_adapter/__init__.py": '''"""HuggingFace Inference Endpoints adapter."""

from .adapter import HFInferenceEndpointModel

__all__ = ["HFInferenceEndpointModel"]
''',

    "packages/duecare-llm-models/src/forge/models/hf_inference_endpoint_adapter/adapter.py": '''"""HuggingFace Inference Endpoints adapter.

Calls any HF-hosted endpoint via stdlib urllib. Useful for arbitrary
community models without local download.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("hf_inference_endpoint")
class HFInferenceEndpointModel(ModelAdapterBase):
    """HuggingFace Inference Endpoint adapter."""

    provider = "hf_inference_endpoint"

    def __init__(
        self,
        endpoint_url: str,
        model_id: str,
        api_key_env: str = "HUGGINGFACE_TOKEN",
        display_name: str | None = None,
        capabilities: set[Capability] | None = None,
        timeout: float = 120.0,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"hf_endpoint:{model_id}"
        self.display_name = display_name or model_id
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.context_length = 8192
        self.capabilities = capabilities or {Capability.TEXT}

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env!r} is not set."
            )
        return key

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        prompt = "\\n".join(f"{m.role}: {m.content}" for m in messages)
        body = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature if temperature > 0 else 0.01,
                "return_full_text": False,
            },
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key()}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTP {e.code} from {self.endpoint_url}: {body_text[:500]}"
            ) from e

        # HF inference API returns a list of {"generated_text": "..."}
        if isinstance(response, list) and response:
            text = response[0].get("generated_text", "")
        else:
            text = response.get("generated_text", "") if isinstance(response, dict) else ""

        return GenerationResult(
            text=text,
            finish_reason="stop",
            model_id=self.id,
            raw={"response": response} if not isinstance(response, dict) else response,
        )

    def healthcheck(self) -> ModelHealth:
        try:
            _ = self._api_key()
            return ModelHealth(
                model_id=self.id, healthy=True,
                details={"endpoint_url": self.endpoint_url},
            )
        except RuntimeError as e:
            return ModelHealth(
                model_id=self.id, healthy=False, details={"error": str(e)}
            )
''',
}


def main() -> int:
    created = 0
    updated = 0
    for rel, content in FILES.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        if existed:
            updated += 1
        else:
            created += 1
        print(f"{'UPDATE' if existed else 'CREATE'} {rel}")
    print()
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Total:   {len(FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
