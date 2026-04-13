"""OpenAI-compatible adapter.

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
