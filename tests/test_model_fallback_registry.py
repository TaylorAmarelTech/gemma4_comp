from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_model_fallback_registry.py"
REGISTRY = ROOT / "configs" / "duecare" / "model_fallbacks.json"


def _load():
    spec = importlib.util.spec_from_file_location("fallback_validator", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load()


def test_live_registry_has_multiple_candidates_and_receipt_rules() -> None:
    result = validator.validate_registry(json.loads(REGISTRY.read_text(encoding="utf-8")))

    assert result["valid"] is True
    assert all(item["candidate_count"] >= 2 for item in result["policies"].values())


def test_single_candidate_policy_fails_closed() -> None:
    broken = {
        "schema_version": "duecare.model_fallback_registry.v1",
        "policies": {
            "judge": {
                "selection": "first",
                "required_capabilities": ["structured_json"],
                "candidates": [{"route": "only-one"}],
            }
        },
        "rules": ["Record every candidate, preflight result, selected route, and failure reason."],
    }

    with pytest.raises(validator.RegistryError, match="at least two"):
        validator.validate_registry(broken)
