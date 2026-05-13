"""Harness base protocol."""
from __future__ import annotations

from typing import Any, Protocol


class HarnessBase(Protocol):
    """Minimal contract every harness module implements."""

    name: str

    def register_routes(self, app: Any) -> None:
        """Attach this harness's routes to a FastAPI app."""
        ...
