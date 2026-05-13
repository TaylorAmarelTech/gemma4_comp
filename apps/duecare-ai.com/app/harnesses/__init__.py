"""Hub-side harness registry — mirrors the kernel pattern."""
from __future__ import annotations

from . import curator, packs, pii_anonymize, sentinel, submit

PRIMARY_HARNESSES: tuple = (curator, sentinel, submit)
SECONDARY_HARNESSES: tuple = (packs, pii_anonymize)

__all__ = [
    "curator", "packs", "pii_anonymize", "sentinel", "submit",
    "PRIMARY_HARNESSES", "SECONDARY_HARNESSES", "all_harnesses",
]


def all_harnesses() -> list:
    return [*PRIMARY_HARNESSES, *SECONDARY_HARNESSES]
