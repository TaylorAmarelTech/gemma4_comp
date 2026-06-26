#!/usr/bin/env python3
"""Domain registry loader for the cross-domain harness-lift benchmark.

A thin, dependency-free reader over
``configs/duecare/benchmarks/domains/registry.json`` -- the single source of
truth mapping a benchmark *domain* (``trafficking``, ``money_laundering``, ...)
to its scheme-prompt pack, RAG vertical, A-E rubric anchors, controlling legal
instruments, regulators/FIUs, and jurisdictions. See ``docs/cross_domain_port.md``.

Propose-only: every legal mapping in the registry must be source-verified by a
domain expert before any public claim. This loader does not assert legal
accuracy; it only resolves and structurally validates the registry.

    python scripts/domain_registry.py                 # list all domains
    python scripts/domain_registry.py money_laundering  # show one domain's spec
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY_PATH = _ROOT / "configs" / "duecare" / "benchmarks" / "domains" / "registry.json"

_REQUIRED_KEYS = (
    "display_name",
    "scheme_pack",
    "rag_vertical",
    "rubric_anchors",
    "instruments",
    "regulators",
    "jurisdictions",
)
_RUBRIC_KEYS = ("A_indicator", "B_law", "C_refuse", "D_resources", "E_safety")


class DomainError(KeyError):
    """Raised when a requested domain id is not present in the registry."""


def load_registry(path: pathlib.Path | None = None) -> dict[str, Any]:
    """Read and structurally validate the domain registry.

    Args:
        path: optional override of the registry path (for tests).

    Returns:
        The parsed ``{"_meta": ..., "domains": {...}}`` document.

    Raises:
        ValueError: if the registry has no ``domains`` map, or a domain entry is
            missing a required key or a rubric anchor.
    """
    p = path or REGISTRY_PATH
    doc = json.loads(p.read_text(encoding="utf-8"))
    domains = doc.get("domains")
    if not isinstance(domains, dict) or not domains:
        raise ValueError(f"registry has no non-empty 'domains' map: {p}")
    for did, spec in domains.items():
        missing = [k for k in _REQUIRED_KEYS if k not in spec]
        if missing:
            raise ValueError(f"domain '{did}' missing keys: {missing}")
        anchors = spec.get("rubric_anchors", {})
        missing_anchors = [k for k in _RUBRIC_KEYS if k not in anchors]
        if missing_anchors:
            raise ValueError(f"domain '{did}' rubric_anchors missing: {missing_anchors}")
    return doc


def list_domains(path: pathlib.Path | None = None) -> list[str]:
    """Return the sorted domain ids in the registry."""
    return sorted(load_registry(path)["domains"].keys())


def get_domain(domain_id: str, path: pathlib.Path | None = None) -> dict[str, Any]:
    """Return one domain's spec dict.

    Raises:
        DomainError: if ``domain_id`` is not in the registry.
    """
    domains = load_registry(path)["domains"]
    if domain_id not in domains:
        raise DomainError(f"unknown domain '{domain_id}'; known: {sorted(domains)}")
    return domains[domain_id]


def resolve_scheme_pack(domain_id: str, path: pathlib.Path | None = None) -> pathlib.Path:
    """Resolve a domain's scheme-pack path to an absolute path (may not exist yet)."""
    spec = get_domain(domain_id, path)
    rel = spec["scheme_pack"]
    candidate = pathlib.Path(rel)
    return candidate if candidate.is_absolute() else (_ROOT / rel)


def _main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Inspect the benchmark domain registry.")
    ap.add_argument("domain", nargs="?", help="domain id to show; omit to list all")
    args = ap.parse_args()
    if args.domain:
        print(json.dumps(get_domain(args.domain), indent=2, ensure_ascii=False))
    else:
        for did in list_domains():
            spec = get_domain(did)
            print(
                f"{did}: {spec['display_name']} "
                f"[{spec.get('status', '?')}] -> {spec['scheme_pack']}"
            )


if __name__ == "__main__":
    _main()
