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
    tool_name: str
    query: dict
    success: bool
    items: list[dict] = field(default_factory=list)
    """One dict per result item. Recommended keys: title, url, snippet,
    source, published_at."""
    summary: str = ""
    """One-line summary of what was found, for inclusion in a Gemma prompt."""
    error: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)
    """The unmodified upstream response, for debugging."""


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
