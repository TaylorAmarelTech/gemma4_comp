"""Import Corpus harness."""
from __future__ import annotations

from .handler import register_routes

name = "import_corpus"
applied_layers: tuple[str, ...] = ()  # CRUD only, no safety layers

__all__ = ["name", "applied_layers", "register_routes"]
