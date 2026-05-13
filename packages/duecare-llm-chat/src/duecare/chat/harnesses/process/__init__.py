"""Process Files harness."""
from __future__ import annotations

from .handler import register_routes

name = "process"
applied_layers: tuple[str, ...] = ("grep", "rag", "tools")

__all__ = ["name", "applied_layers", "register_routes"]
