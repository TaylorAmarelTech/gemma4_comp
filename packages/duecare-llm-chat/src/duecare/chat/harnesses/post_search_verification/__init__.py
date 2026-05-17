"""Post-search verification harness.

Search results are not facts. This harness verifies candidate result cards for
source quality, relevance, contradictions, and deanonymization risk before any
result is turned into prompt context or a KnowledgeObject.
"""
from __future__ import annotations

from .handler import register_routes
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec

name = "post_search_verification"
applied_layers: tuple[str, ...] = ()
consumes: tuple[str, ...] = (
    "context_snippet",
    "citation_edge",
    "rag_doc",
)
emits: tuple[str, ...] = (
    "context_snippet",
    "citation_edge",
    "audit_template",
)
capabilities = {
    "verify_search_results": "Score result candidates before they can become model context.",
    "score_source_quality": "Prefer official or recognized public sources and flag weak sources.",
    "detect_deanonymization_risk": "Block result sets that reintroduce direct identifiers.",
}

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="safety_gate",
    label="Post-search verification gate",
    summary="Verify online result candidates before they are injected into chat, extraction, or knowledge packs.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role="Deterministic checks run first; local Gemma can later summarize contradictions over accepted snippets.",
    test_pages=(
        {"label": "Search", "href": "/static/search.html"},
        {"label": "Harness Workbench", "href": "/static/harness.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/search/verify-results", "summary": "Verify candidate search results"},
        {"method": "GET", "path": "/api/search/verification-info", "summary": "Report verification fields and policy"},
    ),
    examples=(
        "Verify public ILO and government result cards before drafting a RAG knowledge object.",
        "Flag a low-relevance or deanonymizing search result before it reaches a model prompt.",
    ),
    comparison="Compare accepted/review/blocked result sets before and after query sanitization.",
    capabilities=capabilities,
    workflow=(
        "Receive sanitized query and normalized search result cards.",
        "Score source quality from URL/domain and snippet markers.",
        "Score relevance against the sanitized query.",
        "Flag contradictions across candidate snippets.",
        "Block results that reintroduce direct identifiers.",
        "Return accepted/review/blocked envelopes for reviewer promotion.",
    ),
    prompt_sets=(
        "deterministic source-quality and relevance policy",
        "future local Gemma contradiction-summary prompt over accepted snippets",
    ),
    knowledge_flow=(
        "Consumes candidate context/citation/RAG snippets from search and emits only "
        "accepted or review-gated snippets/citation edges plus an audit row."
    ),
    model_fit=(
        "No model is required for the first gate. Small local Gemma models can help "
        "summarize conflicts, but external models should only see sanitized snippets."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="verify_search_results",
            label="Post-search candidate verification",
            entrypoints=("/api/search/verify-results", "/static/search.html"),
            steps=(
                "receive sanitized query and normalized result cards",
                "score source quality and relevance",
                "detect contradiction markers across candidate snippets",
                "detect deanonymization risk before prompt injection",
                "return accepted, review, and blocked result envelopes",
            ),
            consumes=("context_snippet", "citation_edge", "rag_doc"),
            emits=("context_snippet", "citation_edge", "audit_template"),
            model_call="optional",
            verification=(
                "raw prompt should not be included",
                "result is candidate evidence until accepted or reviewer-promoted",
                "blocked results must not be injected into prompts",
            ),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract(
            "candidate_search_results",
            "Candidate search snippets and citations",
            "knowledge_pack",
            ("context_snippet", "citation_edge", "rag_doc"),
            True,
            "local",
        ),
    ),
    logic_packs=(
        HarnessPackContract(
            "trusted_source_policy",
            "Trusted source and result-quality policy",
            "logic_pack",
            ("prompt_template", "evaluation_metric"),
            True,
            "local",
        ),
        HarnessPackContract(
            "verification_schema",
            "Search result verification schema",
            "logic_pack",
            ("evaluation_dimension", "evaluation_metric", "audit_template"),
            True,
            "local",
        ),
    ),
    model_io={
        "input": "sanitized query plus normalized search result cards",
        "output": "accepted/review/blocked result envelopes with source quality, relevance, contradiction, and deanonymization fields",
        "model_transport": "none by default; optional local Gemma contradiction summarization over sanitized snippets",
    },
    model_targets=(
        HarnessModelTarget(
            "deterministic_result_verifier",
            "Deterministic result verifier",
            "none",
            "Required local verification before search results become prompt context.",
            ("structured_json", "safety_filtering", "evidence_tracing"),
            required=True,
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "local_gemma4_result_reviewer",
            "Local Gemma 4 result reviewer",
            "gemma4_runtime",
            "Optional local review of accepted snippets for contradiction summaries.",
            ("text_generation", "chat_messages", "evidence_tracing"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "external_result_reviewer",
            "External result reviewer",
            "frontier_api",
            "Optional external review only for sanitized snippets and public URLs.",
            ("text_generation", "chat_messages", "evidence_tracing"),
            trust_boundary="external",
            credential_env=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"),
            notes="Never send raw user prompts or private case facts to this target.",
        ),
    ),
    input_verification=("sanitized query only", "normalized result cards", "no raw private prompt"),
    output_verification=("accepted/review/blocked status", "source metadata preserved", "blocked results excluded from prompt injection"),
    privacy_boundaries=("external search output is untrusted", "raw prompt stays local", "external reviewers receive sanitized snippets only"),
)

__all__ = ["name", "applied_layers", "consumes", "emits", "capabilities", "register_routes", "spec"]
