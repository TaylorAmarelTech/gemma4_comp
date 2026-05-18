"""Bulk File Review harness: bundle analyst + graph-chat."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec

name = "process"
applied_layers: tuple[str, ...] = ("grep", "rag", "tools")
capabilities: tuple[str, ...] = ()  # multi_turn scaffolded but disabled

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="gemma_harness",
    label="Bulk file review",
    summary="Review ZIP, CSV, JSONL, text, image, and PDF bundles, extract intelligence, and ask Gemma 4 about the parsed graph.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="hybrid",
    model_role="Batch parsing is local; graph-chat and edge refinement use Gemma 4 with GREP/RAG/tools grounding.",
    test_pages=(
        {"label": "Bulk File Review", "href": "/static/process.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/process/batch", "summary": "Parse and score uploaded rows"},
        {"method": "POST", "path": "/api/process/batch/start", "summary": "Start background upload processing job"},
        {"method": "GET", "path": "/api/process/batch/status/{job_id}", "summary": "Poll upload-processing job status"},
        {"method": "POST", "path": "/api/process/graph-extract", "summary": "Run local Gemma graph-edge extraction"},
        {"method": "POST", "path": "/api/process/graph-chat", "summary": "Ask Gemma 4 about the last bundle"},
    ),
    examples=(
        "Upload a ZIP of recruiter chats, scanned IDs, and payment receipts, then inspect the OCR and vision queue.",
        "Upload a CSV of complaints and ask for the top fee-camouflage patterns.",
    ),
    comparison="Use Bulk File Review for batch output, then paste representative rows into Compare.",
    workflow=(
        "Inventory files, folders, pages, chunks, and media assets locally.",
        "Run deterministic parsing, GREP, entity extraction, folder edges, and journey-stage mapping.",
        "Classify page items and route them through the documented prompt tree when Gemma is enabled.",
        "Review extracted graph edges, knowledge candidates, and graph-chat answers with row/page provenance.",
    ),
    prompt_sets=(
        "GRAPH_CHAT_SYSTEM_PROMPT",
        "GRAPH_EDGE_PROMPT_TEMPLATES",
        "PAGE_ITEM_PROMPT_TREE: classify -> targeted extraction -> cross-document linking -> knowledge candidate",
    ),
    knowledge_flow=(
        "Consumes local knowledge files as graph/RAG context and can emit audit "
        "templates plus reviewable graph edges, RAG candidates, and knowledge-object hints."
    ),
    model_fit=(
        "Deterministic parsing works without a model. Text-only edge extraction "
        "works with smaller Gemma models over compact context. Multimodal page "
        "review, OCR+image reasoning, and exhaustive cross-document linking need "
        "a stronger multimodal-capable local runtime. A fine-tuned Gemma 4 "
        "adapter trained on reviewed document-classification and graph-edge "
        "examples can improve page routing, edge typing, and cross-document "
        "linking quality."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="bundle_review",
            label="Local bundle review",
            entrypoints=("/api/process/batch", "/api/process/batch/start", "/static/process.html"),
            steps=(
                "inventory uploaded files and media",
                "parse text, tables, images, and document chunks locally",
                "run deterministic risk/entity extraction and GREP checks",
                "emit review rows, media queue, graph candidates, and provenance",
            ),
            consumes=("grep_rule", "rag_doc", "context_snippet", "tool_definition"),
            emits=("extracted_fact", "entity_signal", "modus_operandi", "context_snippet"),
            model_call="optional",
            verification=("row/page provenance", "media queue explicitly marks unread assets", "local-only source metadata"),
        ),
        HarnessLogicPath(
            id="graph_chat",
            label="Graph chat and edge refinement",
            entrypoints=("/api/process/graph-chat", "/api/process/graph-extract"),
            steps=(
                "load last parsed bundle graph",
                "compose GREP/RAG/tool grounding",
                "ask Gemma 4 for bounded graph analysis or edge proposals",
                "return typed edges and graph-chat answer with source IDs",
            ),
            consumes=("grep_rule", "rag_doc", "corridor_profile", "ngo_directory"),
            emits=("entity_signal", "modus_operandi", "context_snippet"),
            model_call="hybrid",
            verification=("typed edge schema", "source_node/target_node evidence", "review_status on proposed edges"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("local_imports", "Uploaded local evidence", "knowledge_pack", ("context_snippet",), False, "local"),
        HarnessPackContract("process_grounding", "Process grounding packs", "knowledge_pack", ("grep_rule", "rag_doc", "corridor_profile", "ngo_directory"), True, "local"),
    ),
    logic_packs=(
        HarnessPackContract("process_prompt_tree", "Process prompt tree", "logic_pack", ("prompt_template",), True, "local"),
        HarnessPackContract("typed_edge_schema", "Typed graph edge schema", "logic_pack", ("envelope_schema",), True, "local"),
    ),
    model_io={
        "input": "case bundle summaries, parsed rows, graph state, selected user question",
        "output": "process rows, graph edges, graph-chat answer, knowledge candidates",
        "model_transport": "deterministic parser first; Gemma 4 only for graph-chat and optional edge passes",
    },
    model_targets=(
        HarnessModelTarget(
            "deterministic_parser",
            "Deterministic local parser",
            "none",
            "Default path for upload inventory, basic extraction, and source provenance.",
            ("structured_json",),
            required=True,
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "local_gemma4_runtime",
            "Local Gemma 4 graph analyst",
            "gemma4_runtime",
            "Optional local model for graph chat, edge refinement, and media-aware review. Can be loaded with a fine-tuned adapter for better document classification and bulk graph-edge generation.",
            ("text_generation", "chat_messages", "vision", "structured_json", "long_context"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "external_structured_extractor",
            "External structured extractor",
            "duecare_model_adapter",
            "Optional stronger adapter for large-document graph extraction after anonymization policy is satisfied.",
            ("text_generation", "chat_messages", "structured_json", "long_context"),
            trust_boundary="configurable",
            notes="Route external calls through anonymization and policy gates before use.",
        ),
    ),
    input_verification=("upload size/type constraints", "explicit unread-media queue", "local-only provenance tracking"),
    output_verification=("typed edge schema", "row/page/chunk grounding", "review_status for model-proposed facts"),
    privacy_boundaries=("case files remain local", "raw bundles are not submitted to the public hub"),
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
