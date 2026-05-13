"""Chat harness — full multimodal orchestrator."""
from __future__ import annotations

from .handler import register_routes
from .send import serve_chat_send
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "chat"
applied_layers: tuple[str, ...] = ("persona", "grep", "rag", "tools", "online")
capabilities: tuple[str, ...] = ()  # multi_turn scaffolded but disabled

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits",
           "register_routes", "serve_chat_send"]
