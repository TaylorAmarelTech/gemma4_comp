"""Knowledge Extraction harness — drafts typed KnowledgeObject envelopes."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessSpec

name = "extraction"
applied_layers: tuple[str, ...] = ("grep", "rag")
capabilities: tuple[str, ...] = ()  # single-shot; multi_turn not applicable

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="gemma_harness",
    label="Knowledge extraction",
    summary="Draft standardized, reviewable knowledge-object envelopes from source bundles or compact text.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role="Gemma 4 drafts envelope content; without a model the endpoint returns reviewable deterministic suggestions.",
    test_pages=(
        {"label": "Knowledge extraction", "href": "/static/knowledge.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/knowledge/source-file", "summary": "Parse uploaded source files through the process parser"},
        {"method": "POST", "path": "/api/knowledge/draft-envelope", "summary": "Draft a knowledge-object envelope"},
        {"method": "POST", "path": "/api/knowledge/promote", "summary": "Promote reviewed draft to local knowledge store"},
        {"method": "POST", "path": "/api/knowledge/import", "summary": "Import knowledge files ZIP"},
    ),
    examples=(
        "Turn a new fee-cap citation into a rag_doc or context_snippet envelope.",
        "Draft a grep_rule from a recurring recruiter phrase found in case notes.",
        "Promote a non-PII entity_signal or modus_operandi pattern for later graph/RAG use.",
    ),
    comparison="Compare extracted knowledge by promoting locally, then rerunning Chat/Compare or Process graph extraction.",
    workflow=(
        "Upload source bundle or paste compact source text.",
        "Reuse Process parsing to create source summaries and deterministic hints.",
        "Auto-suggest useful leaf types and draft JSON content with Gemma when loaded.",
        "Human reviewer promotes useful envelopes, then exports knowledge files or shares after anonymization.",
    ),
    prompt_sets=(
        "auto leaf inference over text",
        "EXTRACTION_SYSTEM_PROMPT per target KnowledgeObject type",
        "schema hints for grep_rule, rag_doc, fact_template, extracted_fact, entity_signal, and modus_operandi",
    ),
    knowledge_flow=(
        "Consumes existing GREP/RAG/prompt/fact knowledge for grounding and "
        "emits reusable matching, grounding, reasoning, evaluation, input, and "
        "output knowledge objects after reviewer promotion."
    ),
    model_fit=(
        "Works deterministically without a model. Smaller text models are best "
        "for compact summaries and single envelopes. Media-derived claims, "
        "current contacts, and volatile legal facts should remain needs_review "
        "until verified through source documents or stronger local processing."
    ),
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
