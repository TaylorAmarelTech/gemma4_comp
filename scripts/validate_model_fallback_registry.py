#!/usr/bin/env python3
"""Fail closed when a DueCare model policy has only one route or no receipt rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "configs" / "duecare" / "model_fallbacks.json"


class RegistryError(RuntimeError):
    """Raised when a model fallback policy is brittle or ambiguous."""


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != "duecare.model_fallback_registry.v1":
        raise RegistryError("unexpected model fallback registry schema")
    policies = registry.get("policies")
    if not isinstance(policies, dict) or not policies:
        raise RegistryError("model fallback registry has no policies")
    summary: dict[str, Any] = {"policies": {}, "valid": True}
    for policy_name, policy in policies.items():
        if not isinstance(policy, dict):
            raise RegistryError(f"policy {policy_name!r} is not an object")
        candidates = policy.get("candidates")
        if not isinstance(candidates, list) or len(candidates) < 2:
            raise RegistryError(f"policy {policy_name!r} must have at least two candidates")
        if not str(policy.get("selection") or "").strip():
            raise RegistryError(f"policy {policy_name!r} lacks a selection policy")
        capabilities = policy.get("required_capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise RegistryError(f"policy {policy_name!r} lacks required capabilities")
        canonical = [json.dumps(candidate, sort_keys=True) for candidate in candidates]
        if len(canonical) != len(set(canonical)):
            raise RegistryError(f"policy {policy_name!r} repeats a candidate")
        accelerators = policy.get("accelerator_candidates")
        if accelerators is not None and (
            not isinstance(accelerators, list) or len(accelerators) < 2
        ):
            raise RegistryError(
                f"policy {policy_name!r} must have at least two accelerator candidates"
            )
        summary["policies"][policy_name] = {
            "candidate_count": len(candidates),
            "accelerator_candidate_count": len(accelerators or []),
            "selection": policy["selection"],
        }
    rules = registry.get("rules")
    if not isinstance(rules, list) or not any("Record every candidate" in rule for rule in rules):
        raise RegistryError("registry lacks the mandatory attempt-receipt rule")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    print(json.dumps(validate_registry(registry), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
