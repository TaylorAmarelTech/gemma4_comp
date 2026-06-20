"""Knowledge Extraction harness — drafts typed KnowledgeObject envelopes."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec
from ..base import BaseHarness

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
        {"method": "POST", "path": "/api/knowledge/from-edge", "summary": "Draft a knowledge-object envelope from a Process typed edge"},
        {"method": "POST", "path": "/api/knowledge/polish-envelope", "summary": "Two-pass Gemma critique + rewrite of a draft envelope"},
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
    logic_paths=(
        HarnessLogicPath(
            id="draft_envelope",
            label="KnowledgeObject drafting",
            entrypoints=("/api/knowledge/source-file", "/api/knowledge/draft-envelope", "/api/knowledge/from-edge", "/static/knowledge.html"),
            steps=(
                "parse or receive compact source text",
                "infer useful KnowledgeObject leaf type and deterministic hints, or map a Process typed edge directly",
                "compose GREP/RAG grounding for the draft",
                "ask Gemma 4 for schema-shaped JSON when loaded",
                "validate and mark draft for human promotion",
            ),
            consumes=("grep_rule", "rag_doc", "prompt_template", "fact_template"),
            emits=("grep_rule", "rag_doc", "ngo_directory", "fact_template", "extracted_fact", "entity_signal", "context_snippet", "modus_operandi", "rubric_dimension", "citation_edge", "envelope_schema"),
            model_call="optional",
            verification=("KnowledgeObject envelope schema", "needs_review for volatile facts", "human promotion required"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("source_context", "Source and existing knowledge context", "knowledge_pack", ("grep_rule", "rag_doc", "prompt_template", "fact_template"), False, "local"),
    ),
    logic_packs=(
        HarnessPackContract("knowledge_schemas", "KnowledgeObject schemas and prompts", "logic_pack", ("envelope_schema", "prompt_template"), True, "local"),
    ),
    model_io={
        "input": "source text, target KnowledgeObject type, deterministic hints",
        "output": "draft KnowledgeObject envelope and validation metadata",
        "model_transport": "optional Gemma 4 drafter, deterministic skeleton fallback",
    },
    model_targets=(
        HarnessModelTarget(
            "deterministic_envelope_skeleton",
            "Deterministic envelope skeleton",
            "none",
            "Builds reviewable KnowledgeObject drafts without a model.",
            ("structured_json",),
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "local_gemma4_drafter",
            "Local Gemma 4 drafter",
            "gemma4_runtime",
            "Drafts schema-shaped KnowledgeObject envelopes from compact local text.",
            ("text_generation", "chat_messages", "structured_json"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "frontier_long_context_drafter",
            "Frontier long-context drafter",
            "frontier_api",
            "Optional stronger model for long IOM/TIP/court-document extraction after privacy review.",
            ("text_generation", "chat_messages", "structured_json", "long_context"),
            trust_boundary="external",
            credential_env=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"),
        ),
    ),
    input_verification=("source text size and type checks", "target type must be known"),
    output_verification=("KnowledgeObject schema validation", "review_required before promotion", "volatile facts marked for verification"),
    privacy_boundaries=("drafting stays local", "submission should pass anonymization before hub sharing"),
)


class ExtractionHarness(BaseHarness):
    """Extends the thin BaseHarness for its shared helpers (emit_training_row / compose).
    Single source of the harness primitive is the module attrs above; the `harness`
    singleton carries them for handlers + the registry."""

    name = name
    applied_layers = applied_layers
    consumes = consumes
    emits = emits


harness = ExtractionHarness()

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
