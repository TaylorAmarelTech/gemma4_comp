"""Base helpers for Model adapters.

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
