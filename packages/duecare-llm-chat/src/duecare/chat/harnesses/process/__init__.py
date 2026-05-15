"""Bulk File Review harness: bundle analyst + graph-chat."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessSpec

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
        "a stronger multimodal-capable local runtime."
    ),
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
