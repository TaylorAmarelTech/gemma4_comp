"""Smoke tests for duecare-llm-engine."""
from __future__ import annotations

import pytest


def test_engine_imports() -> None:
    try:
        from duecare.engine import (
            Document,
            Edge,
            Engine,
            EngineConfig,
            Entity,
            Finding,
            Run,
        )
    except ImportError as e:
        pytest.skip(f"engine depends on packages not installed: {e}")
    assert Engine is not None
    assert EngineConfig is not None
    for cls in (Run, Document, Entity, Edge, Finding):
        assert cls is not None


def test_engine_config_constructible() -> None:
    try:
        from duecare.engine import EngineConfig
    except ImportError as e:
        pytest.skip(f"engine depends on packages not installed: {e}")
    cfg = EngineConfig()
    assert cfg is not None
    assert cfg.model == "google/gemma-4-E4B-it"
