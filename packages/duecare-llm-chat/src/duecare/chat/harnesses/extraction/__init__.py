"""Knowledge Extraction harness — drafts typed KnowledgeObject envelopes."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "extraction"
applied_layers: tuple[str, ...] = ("grep", "rag")
capabilities: tuple[str, ...] = ()  # single-shot; multi_turn not applicable

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes"]
