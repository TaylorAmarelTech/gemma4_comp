"""Anthropic (Claude) adapter.

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
            body["system"] = "\n\n".join(system_parts)
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
