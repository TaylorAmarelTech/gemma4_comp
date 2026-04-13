"""Capability - what a Model can do."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """Model capabilities. Each adapter declares which it supports."""

    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    LONG_CONTEXT = "long_context"   # effective context > 32K
    FINE_TUNABLE = "fine_tunable"   # has a local LoRA / SFT path available
