"""Hub-side harness base."""
from __future__ import annotations

from typing import Any, Protocol


class HubHarnessBase(Protocol):
    name: str
    applied_layers: tuple[str, ...]
    def register_routes(self, app: Any) -> None: ...
