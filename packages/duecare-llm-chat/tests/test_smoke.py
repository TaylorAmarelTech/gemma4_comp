"""Smoke tests for duecare-llm-chat (harness API + app constructors)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_harness_module():
    """Load harness/__init__.py directly so we don't pull in the
    fastapi-dependent duecare.chat.app at module import time. This lets
    these tests run in environments where fastapi is not installed."""
    harness_init = (Path(__file__).parent.parent / "src" / "duecare" / "chat"
                    / "harness" / "__init__.py")
    spec = importlib.util.spec_from_file_location("h", harness_init)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_harness_loads_with_expected_counts() -> None:
    """v3.16 counts. GREP jumped 49→108 with 9 new categories (H–P):
    sector-specific labour abuse, kafala extended mechanisms,
    cross-border financial flows, employer abuse patterns, document
    fraud, recruiter sales tactics, recovery-suppression and
    repatriation barriers, additional corridors (Lebanon-internal /
    Libya transit / Iraq KRG / Cyprus North / Taiwan caregiver),
    and platform/digital recruitment (online platforms, deepfake
    interviews, encrypted-platform coercion, offshore shell HR,
    cam-studio sextortion). RAG/tools/examples unchanged this bump.
    Classifier examples 46→51: 5 multimodal additions (TikTok
    recruitment, Telegram money mule, cam-studio contract,
    backdated contract, two-contract side-by-side)."""
    h = _load_harness_module()
    assert len(h.GREP_RULES) == 108
    assert len(h.RAG_CORPUS) == 33
    assert len(h._TOOL_DISPATCH) == 5
    assert len(h.EXAMPLE_PROMPTS) == 407
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
    from duecare.chat import create_app, create_classifier_app
    assert callable(create_app)
    assert callable(create_classifier_app)
