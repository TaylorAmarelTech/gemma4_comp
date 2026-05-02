"""Smoke tests for duecare-llm-research-tools."""
from __future__ import annotations

import pytest


def test_research_tools_imports() -> None:
    try:
        from duecare.research_tools import (
            ResearchTool, ResearchResult,
            PIIFilter, PIIRejectionError,
            OpenClawTool,
            register_research_tool, get_research_tool, list_research_tools,
            RESEARCH_TOOL_REGISTRY,
        )
    except ImportError as e:
        pytest.skip(f"research_tools depends on packages not installed: {e}")
    assert ResearchTool is not None
    assert callable(register_research_tool)
    assert callable(list_research_tools)
    assert isinstance(RESEARCH_TOOL_REGISTRY, dict)


def test_pii_filter_basic() -> None:
    try:
        from duecare.research_tools import PIIFilter
    except ImportError as e:
        pytest.skip(f"research_tools depends on packages not installed: {e}")
    f = PIIFilter()
    # The filter exists and is constructible; behavior tests are in a
    # separate suite once we add fixtures.
    assert f is not None


def test_registry_lookup() -> None:
    try:
        from duecare.research_tools import (
            list_research_tools, RESEARCH_TOOL_REGISTRY,
        )
    except ImportError as e:
        pytest.skip(f"research_tools depends on packages not installed: {e}")
    listed = list_research_tools()
    assert isinstance(listed, (list, tuple))
    assert isinstance(RESEARCH_TOOL_REGISTRY, dict)
