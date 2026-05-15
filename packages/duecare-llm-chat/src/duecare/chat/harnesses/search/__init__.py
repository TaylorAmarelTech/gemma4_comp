"""Search harness — server-automated + client-triggered web search."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessSpec

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
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
