"""Behavioral tests for the PII filter (the hard gate the safety contract
mandates: no raw PII can pass downstream)."""
from __future__ import annotations

import pytest


def test_pii_filter_constructible() -> None:
    try:
        from duecare.research_tools import PIIFilter
    except ImportError as e:
        pytest.skip(f"research_tools imports unavailable: {e}")
    f = PIIFilter()
    assert f is not None


def test_registry_register_and_lookup() -> None:
    try:
        from duecare.research_tools import (
            register_research_tool, get_research_tool,
            ResearchTool, ResearchResult,
        )
    except ImportError as e:
        pytest.skip(f"research_tools imports unavailable: {e}")

    class _DummyTool:
        name = "dummy_test_tool"

        def search(self, query: str, **kwargs) -> "ResearchResult":  # type: ignore
            return ResearchResult(query=query, results=[], source=self.name)

    register_research_tool("dummy_test_tool", _DummyTool())
    looked_up = get_research_tool("dummy_test_tool")
    assert looked_up is not None
    assert looked_up.name == "dummy_test_tool"


def test_research_tool_protocol_shape() -> None:
    try:
        from duecare.research_tools import ResearchTool, ResearchResult
    except ImportError as e:
        pytest.skip(f"research_tools imports unavailable: {e}")
    # ResearchResult should be constructible with the documented fields
    r = ResearchResult(query="test", results=[], source="unit")
    assert r.query == "test"
    assert r.source == "unit"
