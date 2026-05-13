"""Harness registry.

PRIMARY_HARNESSES are the 4 user-facing safety harnesses
(chat / process / extraction / anonymization). SECONDARY_HARNESSES
are CRUD or inspector surfaces that share the same architectural
contract (name + applied_layers + register_routes) but are not
themselves load-bearing safety layers.
"""
from __future__ import annotations

from . import anonymization, chat, extraction, import_corpus, process

PRIMARY_HARNESSES: tuple = (chat, process, extraction, anonymization)
SECONDARY_HARNESSES: tuple = (import_corpus,)

__all__ = [
    "anonymization", "chat", "extraction", "import_corpus", "process",
    "PRIMARY_HARNESSES", "SECONDARY_HARNESSES", "all_harnesses",
]


def all_harnesses() -> list:
    """Return every harness module known to the registry."""
    return [*PRIMARY_HARNESSES, *SECONDARY_HARNESSES]
