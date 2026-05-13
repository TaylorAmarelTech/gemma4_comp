"""Function-calling tools contributed by the process harness."""
from __future__ import annotations


TOOLS: list[dict] = [
    {
        "name": "bundle_top_corridors",
        "description": (
            "Return the top migration corridors mentioned in the most "
            "recent uploaded bundle. Use when answering 'which corridors "
            "appear in this case data?'."
        ),
        "parameters": {
            "type": "object",
            "properties": {"top_n": {"type": "integer", "default": 5}},
            "required": [],
        },
    },
    {
        "name": "bundle_top_grep_rules",
        "description": (
            "Return the GREP rule_ids that fired most often across the "
            "most recent uploaded bundle. Use when answering 'what are "
            "the most common indicators in this batch?'."
        ),
        "parameters": {
            "type": "object",
            "properties": {"top_n": {"type": "integer", "default": 10}},
            "required": [],
        },
    },
]


def list_tools() -> list[dict]:
    return list(TOOLS)
