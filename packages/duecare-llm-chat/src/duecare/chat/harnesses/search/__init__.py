"""Search harness — server-automated + client-triggered web search."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "search"
applied_layers: tuple[str, ...] = ()  # search IS the layer; doesn't compose others
capabilities: tuple[str, ...] = ()    # multi_turn (Gemma-guided) deferred to Phase 12

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes"]
