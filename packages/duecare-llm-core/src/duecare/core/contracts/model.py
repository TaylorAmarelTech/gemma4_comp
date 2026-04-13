"""Model protocol. Any LLM, local or remote, with a common interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)


@runtime_checkable
class Model(Protocol):
    """A language model. Any backend, any provider, any size.

    Adapters wrap concrete implementations (HF Transformers, llama.cpp,
    Ollama, OpenAI, Anthropic, Google Gemini, ...) behind this single
    protocol. Every other Duecare layer depends only on Model, never on
    a concrete adapter.
    """

    id: str
    display_name: str
    provider: str
    capabilities: set[Capability]
    context_length: int

    def generate(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        images: list[bytes] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs,
    ) -> GenerationResult: ...

    def embed(self, texts: list[str]) -> list[Embedding]: ...

    def healthcheck(self) -> ModelHealth: ...
