"""Bulk File Review harness: bundle analyst + graph-chat."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "process"
applied_layers: tuple[str, ...] = ("grep", "rag", "tools")
capabilities: tuple[str, ...] = ()  # multi_turn scaffolded but disabled

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes"]
