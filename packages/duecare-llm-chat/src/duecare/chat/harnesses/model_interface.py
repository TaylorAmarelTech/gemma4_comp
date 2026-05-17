"""Provider-neutral model interface helpers for harnesses.

The harness layer should not care whether a model is the Kaggle Gemma 4
runtime, a DueCare model adapter, Ollama, an OpenAI-compatible endpoint,
Anthropic, Gemini, or a simple test callable. These helpers define the
smallest common request/response shape and call adapters by duck typing.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class UniversalModelRequest:
    """Normalized model request used by harnesses."""

    messages: tuple[Mapping[str, Any], ...]
    tools: tuple[Mapping[str, Any], ...] = ()
    images: tuple[Any, ...] = ()
    max_tokens: int = 1024
    temperature: float = 0.0
    top_p: float | None = None
    top_k: int | None = None
    response_format: str = ""
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class UniversalModelResponse:
    """Normalized model response returned to harnesses."""

    text: str
    raw: Any = None
    model_id: str = ""
    provider: str = ""
    usage: Mapping[str, Any] | None = None
    finish_reason: str = ""
    latency_ms: int | None = None
    tool_calls: tuple[Mapping[str, Any], ...] = ()


class SupportsGenerate(Protocol):
    """Duck-typed shape implemented by duecare-llm-models adapters."""

    def generate(
        self,
        messages: list[Any],
        tools: list[Any] | None = None,
        images: list[Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> Any:
        ...


def normalize_model_messages(prompt_or_messages: Any) -> tuple[Mapping[str, Any], ...]:
    """Coerce a prompt string, dict, pydantic message, or message list.

    The returned shape is plain dicts so harness traces can serialize them
    without depending on a specific provider SDK.
    """
    if isinstance(prompt_or_messages, str):
        return ({"role": "user", "content": prompt_or_messages},)
    if isinstance(prompt_or_messages, Mapping):
        return (_message_to_dict(prompt_or_messages),)
    if isinstance(prompt_or_messages, Sequence) and not isinstance(prompt_or_messages, (bytes, bytearray)):
        return tuple(_message_to_dict(item) for item in prompt_or_messages)
    return ({"role": "user", "content": str(prompt_or_messages)},)


def request_from_input(
    prompt_or_messages: Any,
    *,
    tools: Sequence[Mapping[str, Any]] | None = None,
    images: Sequence[Any] | None = None,
    max_tokens: int | None = None,
    max_new_tokens: int | None = None,
    temperature: float = 0.0,
    top_p: float | None = None,
    top_k: int | None = None,
    response_format: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> UniversalModelRequest:
    """Build the normalized model request object."""
    token_limit = int(max_tokens or max_new_tokens or 1024)
    return UniversalModelRequest(
        messages=normalize_model_messages(prompt_or_messages),
        tools=tuple(dict(item) for item in (tools or ())),
        images=tuple(images or ()),
        max_tokens=token_limit,
        temperature=float(temperature),
        top_p=top_p,
        top_k=top_k,
        response_format=response_format,
        metadata=dict(metadata or {}),
    )


def call_model_backend(
    backend: Any,
    prompt_or_messages: Any,
    *,
    tools: Sequence[Mapping[str, Any]] | None = None,
    images: Sequence[Any] | None = None,
    max_tokens: int | None = None,
    max_new_tokens: int | None = None,
    temperature: float = 0.0,
    top_p: float | None = None,
    top_k: int | None = None,
    response_format: str = "",
    **kwargs: Any,
) -> UniversalModelResponse:
    """Call any supported model backend and normalize its response.

    Supported backend shapes:
    - `duecare.models` adapters with `.generate(...)`
    - objects with `.chat(...)` or `.complete(...)`
    - direct callables such as `app.state.gemma_call`
    """
    if backend is None:
        raise RuntimeError("No model backend configured for this harness path.")

    request = request_from_input(
        prompt_or_messages,
        tools=tools,
        images=images,
        max_tokens=max_tokens,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        response_format=response_format,
    )
    call_kwargs = _provider_kwargs(request, **kwargs)

    if hasattr(backend, "generate"):
        result = backend.generate(
            _messages_for_duecare_model(request.messages),
            tools=_tools_for_duecare_model(request.tools) or None,
            images=list(request.images) or None,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            **call_kwargs,
        )
        return coerce_model_response(result, raw_backend=backend)

    if hasattr(backend, "chat"):
        result = backend.chat(
            list(request.messages),
            tools=list(request.tools) or None,
            images=list(request.images) or None,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            **call_kwargs,
        )
        return coerce_model_response(result, raw_backend=backend)

    if hasattr(backend, "complete"):
        result = backend.complete(
            _prompt_text(request.messages),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            **call_kwargs,
        )
        return coerce_model_response(result, raw_backend=backend)

    if isinstance(backend, Callable):
        callable_kwargs = dict(call_kwargs)
        callable_kwargs["temperature"] = request.temperature
        callable_kwargs["max_new_tokens"] = request.max_tokens
        result = backend(_callable_payload(prompt_or_messages, request), **callable_kwargs)
        return coerce_model_response(result, raw_backend=backend)

    raise TypeError(f"Unsupported model backend type: {type(backend).__name__}")


def coerce_model_response(result: Any, *, raw_backend: Any = None) -> UniversalModelResponse:
    """Extract text, usage, model id, and tool calls from common SDK shapes."""
    text = _extract_text(result)
    usage = _extract_usage(result)
    tool_calls = tuple(_extract_tool_calls(result))
    return UniversalModelResponse(
        text=text,
        raw=result,
        model_id=_extract_attr_or_key(result, "model_id") or _extract_attr_or_key(result, "model") or "",
        provider=getattr(raw_backend, "provider", "") or getattr(raw_backend, "id", ""),
        usage=usage,
        finish_reason=_extract_attr_or_key(result, "finish_reason") or "",
        latency_ms=_extract_int_attr_or_key(result, "latency_ms"),
        tool_calls=tool_calls,
    )


def _message_to_dict(message: Any) -> Mapping[str, Any]:
    if isinstance(message, Mapping):
        role = str(message.get("role") or "user")
        content = message.get("content", "")
        out = {"role": role, "content": content}
        for key in ("name", "tool_call_id"):
            if key in message and message[key] is not None:
                out[key] = message[key]
        return out
    if hasattr(message, "model_dump"):
        return _message_to_dict(message.model_dump())
    if hasattr(message, "dict"):
        return _message_to_dict(message.dict())
    return {"role": getattr(message, "role", "user"), "content": getattr(message, "content", str(message))}


def _messages_for_duecare_model(messages: Sequence[Mapping[str, Any]]) -> list[Any]:
    try:
        from duecare.core.schemas import ChatMessage
    except Exception:
        return [dict(item) for item in messages]

    converted: list[Any] = []
    for item in messages:
        content = item.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        converted.append(ChatMessage(
            role=_core_role(str(item.get("role") or "user")),
            content=content,
            name=item.get("name"),
            tool_call_id=item.get("tool_call_id"),
        ))
    return converted


def _tools_for_duecare_model(tools: Sequence[Mapping[str, Any]]) -> list[Any]:
    if not tools:
        return []
    try:
        from duecare.core.schemas import ToolSpec
    except Exception:
        return [dict(item) for item in tools]

    converted: list[Any] = []
    for item in tools:
        converted.append(ToolSpec(
            name=str(item.get("name") or item.get("function", {}).get("name") or ""),
            description=str(item.get("description") or item.get("function", {}).get("description") or ""),
            parameters=dict(item.get("parameters") or item.get("function", {}).get("parameters") or {}),
        ))
    return converted


def _core_role(role: str) -> str:
    if role == "model":
        return "assistant"
    if role in {"system", "user", "assistant", "tool"}:
        return role
    return "user"


def _provider_kwargs(request: UniversalModelRequest, **kwargs: Any) -> dict[str, Any]:
    out = dict(kwargs)
    if request.top_p is not None:
        out["top_p"] = request.top_p
    if request.top_k is not None:
        out["top_k"] = request.top_k
    if request.response_format:
        out["response_format"] = request.response_format
    return out


def _callable_payload(original: Any, request: UniversalModelRequest) -> Any:
    if isinstance(original, str):
        return original
    return [dict(item) for item in request.messages]


def _prompt_text(messages: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in messages)


def _extract_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if hasattr(result, "text"):
        return str(getattr(result, "text") or "")
    if isinstance(result, Mapping):
        for key in ("text", "response", "output_text"):
            value = result.get(key)
            if isinstance(value, str):
                return value
        message = result.get("message")
        if isinstance(message, Mapping):
            content = message.get("content")
            if isinstance(content, str):
                return content
        choices = result.get("choices")
        if isinstance(choices, Sequence) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                msg = first.get("message")
                if isinstance(msg, Mapping) and isinstance(msg.get("content"), str):
                    return msg["content"]
                if isinstance(first.get("text"), str):
                    return first["text"]
        content = result.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, Sequence):
            pieces = []
            for part in content:
                if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                    pieces.append(part["text"])
            if pieces:
                return "\n".join(pieces)
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    return str(result)


def _extract_usage(result: Any) -> Mapping[str, Any] | None:
    if isinstance(result, Mapping):
        usage = result.get("usage")
        return dict(usage) if isinstance(usage, Mapping) else None
    keys = ("tokens_used", "prompt_tokens", "completion_tokens", "cost_usd")
    usage = {key: getattr(result, key) for key in keys if hasattr(result, key)}
    return usage or None


def _extract_tool_calls(result: Any) -> list[Mapping[str, Any]]:
    calls = _extract_attr_or_key(result, "tool_calls")
    if not calls:
        return []
    out: list[Mapping[str, Any]] = []
    for call in calls:
        if isinstance(call, Mapping):
            out.append(dict(call))
        elif hasattr(call, "model_dump"):
            out.append(dict(call.model_dump()))
        elif hasattr(call, "dict"):
            out.append(dict(call.dict()))
        else:
            out.append({"raw": str(call)})
    return out


def _extract_attr_or_key(result: Any, key: str) -> Any:
    if isinstance(result, Mapping):
        return result.get(key)
    return getattr(result, key, None)


def _extract_int_attr_or_key(result: Any, key: str) -> int | None:
    value = _extract_attr_or_key(result, key)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None
