"""Centralized kernel settings sourced from environment variables.

Replaces 14+ scattered ``os.environ.get(...)`` reads with a single
``KernelSettings`` model so:

  * Types are explicit (boolean parsing, int casts, default values).
  * Defaults are documented in one place.
  * A future kernel deployment can override values consistently.
  * Tests can construct a settings instance with explicit overrides
    instead of monkey-patching ``os.environ``.

Why a custom factory instead of ``pydantic-settings``?

We want zero new dependencies on the Kaggle runtime. The
``KernelSettings.from_env()`` classmethod does the env-var reads
manually but the model itself uses Pydantic v2 BaseModel so field
types are validated. This is good enough for our scope and avoids
pinning another package version.

Wiring example:

    from duecare.chat.config import KernelSettings, settings

    # Read once at module load (same as the kernel's existing pattern).
    cfg = settings()

    if cfg.enable_online_search:
        ...

    api_key = cfg.openai_api_key  # "" when unset

The ``settings()`` accessor returns a cached instance. Call
``settings(reload=True)`` to re-read os.environ (rarely needed; the
kernel runs in a single process so env values are stable after
boot).

This module does NOT replace Phase 0's early env reads in kernel.py
(the kernel script reads a few values BEFORE duecare.chat is on the
Python path because they configure how duecare.chat is installed).
Those reads stay inline. New code paths added after the kernel has
loaded duecare.chat can use this module.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _env_bool(name: str, default: bool) -> bool:
    """Parse an env var into a boolean using the same semantics as
    ``duecare.chat.kernel_api.parse_request_bool`` so behaviour is
    consistent across the two surfaces."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    s = raw.strip().lower()
    if s in ("true", "1", "yes", "y", "on"):
        return True
    if s in ("false", "0", "no", "n", "off", ""):
        return False
    return default


def _env_int(name: str, default: int) -> int:
    """Parse an env var into an int with a default fallback. Returns
    the default on missing OR non-numeric values so a stray
    ``GEMMA_MAX_SEQ_LEN=large`` doesn't crash the kernel boot."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str = "") -> str:
    """String env var with default. Strips whitespace; preserves case."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip() if isinstance(raw, str) else default


class KernelSettings(BaseModel):
    """All env-var-driven kernel configuration in one place.

    Frozen so callers cannot accidentally mutate a settings instance
    and have the change visible elsewhere. To override, build a new
    instance via ``KernelSettings(**overrides)`` or use
    ``settings(reload=True)`` after mutating ``os.environ``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ------------------------------------------------------------------
    # Identity / version
    # ------------------------------------------------------------------
    duecare_version: str = Field(
        default="0.17.0",
        description="Kernel build version shown on the Status page.",
    )
    duecare_commit_sha: str = Field(
        default="master",
        description="Git ref the wheels were built from.",
    )
    required_chat_version: str = Field(
        default="0.17.0",
        description=(
            "Minimum duecare-llm-chat version the kernel expects. "
            "Phase 0 install verifies this before continuing."
        ),
    )

    # ------------------------------------------------------------------
    # Default model variant
    # ------------------------------------------------------------------
    gemma_model_variant: str = Field(
        default="e4b-it",
        description=(
            "Variant the kernel pre-loads at boot when no picker click "
            "has happened yet. The browser picker overrides this at "
            "runtime. See duecare.chat.variants for valid ids."
        ),
    )
    gemma_load_in_4bit: bool = Field(
        default=True,
        description="Pass load_in_4bit=True to FastModel.from_pretrained.",
    )
    gemma_max_seq_len: int = Field(
        default=32768,
        ge=1024,
        le=131072,
        description="Max context window. Default 32k covers persona+GREP+RAG+tools.",
    )

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------
    enable_online_search: bool = Field(
        default=True,
        description="Expose the /api/online-search route + chat toggle.",
    )
    duecare_allow_old_wheel: bool = Field(
        default=False,
        description=(
            "Skip the strict chat-package version check at boot. Used "
            "during development when wheels lag behind the kernel."
        ),
    )

    # ------------------------------------------------------------------
    # Cloud route credentials (all optional; empty string = disabled)
    # ------------------------------------------------------------------
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"

    # ------------------------------------------------------------------
    # Operator auth
    # ------------------------------------------------------------------
    duecare_operator_token: str = Field(
        default="",
        description=(
            "When set, the kernel uses this as the operator token "
            "instead of generating a random one. Set to keep tokens "
            "stable across cell restarts."
        ),
    )

    # ------------------------------------------------------------------
    # HF cache routing
    # ------------------------------------------------------------------
    hf_home: str = Field(
        default="",
        description=(
            "Path the kernel sets HF_HOME to early in boot. Empty "
            "means the kernel picks a Kaggle-aware default."
        ),
    )

    @classmethod
    def from_env(cls) -> "KernelSettings":
        """Build a settings instance from current os.environ values."""
        return cls(
            duecare_version=_env_str("DUECARE_VERSION", "0.17.0"),
            duecare_commit_sha=_env_str("DUECARE_COMMIT_SHA", "master"),
            required_chat_version=_env_str(
                "DUECARE_REQUIRED_CHAT_VERSION", "0.17.0",
            ),
            gemma_model_variant=_env_str("GEMMA_MODEL_VARIANT", "e4b-it"),
            gemma_load_in_4bit=_env_bool("GEMMA_LOAD_IN_4BIT", True),
            gemma_max_seq_len=_env_int("GEMMA_MAX_SEQ_LEN", 32768),
            enable_online_search=_env_bool("ENABLE_ONLINE_SEARCH", True),
            duecare_allow_old_wheel=_env_bool(
                "DUECARE_ALLOW_OLD_WHEEL", False,
            ),
            gemini_api_key=_env_str("GEMINI_API_KEY"),
            openai_api_key=_env_str("OPENAI_API_KEY"),
            openai_base_url=_env_str(
                "OPENAI_BASE_URL", "https://api.openai.com/v1",
            ),
            openai_model=_env_str("OPENAI_MODEL", "gpt-4o-mini"),
            ollama_host=_env_str("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=_env_str("OLLAMA_MODEL", "gemma2:2b"),
            duecare_operator_token=_env_str("DUECARE_OPERATOR_TOKEN"),
            hf_home=_env_str("HF_HOME"),
        )

    def has_cloud_credentials(self) -> dict[str, bool]:
        """Quick summary of which cloud routes are configured. Used
        by the Status page to show which BYOK variants are ready."""
        return {
            "gemini": bool(self.gemini_api_key),
            "openai": bool(self.openai_api_key),
            "ollama": bool(self.ollama_host and self.ollama_model),
        }


_cached: Optional[KernelSettings] = None


def settings(*, reload: bool = False) -> KernelSettings:
    """Get the kernel settings.

    Returns a cached instance unless ``reload=True``, in which case
    the env is re-read. The cache exists because the kernel runs in
    a single process and env values are stable after boot, so we
    want to avoid the small overhead of repeated env reads.
    """
    global _cached
    if _cached is None or reload:
        _cached = KernelSettings.from_env()
    return _cached


__all__ = [
    "KernelSettings",
    "settings",
]
