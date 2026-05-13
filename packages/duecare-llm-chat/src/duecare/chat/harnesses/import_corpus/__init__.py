"""Import Corpus harness — user-attached evidence CRUD."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "import_corpus"
applied_layers: tuple[str, ...] = ()
capabilities: tuple[str, ...] = ()  # CRUD; multi_turn not applicable

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes"]
