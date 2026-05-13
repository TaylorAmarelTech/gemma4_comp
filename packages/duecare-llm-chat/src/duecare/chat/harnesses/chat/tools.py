"""Tools specific to the chat harness.

Function-calling tools that Gemma 4 invokes when toggles.tools is on AND
this harness is the active surface. Wire into app.state.tools_call at
create_app time, or expose as ``list_tools()`` for the chat orchestrator
to merge into the global tool registry.

Default: empty list (no harness-specific tools yet).
"""
from __future__ import annotations


TOOLS: list[dict] = []


def list_tools() -> list[dict]:
    """Return tool specs this harness contributes to function-calling."""
    return list(TOOLS)
