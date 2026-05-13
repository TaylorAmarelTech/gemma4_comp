"""Anonymization & Sharing harness.

Intentionally regex-only -- this harness is the PII safety GATE, so it
must NOT pass raw text through Gemma. The deterministic regex pass is
what makes the gate auditable.
"""
from __future__ import annotations

from .handler import register_routes

name = "anonymization"
applied_layers: tuple[str, ...] = ()  # regex-only by design

__all__ = ["name", "applied_layers", "register_routes"]
