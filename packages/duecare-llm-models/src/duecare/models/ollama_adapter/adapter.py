"""Ollama adapter -- local Ollama server via HTTP API.

Connects to a running Ollama instance (default http://localhost:11434)
and supports text generation, function calling, multimodal (vision)
input, and embeddings. Uses httpx for robust HTTP handling with
configurable timeouts and connection-error recovery.

Ollama model names follow the ``name:tag`` convention, e.g.
``gemma4:e4b``, ``gemma4:e2b``, ``llama3.3``, ``mistral``.

No hard dependency on the ``ollama`` Python client -- only httpx is
required.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolCall,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase
from duecare.observability.logging import get_logger

log = get_logger("duecare.models.ollama")

# Ollama API response field names.
_FIELD_MESSAGE = "message"
_FIELD_CONTENT = "content"
_FIELD_TOOL_CALLS = "tool_calls"
_FIELD_DONE_REASON = "done_reason"
_FIELD_PROMPT_EVAL_COUNT = "prompt_eval_count"
_FIELD_EVAL_COUNT = "eval_count"
_FIELD_EMBEDDING = "embedding"


@model_registry.register("ollama")
class OllamaModel(ModelAdapterBase):
    """Talk to a local Ollama server.

    Args:
        model_id: Ollama model name, e.g. ``gemma4:e4b``, ``llama3.3``.
        display_name: Human-readable label (defaults to *model_id*).
        host: Base URL for the Ollama HTTP API.
        timeout: Per-request timeout in seconds. Ollama inference on
            large models can be slow, so the default is generous.
        context_length: Context window size to advertise. Ollama models
            vary; 8192 is a safe default for most.
        capabilities: Override the default capability set.
    """

    provider = "ollama"

    def __init__(
        self,
        model_id: str,
        *,
        display_name: str | None = None,
        host: str = "http://localhost:11434",
        timeout: float = 300.0,
        context_length: int = 8192,
        capabilities: set[Capability] | None = None,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"ollama:{model_id}"
        self.display_name = display_name or model_id
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.context_length = context_length
        self.capabilities = capabilities or {
            Capability.TEXT,
            Capability.EMBEDDINGS,
            Capability.FUNCTION_CALLING,
            Capability.VISION,
        }
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        """Return or lazily create the httpx client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to the Ollama API and return the decoded response.

        Args:
            path: API path, e.g. ``/api/chat``.
            body: Request body as a dict.

        Returns:
            Decoded JSON response.

        Raises:
            ConnectionError: Ollama is not reachable.
            TimeoutError: Request exceeded the configured timeout.
            RuntimeError: Ollama returned an HTTP error.
        """
        client = self._get_client()
        try:
            resp = client.post(path, json=body)
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Is it running? Start with: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama request to {path} timed out after {self.timeout}s "
                f"for model {self.model_id!r}."
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Ollama request failed: {exc}"
            ) from exc

        if resp.status_code != 200:
            detail = resp.text[:500]
            raise RuntimeError(
                f"Ollama returned HTTP {resp.status_code} for {path}: {detail}"
            )
        return resp.json()

    def _get(self, path: str) -> dict[str, Any]:
        """GET from the Ollama API."""
        client = self._get_client()
        try:
            resp = client.get(path)
        except httpx.ConnectError as exc:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}."
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama GET {path} timed out."
            ) from exc
        if resp.status_code != 200:
            raise RuntimeError(
                f"Ollama returned HTTP {resp.status_code} for GET {path}"
            )
        return resp.json()

    # ------------------------------------------------------------------
    # Message serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_messages(
        messages: list[ChatMessage],
        images: list[bytes] | None,
    ) -> list[dict[str, Any]]:
        """Convert DueCare ChatMessages to Ollama wire format.

        If *images* are provided they are attached (base64-encoded) to
        the last user message, matching Ollama's multimodal API.
        """
        wire: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
            }
            wire.append(entry)

        # Attach images to the final user message.
        if images and wire:
            last_user_idx: int | None = None
            for idx in range(len(wire) - 1, -1, -1):
                if wire[idx]["role"] == "user":
                    last_user_idx = idx
                    break
            if last_user_idx is not None:
                wire[last_user_idx]["images"] = [
                    base64.b64encode(img).decode("ascii") for img in images
                ]

        return wire

    # ------------------------------------------------------------------
    # Tool-call parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tool_calls(
        raw_calls: list[dict[str, Any]] | None,
    ) -> list[ToolCall]:
        """Parse Ollama tool_calls into DueCare ToolCall schemas."""
        if not raw_calls:
            return []
        parsed: list[ToolCall] = []
        for tc in raw_calls:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    raw_args = {}
            parsed.append(
                ToolCall(
                    name=fn.get("name", ""),
                    arguments=raw_args if isinstance(raw_args, dict) else {},
                    call_id=tc.get("id"),
                )
            )
        return parsed

    # ------------------------------------------------------------------
    # Core Model protocol methods
    # ------------------------------------------------------------------

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs: Any,
    ) -> GenerationResult:
        """Send a chat completion request to Ollama.

        Args:
            messages: Conversation history.
            tools: Optional tool specifications for function calling.
            images: Optional images (raw bytes) for multimodal models.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 = greedy).
            **kwargs: Additional Ollama options forwarded to the API.

        Returns:
            A populated ``GenerationResult``.
        """
        body: dict[str, Any] = {
            "model": self.model_id,
            "messages": self._serialize_messages(messages, images),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        # Forward any extra Ollama options the caller passes.
        extra_options: dict[str, Any] | None = kwargs.get("options")
        if extra_options and isinstance(extra_options, dict):
            body["options"].update(extra_options)

        if tools:
            body["tools"] = [t.to_openai() for t in tools]

        log.debug(
            "ollama generate",
            model=self.model_id,
            n_messages=len(messages),
            max_tokens=max_tokens,
        )

        response = self._post("/api/chat", body)
        message = response.get(_FIELD_MESSAGE, {})

        prompt_tokens = response.get(_FIELD_PROMPT_EVAL_COUNT, 0)
        completion_tokens = response.get(_FIELD_EVAL_COUNT, 0)

        tool_calls = self._parse_tool_calls(
            message.get(_FIELD_TOOL_CALLS),
        )

        return GenerationResult(
            text=message.get(_FIELD_CONTENT, ""),
            finish_reason=response.get(_FIELD_DONE_REASON, "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_used=prompt_tokens + completion_tokens,
            tool_calls=tool_calls,
            model_id=self.id,
            model_version=response.get("model", ""),
            raw=response,
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        """Generate embeddings via Ollama's /api/embeddings endpoint.

        Args:
            texts: Strings to embed.

        Returns:
            One ``Embedding`` per input text.
        """
        results: list[Embedding] = []
        for text in texts:
            resp = self._post(
                "/api/embeddings",
                {"model": self.model_id, "prompt": text},
            )
            vec = resp.get(_FIELD_EMBEDDING, [])
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
        """Check whether Ollama is reachable and the model is available.

        Returns:
            ``ModelHealth`` with ``healthy=True`` if Ollama responds and
            the requested model is listed in ``/api/tags``.
        """
        try:
            data = self._get("/api/tags")
            available_models = [
                m.get("name", "") for m in data.get("models", [])
            ]
            # Ollama lists models as "name:tag"; match on the base name.
            base_name = self.model_id.split(":")[0]
            model_found = any(
                m.split(":")[0] == base_name for m in available_models
            )
            return ModelHealth(
                model_id=self.id,
                healthy=True,
                details={
                    "host": self.host,
                    "model_found": model_found,
                    "available_models": available_models,
                },
            )
        except (ConnectionError, TimeoutError) as exc:
            return ModelHealth(
                model_id=self.id,
                healthy=False,
                details={"host": self.host, "error": str(exc)},
            )
        except Exception as exc:
            return ModelHealth(
                model_id=self.id,
                healthy=False,
                details={"host": self.host, "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """Return all model names available on the Ollama server.

        Returns:
            List of model name strings (e.g. ``['gemma4:e4b', 'llama3.3:latest']``).

        Raises:
            ConnectionError: If Ollama is unreachable.
        """
        data = self._get("/api/tags")
        return [m.get("name", "") for m in data.get("models", [])]

    def pull_model(self, *, model_name: str | None = None) -> bool:
        """Pull a model into the local Ollama cache.

        Args:
            model_name: Name to pull. Defaults to ``self.model_id``.

        Returns:
            ``True`` if the pull completed successfully.
        """
        name = model_name or self.model_id
        log.info("ollama pulling model", model=name)
        # /api/pull streams progress; use a longer timeout.
        client = self._get_client()
        try:
            resp = client.post(
                "/api/pull",
                json={"name": name, "stream": False},
                timeout=httpx.Timeout(3600.0, connect=10.0),
            )
            return resp.status_code == 200
        except httpx.TimeoutException:
            log.warning("ollama pull timed out", model=name)
            return False
        except httpx.ConnectError:
            log.warning("ollama not reachable for pull", model=name)
            return False

    def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __del__(self) -> None:
        self.close()
