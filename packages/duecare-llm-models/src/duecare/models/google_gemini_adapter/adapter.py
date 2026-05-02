"""Google Gemini API adapter.

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

    def _load(self) -> None:
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
        prompt = "\n".join(prompt_parts)

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
