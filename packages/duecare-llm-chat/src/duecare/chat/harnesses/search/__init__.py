"""Search harness — server-automated + client-triggered web search."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec
from ..base import BaseHarness

name = "search"
applied_layers: tuple[str, ...] = ()  # search IS the layer; doesn't compose others
capabilities: tuple[str, ...] = ()    # multi_turn (Gemma-guided) deferred to Phase 12

spec = HarnessSpec(
    name=name,
    tier="secondary",
    kind="utility_surface",
    label="Search utility",
    summary="Web search backend access after search_safety has sanitized the query.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="downstream",
    model_role="The search call itself is not a Gemma harness; Gemma is used downstream when results are drafted into knowledge or injected into chat.",
    test_pages=(
        {"label": "Search", "href": "/static/search.html"},
        {"label": "Search safety", "href": "/static/search-safety.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/search/client", "summary": "User-triggered search"},
        {"method": "POST", "path": "/api/search/server", "summary": "Automated/server search"},
        {"method": "GET", "path": "/api/search/backends", "summary": "Backend availability"},
    ),
    examples=(
        "Search for a public ILO citation after the query has been sanitized.",
        "Draft search snippets into reviewed RAG knowledge objects with Gemma.",
    ),
    comparison="Compare backend result sets; use Chat/Compare for Gemma response differences.",
    workflow=(
        "Receive sanitized query from Search Safety or caller.",
        "Select first available backend or requested backend.",
        "Return source cards and result set metadata.",
        "Optionally draft reviewed knowledge from snippets through Knowledge Extraction.",
    ),
    prompt_sets=(
        "no direct Gemma prompt in the search call",
        "downstream result-to-knowledge drafting uses extraction prompts",
    ),
    knowledge_flow=(
        "Consumes corridor/contact/context knowledge for source planning when "
        "available and emits result sets plus candidate citation/context snippets."
    ),
    model_fit=(
        "Search does not require Gemma. Optional query rephrasing belongs to "
        "Search Safety, and deeper result refinement belongs to Knowledge Extraction."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="run_sanitized_search",
            label="Sanitized search execution",
            entrypoints=("/api/search/client", "/api/search/server", "/static/search.html"),
            steps=(
                "receive sanitized query or require caller-provided safety status",
                "select available backend",
                "normalize result cards and source metadata",
                "return candidates for human review or downstream extraction",
            ),
            consumes=("corridor_profile", "ngo_directory", "context_snippet"),
            emits=("context_snippet", "citation_edge"),
            model_call="none",
            verification=("caller should pass through search_safety first", "result cards preserve URL/source metadata"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("search_context", "Search planning context", "knowledge_pack", ("corridor_profile", "ngo_directory", "context_snippet"), False, "local"),
    ),
    logic_packs=(
        HarnessPackContract("backend_registry", "Search backend registry", "logic_pack", ("tool_definition",), True, "local"),
    ),
    model_io={
        "input": "sanitized query, selected backend, optional source constraints",
        "output": "normalized result set and candidate snippets",
        "model_transport": "none in search call; downstream extraction/chat may call Gemma",
    },
    model_targets=(
        HarnessModelTarget(
            "search_backend_only",
            "Search backend only",
            "none",
            "Search executes against a selected backend and does not call an LLM directly.",
            ("structured_json",),
            required=True,
            default=True,
            trust_boundary="external",
            notes="Raw prompts should not enter this target; use search_safety first.",
        ),
    ),
    input_verification=("query should be sanitized by search_safety", "backend allow-list"),
    output_verification=("source URL/title/snippet preserved", "results are candidates, not verified facts"),
    privacy_boundaries=("third-party backend receives only sanitized query", "raw prompt should not be submitted here"),
)


class SearchHarness(BaseHarness):
    """Extends the thin BaseHarness for its shared helpers (emit_training_row / compose).
    Single source of the harness primitive is the module attrs above; the `harness`
    singleton carries them for handlers + the registry."""

    name = name
    applied_layers = applied_layers
    consumes = consumes
    emits = emits


harness = SearchHarness()

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
