"""Harness registry.

Each harness is a self-contained module that exposes
``register_routes(app)`` and ``applied_layers`` and owns its prompts,
helpers, and tests.
"""
from __future__ import annotations

from . import anonymization, chat, extraction, process

__all__ = ["anonymization", "chat", "extraction", "process"]


def all_harnesses() -> list:
    """Return every harness module known to the registry."""
    return [chat, process, extraction, anonymization]
