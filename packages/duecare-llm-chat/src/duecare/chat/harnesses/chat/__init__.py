"""Chat harness."""
from __future__ import annotations

from .handler import register_routes
from .send import serve_chat_send

name = "chat"
applied_layers: tuple[str, ...] = ("persona", "grep", "rag", "tools", "online")

__all__ = ["name", "applied_layers", "register_routes", "serve_chat_send"]
