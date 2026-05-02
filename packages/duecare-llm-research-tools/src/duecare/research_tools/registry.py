"""Research-tool registry. Mirrors the reactive-trigger registry so the
harness can pick tools by name."""
from __future__ import annotations

from duecare.research_tools.protocol import ResearchTool


RESEARCH_TOOL_REGISTRY: dict[str, ResearchTool] = {}


def register_research_tool(name: str, tool: ResearchTool) -> None:
    """Register (or replace) a research tool by name."""
    RESEARCH_TOOL_REGISTRY[name] = tool


def get_research_tool(name: str) -> ResearchTool | None:
    return RESEARCH_TOOL_REGISTRY.get(name)


def list_research_tools() -> list[str]:
    return sorted(RESEARCH_TOOL_REGISTRY.keys())
