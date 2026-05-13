"""Harness registry.

Each harness is a self-contained module that exposes
``register_routes(app)`` and owns its prompts, helpers, and tests.
"""
from __future__ import annotations

from . import extraction  # noqa: F401

__all__ = ["extraction"]
