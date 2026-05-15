"""Smoke tests for duecare-llm-chat (harness API + app constructors)."""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


def _load_harness_module():
    """Load harness/__init__.py directly so we don't pull in the
    fastapi-dependent duecare.chat.app at module import time. This lets
    these tests run in environments where fastapi is not installed."""
    pkg_root = Path(__file__).parent.parent / "src"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    if "duecare" not in sys.modules:
        duecare = types.ModuleType("duecare")
        duecare.__path__ = [str(pkg_root / "duecare")]
        sys.modules["duecare"] = duecare
    if "duecare.chat" not in sys.modules:
        duecare_chat = types.ModuleType("duecare.chat")
        duecare_chat.__path__ = [str(pkg_root / "duecare" / "chat")]
        sys.modules["duecare.chat"] = duecare_chat
    return importlib.import_module("duecare.chat.harness")


def test_harness_loads_with_expected_counts() -> None:
    """Current wheel harness counts stay pinned for demo reproducibility."""
    h = _load_harness_module()
    assert len(h.GREP_RULES) == 162
    assert len(h.RAG_CORPUS) == 55
    assert len(h._TOOL_DISPATCH) == 5
    assert len(h.EXAMPLE_PROMPTS) == 587
    assert len(h.RUBRICS_5TIER) == 207
    assert len(h.RUBRICS_REQUIRED) == 6
    assert len(h.CLASSIFIER_EXAMPLES) == 54


def test_harness_lookup_data_present() -> None:
    h = _load_harness_module()
    assert len(h.CORRIDOR_FEE_CAPS) >= 7
    assert len(h.FEE_CAMOUFLAGE_DICT) >= 16
    assert len(h.NGO_INTAKE) >= 4
    assert len(h.ILO_INDICATORS) >= 11


def test_default_harness_callable_keys() -> None:
    h = _load_harness_module()
    out = h.default_harness()
    for key in ("grep_call", "rag_call", "tools_call",
                "grep_catalog", "rag_catalog", "tools_catalog",
                "example_prompts", "layer_docs"):
        assert key in out
    assert callable(out["grep_call"])
    assert callable(out["rag_call"])
    assert callable(out["tools_call"])


def test_grep_call_smoke() -> None:
    h = _load_harness_module()
    out = h.default_harness()
    res = out["grep_call"](
        "I run an agency in Hong Kong charging 68% APR for placement loans")
    assert isinstance(res, dict)
    assert "hits" in res
    assert isinstance(res["hits"], list)


def test_app_constructors_importable() -> None:
    """Importing app + classifier needs fastapi installed; skip if not."""
    pytest.importorskip("fastapi")
    app_mod = importlib.import_module("duecare.chat.app")
    classifier_mod = importlib.import_module("duecare.chat.classifier")
    assert callable(app_mod.create_app)
    assert callable(classifier_mod.create_classifier_app)
