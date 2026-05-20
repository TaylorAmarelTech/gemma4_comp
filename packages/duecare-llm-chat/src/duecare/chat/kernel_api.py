"""Pydantic body models for the kernel mutation endpoints.

Each model corresponds to one POST endpoint in the Kaggle exploration
kernel. Models validate + coerce input (most importantly: parse
JSON-stringified booleans correctly -- bare ``bool("false")`` returns
True in plain Python, which silently enables destructive flags).

The kernel keeps its ``body: dict = Body(default=None)`` route
signatures so FastAPI does not auto-422 on extra fields (some callers
send unknown keys like ``run_id`` for tracing). Instead, each
endpoint calls ``ModelXRequest.model_validate(body or {})`` to get a
type-safe view of the validated fields. This is the best of both
worlds: extra fields are silently ignored (backward compatible) but
the declared fields are typed and coerced.

The bool coercion uses ``parse_request_bool`` which accepts:
  * native True / False  -> as-is
  * 1 / 0                -> True / False
  * "true" / "false" / "yes" / "no" / "on" / "off" (case-insensitive)
  * None / missing       -> the field default

Anything else returns the field default so an obviously bogus value
(e.g., a malformed front-end form post) cannot quietly enable a
destructive flag.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def parse_request_bool(value: Any, default: bool) -> bool:
    """Robust bool parser used by the field validators below.

    Public so the kernel can import it directly when validating fields
    outside the body (e.g., query params, header values).
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off", ""):
            return False
    return default


class _PermissiveBody(BaseModel):
    """Common config for kernel body models.

    ``extra="ignore"`` keeps the model backward-compatible with callers
    that send unknown keys (e.g., tracing fields). Pydantic still
    validates + coerces the declared fields strictly.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)


class UseChatAsJudgeRequest(_PermissiveBody):
    """Body for ``POST /api/use-chat-as-judge``.

    Toggling the mirror affects every grader on the kernel so the
    operator token is always required (validated server-side; the
    field is here so a single ``model_validate`` covers both).
    """

    enabled: bool = True
    operator_token: str = ""

    @field_validator("enabled", mode="before")
    @classmethod
    def _coerce_enabled(cls, v: Any) -> bool:
        return parse_request_bool(v, default=True)


class LoadModelRequest(_PermissiveBody):
    """Body for ``POST /api/load-model``.

    ``variant`` is the picker key (e.g., "31b-it"). ``override``
    bypasses the preflight gate when the operator has manually
    verified disk + GPU headroom.
    """

    variant: str = ""
    override: bool = False

    @field_validator("override", mode="before")
    @classmethod
    def _coerce_override(cls, v: Any) -> bool:
        return parse_request_bool(v, default=False)

    @field_validator("variant", mode="before")
    @classmethod
    def _coerce_variant(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()


class LoadEvaluatorModelRequest(_PermissiveBody):
    """Body for ``POST /api/load-evaluator-model``.

    ``variant`` defaults to ``"31b-it"`` when missing/empty because
    that is the suggested judge model. ``override`` bypasses the
    preflight gate (same semantics as the chat load).
    """

    variant: str = "31b-it"
    override: bool = False

    @field_validator("override", mode="before")
    @classmethod
    def _coerce_override(cls, v: Any) -> bool:
        return parse_request_bool(v, default=False)

    @field_validator("variant", mode="before")
    @classmethod
    def _coerce_variant(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "31b-it"
        return str(v).strip()


class UnloadModelRequest(_PermissiveBody):
    """Body for ``POST /api/unload-model`` and
    ``POST /api/unload-evaluator-model``.

    Used by both chat + judge unload endpoints. ``force`` interrupts
    in-flight users mid-generate (requires operator token).
    ``drain_seconds`` is the grace period for in-flight requests when
    ``force=False``.
    """

    purge_cache: bool = True
    force: bool = False
    drain_seconds: float = Field(default=30.0, ge=0.0, le=600.0)
    operator_token: str = ""

    @field_validator("purge_cache", mode="before")
    @classmethod
    def _coerce_purge_cache(cls, v: Any) -> bool:
        return parse_request_bool(v, default=True)

    @field_validator("force", mode="before")
    @classmethod
    def _coerce_force(cls, v: Any) -> bool:
        return parse_request_bool(v, default=False)


__all__ = [
    "LoadEvaluatorModelRequest",
    "LoadModelRequest",
    "UnloadModelRequest",
    "UseChatAsJudgeRequest",
    "parse_request_bool",
]
