"""Packs harness — adapter for the existing hub module.

Wraps the existing functionality without moving routes. Declares the
hub-side contract so test_hub_harness_imports.py can validate it.
Future refactor: migrate the inline route handlers in app/main.py
into this module's register_routes(app).
"""
from __future__ import annotations

from typing import Any

name = "packs"
applied_layers: tuple[str, ...] = ()
consumes: tuple[str, ...] = ('rag_doc', 'grep_rule', 'fact_template', 'citation_edge', 'corridor_profile')
emits: tuple[str, ...] = ()


def register_routes(app: Any) -> None:
    """No-op: routes already registered inline in app/main.py."""
    return None
