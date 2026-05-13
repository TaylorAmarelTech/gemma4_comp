"""Harness registry.

PRIMARY_HARNESSES are the user-named safety surfaces.
SECONDARY_HARNESSES are CRUD / utility surfaces.
"""
from __future__ import annotations

from . import anonymization, chat, extraction, import_corpus, process, search

PRIMARY_HARNESSES: tuple = (chat, process, extraction, anonymization)
SECONDARY_HARNESSES: tuple = (import_corpus, search)

__all__ = [
    "anonymization", "chat", "extraction", "import_corpus",
    "process", "search",
    "PRIMARY_HARNESSES", "SECONDARY_HARNESSES", "all_harnesses",
]


def all_harnesses() -> list:
    return [*PRIMARY_HARNESSES, *SECONDARY_HARNESSES]
