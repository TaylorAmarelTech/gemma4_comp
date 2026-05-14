"""Search-safety harness -- sanitize a query BEFORE it leaves the kernel.

Threat model: the Online and Search surfaces send the user's query
text to a third-party backend (SearXNG, Brave, Tavily, DuckDuckGo).
If the user pastes confidential info into a search box -- a real
worker name, a passport number, a private contact -- that data
leaks the moment the query is dispatched. This harness intercepts
the query, redacts PII via the same regex + NER stack as the
Anonymization harness, optionally asks Gemma to rephrase the query
in a generalized way, and returns the sanitized version PLUS an
audit record of what was redacted.

Contract (rule_70 / docs/harness_pattern.md):
  name             -- canonical short name
  applied_layers   -- which safety layers fire (none -- this harness
                       IS a safety layer; it doesn't run inside the
                       layered composition)
  consumes         -- KnowledgeObject leaf types read
  emits            -- KnowledgeObject leaf types produced
  capabilities     -- short description per workflow
  register_routes  -- attach FastAPI routes
"""
from __future__ import annotations

from .handler import register_routes

name = "search_safety"
applied_layers: tuple[str, ...] = ()  # this IS a layer, not a consumer of layers
consumes: tuple[str, ...] = (
    "grep_rule",          # PII patterns
    "prompt_template",    # Gemma rephrase prompt
)
emits: tuple[str, ...] = (
    "audit_template",     # per-sanitize audit row
)
capabilities = {
    "sanitize_query": (
        "Strip PII and confidential markers from a search query "
        "before it reaches any external backend. Returns a sanitized "
        "query and an audit record. Optionally invokes Gemma to "
        "rephrase the query in a more generalized form."
    ),
    "block_query": (
        "If the query carries unredactable signals (e.g. a passport "
        "number with no safe generalization), block the search and "
        "return a reason rather than letting it leak."
    ),
}

__all__ = [
    "name", "applied_layers", "consumes", "emits", "capabilities",
    "register_routes",
]
