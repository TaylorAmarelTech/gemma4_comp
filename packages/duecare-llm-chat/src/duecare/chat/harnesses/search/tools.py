"""Function-calling tools the search harness contributes."""
from __future__ import annotations


TOOLS: list[dict] = [
    {
        "name": "web_search",
        "description": (
            "Search the public web via the DueCare search harness. "
            "Returns ranked results with title + URL + snippet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_n": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
]


def list_tools() -> list[dict]:
    return list(TOOLS)
