"""Knowledge Extraction harness.

Paste raw text -> Gemma 4 drafts a typed KnowledgeObject envelope.

Exposes:
  - POST /api/knowledge/draft-envelope
"""
from __future__ import annotations

from .handler import register_routes

name = "extraction"

__all__ = ["name", "register_routes"]
