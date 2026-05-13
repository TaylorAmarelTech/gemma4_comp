"""Knowledge Extraction harness."""
from __future__ import annotations

from .handler import register_routes

name = "extraction"
applied_layers: tuple[str, ...] = ("grep", "rag")

__all__ = ["name", "applied_layers", "register_routes"]
