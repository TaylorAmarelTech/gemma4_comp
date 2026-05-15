"""Import Corpus harness — user-attached evidence CRUD."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessSpec

name = "import_corpus"
applied_layers: tuple[str, ...] = ()
capabilities: tuple[str, ...] = ()  # CRUD; multi_turn not applicable

spec = HarnessSpec(
    name=name,
    tier="secondary",
    kind="utility_surface",
    label="Import corpus utility",
    summary="CRUD over user-attached evidence and local knowledge objects.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="not_required",
    model_role="No Gemma call is made; imported evidence becomes context for Gemma-backed harnesses.",
    test_pages=(
        {"label": "Import corpus", "href": "/static/import.html"},
        {"label": "Knowledge store", "href": "/static/knowledge.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/import/upload", "summary": "Upload ZIP or text file"},
        {"method": "POST", "path": "/api/import/snippet", "summary": "Add a pasted snippet"},
        {"method": "GET", "path": "/api/import/list", "summary": "List imports"},
        {"method": "GET", "path": "/api/import/{doc_id}", "summary": "Read one import"},
        {"method": "DELETE", "path": "/api/import/{doc_id}", "summary": "Delete one import"},
    ),
    examples=(
        "Import a contract excerpt and use Chat with the Import layer enabled.",
        "List local evidence and delete stale test uploads.",
    ),
    comparison="Compare answers before and after imported evidence is available to Chat.",
    workflow=(
        "Upload or paste local evidence.",
        "Store local snippets with metadata and source IDs.",
        "Expose imported corpus rows to Chat, Process, and Knowledge flows when enabled.",
    ),
    prompt_sets=(
        "no direct Gemma prompt",
        "imported evidence becomes context for downstream prompts",
    ),
    knowledge_flow=(
        "Consumes upload schemas and emits local context snippets. This is the "
        "local evidence shelf that other Gemma-backed harnesses can read."
    ),
    model_fit=(
        "No model required. Large imported corpora should be summarized or "
        "retrieved before downstream Gemma calls to avoid long context failures."
    ),
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
