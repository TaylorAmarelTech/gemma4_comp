"""DomainPack protocol. A self-contained safety domain."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

from duecare.core.schemas import DomainCard


@runtime_checkable
class DomainPack(Protocol):
    """A domain = taxonomy + evidence + rubric + seed corpus.

    A domain pack is a self-contained folder under configs/duecare/domains/.
    The same Duecare code runs unchanged against any pack; changing the
    domain means changing which pack you load.
    """

    id: str
    display_name: str
    version: str
    root: Path

    def card(self) -> DomainCard: ...

    def taxonomy(self) -> dict: ...
    def rubric(self) -> dict: ...
    def pii_spec(self) -> dict: ...

    def seed_prompts(self) -> Iterator[dict]: ...
    def evidence(self) -> Iterator[dict]: ...
    def known_failures(self) -> Iterator[dict]: ...
