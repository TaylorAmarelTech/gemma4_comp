"""Anonymization & Sharing harness — PII gate (regex-only by design)."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "anonymization"
applied_layers: tuple[str, ...] = ()  # regex-only by design
capabilities: tuple[str, ...] = ()  # stateless gate; multi_turn not applicable

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes"]
