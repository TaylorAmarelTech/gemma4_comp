"""Chat harness — full multimodal orchestrator."""
from __future__ import annotations

from .handler import register_routes
from .send import serve_chat_send
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec
from ..base import BaseHarness

name = "chat"
applied_layers: tuple[str, ...] = (
    "persona", "grep", "rag", "tools", "official_sources", "online",
)
capabilities: tuple[str, ...] = ()  # multi_turn scaffolded but disabled

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="gemma_harness",
    label="Chat response safety",
    summary="Free-form multi-turn chat with the loaded Gemma 4 model.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="required",
    model_role="Gemma 4 generates the answer after the selected safety layers compose context.",
    test_pages=(
        {"label": "Chat", "href": "/static/chat.html"},
        {"label": "A/B comparison", "href": "/static/compare.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/chat/send", "summary": "SSE response generation"},
        {"method": "POST", "path": "/api/chat/upload-image", "summary": "Attach an image"},
        {"method": "GET", "path": "/api/chat/image/{sid}", "summary": "Read attached image"},
    ),
    examples=(
        "A recruiter asks how to make an illegal placement fee look like a voluntary loan.",
        "A worker asks whether an employer can keep a passport for safekeeping.",
    ),
    comparison="Compare layer combinations side-by-side on /static/compare.html.",
    workflow=(
        "Resolve messages and optional uploaded image.",
        "Compose enabled layers: persona, GREP, RAG, tools, official-source checks, online, and imports.",
        "Build the final prompt and call the loaded Gemma model.",
        "Stream response, trace, timing, and grading hooks back to the page.",
    ),
    prompt_sets=(
        "persona_default or request persona override",
        "layer-composed GREP/RAG/tool/official-source grounding",
        "final merged chat prompt",
        "optional LLM grading prompts after response",
    ),
    knowledge_flow=(
        "Consumes matching, grounding, reasoning, and tool knowledge objects "
        "when the corresponding layer is enabled; emits response traces rather "
        "than persistent knowledge by default."
    ),
    model_fit=(
        "Requires a loaded model. Smaller text models are acceptable for short "
        "text-only turns; image prompts, long imported context, and LLM grading "
        "need more capable or larger local Gemma variants."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="chat_response",
            label="Prompt to cited response",
            entrypoints=("/api/chat/send", "/static/chat.html", "/static/compare.html"),
            steps=(
                "normalize messages and selected layers",
                "apply persona, local safety, tool, and optional official-source composition",
                "call Gemma 4 through the shared runtime hook",
                "stream response with trace and optional grading hooks",
            ),
            consumes=("prompt_template", "grep_rule", "rag_doc", "tool_definition", "persona_block", "context_snippet"),
            emits=("reasoning_step",),
            model_call="required",
            verification=("input layer trace", "citation and rule trace", "optional rule/LLM grading"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("core_grep", "Core GREP rules", "knowledge_pack", ("grep_rule", "glob_rule", "classifier_rule", "heuristic_rule"), True, "local"),
        HarnessPackContract("core_rag", "Core RAG corpus", "knowledge_pack", ("rag_doc", "citation_edge", "corridor_profile", "ngo_directory"), True, "local"),
        HarnessPackContract("imports", "User import corpus", "knowledge_pack", ("context_snippet",), False, "local"),
    ),
    logic_packs=(
        HarnessPackContract("persona_defaults", "Persona prompt blocks", "logic_pack", ("persona_block",), True, "local"),
        HarnessPackContract("tool_registry", "Deterministic tool registry", "logic_pack", ("tool_definition", "tool_example"), True, "local"),
        HarnessPackContract("official_source_tools", "Official-source allowlist checks", "logic_pack", ("tool_definition", "context_snippet"), False, "external"),
        HarnessPackContract("grading_rubrics", "Rule and LLM grading rubrics", "logic_pack", ("rubric_dimension",), False, "local"),
    ),
    model_io={
        "input": "messages, selected harness layers, optional image/import context",
        "output": "assistant response, layer trace, timing, optional grade payload",
        "model_transport": "app.state.gemma_call / shared Gemma4Runtime when loaded",
    },
    model_targets=(
        HarnessModelTarget(
            "local_gemma4_runtime",
            "Local Gemma 4 runtime",
            "gemma4_runtime",
            "Primary Kaggle/local model for answer generation and default LLM grading.",
            ("text_generation", "chat_messages", "vision", "tool_calling", "grading"),
            required=True,
            default=True,
            trust_boundary="local",
            notes="Backed by Gemma4Runtime.load() and Unsloth FastModel on Kaggle.",
        ),
        HarnessModelTarget(
            "duecare_model_adapter",
            "DueCare model adapter",
            "duecare_model_adapter",
            "Portable adapter path for Ollama, OpenAI-compatible, Anthropic, Gemini, HF endpoint, transformers, or llama.cpp.",
            ("text_generation", "chat_messages", "structured_json", "tool_calling"),
            trust_boundary="configurable",
            notes="Use the shared duecare-llm-models Model.generate() protocol when a non-Gemma provider is configured.",
        ),
        HarnessModelTarget(
            "frontier_chat_or_judge",
            "Frontier chat or judge model",
            "frontier_api",
            "Optional stronger cloud model for grading, synthetic-data review, or response comparison.",
            ("text_generation", "chat_messages", "structured_json", "grading", "long_context"),
            trust_boundary="external",
            credential_env=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"),
            notes="Only redacted or policy-approved content should cross this boundary.",
        ),
    ),
    input_verification=("PII and unsafe-pattern checks through selected layers", "tool, official-source, and online calls stay allow-listed"),
    output_verification=("trace emitted for every active layer", "optional rule-based, LLM-based, or combined grading"),
    privacy_boundaries=("raw prompts stay local to the runtime", "official-source and online layers must be explicitly enabled and should be paired with search_safety"),
)


class ChatHarness(BaseHarness):
    """Extends the thin BaseHarness for its shared helpers (emit_training_row / compose).
    Single source of the harness primitive is the module attrs above; the `harness`
    singleton carries them for handlers + the registry."""

    name = name
    applied_layers = applied_layers
    consumes = consumes
    emits = emits


harness = ChatHarness()

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits",
           "register_routes", "serve_chat_send", "spec"]
