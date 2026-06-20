"""Import Corpus harness — user-attached evidence CRUD."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec
from ..base import BaseHarness

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
    logic_paths=(
        HarnessLogicPath(
            id="local_import",
            label="Local evidence import",
            entrypoints=("/api/import/upload", "/api/import/snippet", "/static/import.html"),
            steps=(
                "receive uploaded file, ZIP, or pasted snippet",
                "validate size, type, and local metadata",
                "store as local context snippets with source IDs",
                "expose snippets to chat, process, and extraction when enabled",
            ),
            consumes=("upload_schema",),
            emits=("context_snippet",),
            model_call="none",
            verification=("upload constraints", "source IDs", "delete/list/read CRUD contract"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("local_evidence_shelf", "Local imported evidence shelf", "knowledge_pack", ("context_snippet",), False, "local"),
    ),
    logic_packs=(
        HarnessPackContract("upload_schema", "Upload validation schema", "logic_pack", ("upload_schema",), True, "local"),
    ),
    model_io={
        "input": "file, ZIP, text snippet, or existing local import ID",
        "output": "local context snippets and import metadata",
        "model_transport": "none; downstream harnesses decide whether to call Gemma",
    },
    model_targets=(
        HarnessModelTarget(
            "local_import_only",
            "Local import only",
            "none",
            "Stores local evidence and exposes snippets to downstream harnesses without calling a model.",
            ("structured_json",),
            required=True,
            default=True,
            trust_boundary="local",
        ),
    ),
    input_verification=("upload schema", "file size/type limits", "local source metadata"),
    output_verification=("stable doc IDs", "delete/list/read contract", "context exposed only when selected"),
    privacy_boundaries=("imports remain local", "downstream sharing should pass through anonymization"),
)


class ImportCorpusHarness(BaseHarness):
    """Extends the thin BaseHarness for its shared helpers (emit_training_row / compose).
    Single source of the harness primitive is the module attrs above; the `harness`
    singleton carries them for handlers + the registry."""

    name = name
    applied_layers = applied_layers
    consumes = consumes
    emits = emits


harness = ImportCorpusHarness()

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
