"""External-research tools for the Duecare harness."""
from __future__ import annotations

from duecare.research_tools.protocol import ResearchTool, ResearchResult
from duecare.research_tools.pii_filter import PIIFilter, PIIRejectionError
from duecare.research_tools.openclaw import OpenClawTool
from duecare.research_tools.web_tools import (
    WebSearchTool, WebFetchTool, WikipediaTool,
)
from duecare.research_tools.fast_search import (
    TavilySearchTool, BraveSearchTool, SerperSearchTool,
    FastWebSearchTool, get_recent_audit,
)
from duecare.research_tools.registry import (
    register_research_tool,
    get_research_tool,
    list_research_tools,
    RESEARCH_TOOL_REGISTRY,
)

__all__ = [
    "ResearchTool", "ResearchResult",
    "PIIFilter", "PIIRejectionError",
    "OpenClawTool",
    "WebSearchTool", "WebFetchTool", "WikipediaTool",
    "TavilySearchTool", "BraveSearchTool", "SerperSearchTool",
    "FastWebSearchTool", "get_recent_audit", "BrowserTool",
    "register_research_tool", "get_research_tool",
    "list_research_tools", "RESEARCH_TOOL_REGISTRY",
]
