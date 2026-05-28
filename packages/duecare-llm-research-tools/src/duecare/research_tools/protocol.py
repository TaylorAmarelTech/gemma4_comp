"""ResearchTool protocol -- common interface every external-research
tool implements so the harness can call them uniformly."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class ResearchResult:
    """Normalised output from any research tool. Tools wrap their
    native response in this shape."""
    tool_name: str = ""
    query: dict | str = field(default_factory=dict)
    success: bool = True
    items: list[dict] = field(default_factory=list)
    """One dict per result item. Recommended keys: title, url, snippet,
    source, published_at."""
    results: list[dict] | None = None
    """Backward-compatible alias for items used by older tools/tests."""
    source: str = ""
    """Backward-compatible alias for tool_name used by older tools/tests."""
    summary: str = ""
    """One-line summary of what was found, for inclusion in a Gemma prompt."""
    error: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)
    """The unmodified upstream response, for debugging."""

    def __post_init__(self) -> None:
        if self.results is not None and not self.items:
            self.items = list(self.results)
        elif self.results is None:
            self.results = self.items
        if self.source and not self.tool_name:
            self.tool_name = self.source
        elif self.tool_name and not self.source:
            self.source = self.tool_name


@runtime_checkable
class ResearchTool(Protocol):
    """Every research tool implements this protocol."""

    name: str
    description: str

    def query(self, **kwargs: Any) -> ResearchResult:
        """Run the query. Implementations MUST run their PII filter
        BEFORE any network call. Return a ResearchResult with
        success=False (and `error` set) if the query was rejected or
        the upstream call failed."""
        ...
