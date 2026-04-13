"""Duecare domain packs layer.

Pluggable safety domains. A domain pack is a self-contained folder of
content (taxonomy.yaml, rubric.yaml, seed_prompts.jsonl, evidence.jsonl,
pii_spec.yaml). This module holds the loader + FileDomainPack class.
The actual packs live in configs/duecare/domains/<id>/ and are versioned
like data, not code.
"""

from __future__ import annotations

from pathlib import Path

from duecare.core.registry import Registry
from duecare.core.contracts import DomainPack

from .loader import DEFAULT_ROOT, discover_all, load_domain_pack
from .pack import FileDomainPack

# Global domain-pack registry.
domain_registry: Registry[DomainPack] = Registry(kind="domain")


def register_discovered(root: Path | str | None = None) -> int:
    """Walk the domain pack directory and register every discoverable pack.

    Returns the number of packs registered.
    """
    count = 0
    for pack in discover_all(root):
        if not domain_registry.has(pack.id):
            domain_registry.add(pack.id, pack)
            count += 1
    return count

__all__ = [
    "DEFAULT_ROOT",
    "DomainPack",
    "FileDomainPack",
    "discover_all",
    "domain_registry",
    "load_domain_pack",
    "register_discovered",
]
