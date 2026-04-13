"""Source protocol. See docs/architecture.md section 4.1."""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from src.schemas.items import RawItem


@runtime_checkable
class Source(Protocol):
    """Abstract source connector.

    Every concrete source is read-only and yields RawItems lazily. Sources
    must set a stable `id` so provenance tracking works across runs.
    """

    id: str
    name: str
    version: str
    description: str

    def fetch(self) -> Iterator[RawItem]:
        """Yield raw items lazily. Must not load everything into memory."""
        ...

    def count(self) -> int | None:
        """Total items available, or None if unknown. Used for progress bars."""
        ...

    def healthcheck(self) -> bool:
        """Return True if the source is reachable and readable right now."""
        ...
