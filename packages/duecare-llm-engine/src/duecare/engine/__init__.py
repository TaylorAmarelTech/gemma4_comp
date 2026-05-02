"""Duecare engine package."""
from __future__ import annotations

from duecare.engine.config import EngineConfig
from duecare.engine.runner import Engine
from duecare.engine.results import Run, Document, Entity, Edge, Finding

__all__ = [
    "Engine", "EngineConfig",
    "Run", "Document", "Entity", "Edge", "Finding",
]
