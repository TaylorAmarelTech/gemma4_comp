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
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec

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

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="safety_gate",
    label="Search safety gate",
    summary="Sanitize outbound search queries before they reach a third-party backend.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role="Regex redaction is mandatory; Gemma 4 can optionally rephrase the redacted query.",
    test_pages=(
        {"label": "Search safety", "href": "/static/search-safety.html"},
        {"label": "Search", "href": "/static/search.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/search/sanitize", "summary": "Redact and optionally rephrase a query"},
        {"method": "GET", "path": "/api/search/safety-info", "summary": "Report safety wiring and patterns"},
    ),
    examples=(
        "Sanitize a query containing a phone number, passport number, and destination corridor.",
        "Ask Gemma to generalize a redacted query before web search.",
    ),
    comparison="Run strict vs Gemma-rephrased sanitization on /static/search-safety.html.",
    capabilities=capabilities,
    workflow=(
        "Receive raw search query inside the kernel.",
        "Run deterministic regex PII redaction and record sha256-only audit metadata.",
        "Optionally ask Gemma to rephrase the redacted query in a general form.",
        "Return sanitized query for Search or Online layers; block future unredactable cases.",
    ),
    prompt_sets=(
        "regex redaction catalog",
        "optional Gemma rephrase prompt over already-redacted query",
    ),
    knowledge_flow=(
        "Consumes PII pattern and prompt-template knowledge when configured; "
        "emits sanitized queries and redaction audit records, not source evidence."
    ),
    model_fit=(
        "Strict redaction works without Gemma. Optional rephrasing works with "
        "small text models, but the sanitized query should still avoid private "
        "details before any external backend call."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="sanitize_query",
            label="Outbound search query sanitization",
            entrypoints=("/api/search/sanitize", "/static/search-safety.html"),
            steps=(
                "receive raw search intent inside the local runtime",
                "redact PII and confidential markers deterministically",
                "optionally ask Gemma 4 to generalize the already-redacted query",
                "block the query if safe generalization is not possible",
                "return sanitized query and audit metadata",
            ),
            consumes=("grep_rule", "prompt_template"),
            emits=("audit_template",),
            model_call="optional",
            verification=("PII redaction before backend call", "block unredactable queries", "audit redacted types only"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("privacy_patterns", "PII and confidentiality patterns", "logic_pack", ("grep_rule",), True, "local"),
    ),
    logic_packs=(
        HarnessPackContract("query_rewrite_prompt", "Safe query rewrite prompt", "logic_pack", ("prompt_template",), False, "local"),
    ),
    model_io={
        "input": "raw search intent or already-redacted query",
        "output": "sanitized query, redaction audit, block reason if unsafe",
        "model_transport": "optional Gemma 4 rephrase over redacted query only",
    },
    model_targets=(
        HarnessModelTarget(
            "deterministic_query_sanitizer",
            "Deterministic query sanitizer",
            "none",
            "Required local query redaction before any third-party search backend.",
            ("privacy_review", "query_rewrite", "structured_json"),
            required=True,
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "local_gemma4_query_rewriter",
            "Local Gemma 4 query rewriter",
            "gemma4_runtime",
            "Optional rewrite of an already-redacted query into generalized search terms.",
            ("text_generation", "chat_messages", "query_rewrite"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "external_query_rewriter",
            "External query rewriter",
            "frontier_api",
            "Optional rewrite only after direct identifiers are removed locally.",
            ("text_generation", "chat_messages", "query_rewrite"),
            trust_boundary="external",
            credential_env=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"),
        ),
    ),
    input_verification=("redact before any third-party backend", "detect passport/email/phone/address markers"),
    output_verification=("sanitized query contains no direct identifiers", "unsafe queries can be blocked"),
    privacy_boundaries=("external search sees only sanitized query", "raw search intent stays local"),
)

__all__ = [
    "name", "applied_layers", "consumes", "emits", "capabilities",
    "register_routes", "spec",
]
