"""Chat harness."""
from __future__ import annotations

from .handler import register_routes
from .send import serve_chat_send

name = "chat"

__all__ = ["name", "register_routes", "serve_chat_send"]
