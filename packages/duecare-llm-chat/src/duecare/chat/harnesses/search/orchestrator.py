"""Gemma-guided search orchestrator (Phase 12 — DEFERRED).

Agentic loop: user question -> Gemma rewrites query -> search ->
Gemma evaluates -> maybe re-search -> Gemma synthesizes answer.

For Phase 11 the search harness is deterministic. The orchestrator
raises NotImplementedError so any accidental call surfaces deferred status.
"""
from __future__ import annotations

from typing import Any


def gemma_guided_search(app: Any, question: str, *, max_steps: int = 3) -> dict:
    """DEFERRED to Phase 12."""
    raise NotImplementedError(
        "Gemma-guided search orchestration is scheduled for Phase 12. "
        "Use POST /api/search/{server,client} for the deterministic path."
    )
