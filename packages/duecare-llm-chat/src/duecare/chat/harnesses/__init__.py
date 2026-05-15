"""Harness registry.

PRIMARY_HARNESSES are the user-named safety surfaces.
SECONDARY_HARNESSES are CRUD / utility surfaces.
"""
from __future__ import annotations

from . import (
    anonymization, chat, extraction, import_corpus,
    process, search, search_safety,
)

# search_safety is PRIMARY because it is a defense-in-depth safety
# layer (intercepts outbound search queries before they reach a
# third-party backend). It sits next to anonymization in the safety
# tier even though it does not compose layers itself.
PRIMARY_HARNESSES: tuple = (chat, process, extraction, anonymization, search_safety)
SECONDARY_HARNESSES: tuple = (search, import_corpus)

__all__ = [
    "anonymization", "chat", "extraction", "import_corpus",
    "process", "search", "search_safety",
    "PRIMARY_HARNESSES", "SECONDARY_HARNESSES", "all_harnesses",
]


def all_harnesses() -> list:
    return [*PRIMARY_HARNESSES, *SECONDARY_HARNESSES]
