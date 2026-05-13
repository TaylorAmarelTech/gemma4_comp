"""Process Files harness — bundle analyst + graph-chat."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits

name = "process"
applied_layers: tuple[str, ...] = ("grep", "rag", "tools")

__all__ = ["name", "applied_layers", "consumes", "emits", "register_routes"]
