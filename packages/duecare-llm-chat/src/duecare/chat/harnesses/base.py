"""Harness contract — Protocol (minimum) + BaseHarness class (opt-in helpers).

REQUIRED on every harness module __init__.py:
  name: str                          canonical short name
  applied_layers: tuple[str, ...]    subset of persona/grep/rag/tools/online
  register_routes(app) -> None       attaches FastAPI routes (no-op OK)

OPTIONAL (per-harness extensions):
  consumes: tuple[str, ...]    KnowledgeObject types this harness reads
  emits: tuple[str, ...]       KnowledgeObject types this harness writes
  tools.list_tools()           function-calling tools
  knowledge.manifest()         {"emits": [...], "consumes": [...]}
  evaluation.rubric / examples per-harness grading
  _training_log.log_interaction() per-task JSONL emission
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class HarnessBase(Protocol):
    """Structural-typing contract every harness module satisfies."""

    name: str
    applied_layers: tuple[str, ...]

    def register_routes(self, app: Any) -> None:
        """Attach this harness's routes to a FastAPI app."""
        ...


class BaseHarness:
    """Opt-in convenience base. Subclasses set name/applied_layers/consumes/emits
    and override register_routes(app). Inherits 3 shared helpers.
    """

    name: str = ""
    applied_layers: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    emits: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()  # multi_turn, streaming, function_calling, multimodal

    def supports(self, capability: str) -> bool:
        """Return True when this harness declares the named capability."""
        return capability in self.capabilities

    def register_routes(self, app: Any) -> None:  # pragma: no cover
        raise NotImplementedError(
            f"{type(self).__name__}.register_routes must be overridden"
        )

    def emit_training_row(
        self,
        *,
        input_payload: Any,
        output_payload: Any,
        applied_layers: dict | None = None,
        trace: dict | None = None,
        anonymize: bool = True,
        extra: dict | None = None,
    ) -> Any:
        """Append one JSONL row to /kaggle/working/training/<name>.jsonl."""
        try:
            from ._training_log import log_interaction
            return log_interaction(
                self.name,
                input_payload=input_payload,
                output_payload=output_payload,
                applied_layers=applied_layers,
                trace=trace,
                anonymize=anonymize,
                extra=extra,
            )
        except Exception:
            return None

    def compose(
        self,
        app: Any,
        text: str,
        *,
        layers: tuple[str, ...] | list[str] | None = None,
    ) -> dict:
        """Fan out safety layers; defaults to this harness's applied_layers."""
        from ._layers import compose_layers
        return compose_layers(
            app, text, layers=layers or self.applied_layers,
        )

    def load_knowledge(self, app: Any, ko_type: str) -> list[dict]:
        """Read runtime knowledge extras for one KO type."""
        attr = f"knowledge_extras_{ko_type.replace('_rule', '')}"
        return getattr(app.state, attr, None) or []


@dataclass(frozen=True)
class HarnessSpec:
    """User-facing contract for one harness surface.

    The spec lives beside the harness implementation, so routes, prompt
    paths, knowledge consumption, model-fit limits, and examples can evolve
    together. `/api/harnesses` serializes this object for the Harness
    Workbench and documentation pages.
    """

    name: str
    tier: str
    kind: str
    label: str
    summary: str
    applied_layers: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    emits: tuple[str, ...] = ()
    gemma_mode: str = "not_required"
    model_role: str = ""
    test_pages: tuple[dict[str, str], ...] = ()
    endpoints: tuple[dict[str, str], ...] = ()
    examples: tuple[str, ...] = ()
    comparison: str = ""
    capabilities: tuple[str, ...] | Mapping[str, str] = ()
    workflow: tuple[str, ...] = ()
    prompt_sets: tuple[str, ...] = ()
    knowledge_flow: str = ""
    model_fit: str = ""

    def to_contract(
        self,
        *,
        register_routes: bool = False,
        model_loaded: bool = False,
        gemma_available: bool = False,
    ) -> dict[str, Any]:
        if isinstance(self.capabilities, Mapping):
            capabilities: list[str] | dict[str, str] = dict(self.capabilities)
        else:
            capabilities = list(self.capabilities)
        return {
            "name": self.name,
            "tier": self.tier,
            "kind": self.kind,
            "label": self.label,
            "summary": self.summary,
            "applied_layers": list(self.applied_layers),
            "consumes": list(self.consumes),
            "emits": list(self.emits),
            "gemma_mode": self.gemma_mode,
            "model_role": self.model_role,
            "test_pages": list(self.test_pages),
            "endpoints": list(self.endpoints),
            "examples": list(self.examples),
            "comparison": self.comparison,
            "capabilities": capabilities,
            "workflow": list(self.workflow),
            "prompt_sets": list(self.prompt_sets),
            "knowledge_flow": self.knowledge_flow,
            "model_fit": self.model_fit,
            "register_routes": register_routes,
            "model_loaded": model_loaded,
            "gemma_available": gemma_available,
        }


def _tuple(value: Any) -> tuple:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def spec_from_mapping(data: Mapping[str, Any]) -> HarnessSpec:
    """Coerce legacy dict metadata into a `HarnessSpec`."""
    return HarnessSpec(
        name=str(data.get("name") or ""),
        tier=str(data.get("tier") or "secondary"),
        kind=str(data.get("kind") or "utility_surface"),
        label=str(data.get("label") or data.get("name") or ""),
        summary=str(data.get("summary") or ""),
        applied_layers=_tuple(data.get("applied_layers")),
        consumes=_tuple(data.get("consumes")),
        emits=_tuple(data.get("emits")),
        gemma_mode=str(data.get("gemma_mode") or "not_required"),
        model_role=str(data.get("model_role") or ""),
        test_pages=_tuple(data.get("test_pages")),
        endpoints=_tuple(data.get("endpoints")),
        examples=_tuple(data.get("examples")),
        comparison=str(data.get("comparison") or ""),
        capabilities=data.get("capabilities") or (),
        workflow=_tuple(data.get("workflow")),
        prompt_sets=_tuple(data.get("prompt_sets")),
        knowledge_flow=str(data.get("knowledge_flow") or ""),
        model_fit=str(data.get("model_fit") or ""),
    )


def contract_from_module(
    module: Any,
    *,
    fallback: Mapping[str, Any] | None = None,
    model_loaded: bool = False,
    gemma_available: bool = False,
) -> dict[str, Any]:
    """Return a JSON-safe contract for a harness module.

    New harnesses should export `spec = HarnessSpec(...)`. The fallback path
    keeps older modules working while the codebase migrates incrementally.
    Runtime exports remain authoritative for applied layers and knowledge
    consumption/emission declarations.
    """
    raw_spec = getattr(module, "spec", None)
    if isinstance(raw_spec, HarnessSpec):
        spec = raw_spec
    elif isinstance(raw_spec, Mapping):
        spec = spec_from_mapping(raw_spec)
    elif fallback:
        spec = spec_from_mapping(fallback)
    else:
        spec = HarnessSpec(
            name=str(getattr(module, "name", "")),
            tier="secondary",
            kind="utility_surface",
            label=str(getattr(module, "name", "")),
            summary="",
            applied_layers=_tuple(getattr(module, "applied_layers", ())),
            consumes=_tuple(getattr(module, "consumes", ())),
            emits=_tuple(getattr(module, "emits", ())),
            capabilities=getattr(module, "capabilities", ()) or (),
        )

    applied_layers = _tuple(getattr(module, "applied_layers", spec.applied_layers))
    consumes = _tuple(getattr(module, "consumes", spec.consumes))
    emits = _tuple(getattr(module, "emits", spec.emits))
    capabilities = getattr(module, "capabilities", spec.capabilities) or ()
    if (
        applied_layers != spec.applied_layers
        or consumes != spec.consumes
        or emits != spec.emits
        or capabilities != spec.capabilities
    ):
        spec = HarnessSpec(
            name=spec.name,
            tier=spec.tier,
            kind=spec.kind,
            label=spec.label,
            summary=spec.summary,
            applied_layers=applied_layers,
            consumes=consumes,
            emits=emits,
            gemma_mode=spec.gemma_mode,
            model_role=spec.model_role,
            test_pages=spec.test_pages,
            endpoints=spec.endpoints,
            examples=spec.examples,
            comparison=spec.comparison,
            capabilities=capabilities,
            workflow=spec.workflow,
            prompt_sets=spec.prompt_sets,
            knowledge_flow=spec.knowledge_flow,
            model_fit=spec.model_fit,
        )
    return spec.to_contract(
        register_routes=callable(getattr(module, "register_routes", None)),
        model_loaded=model_loaded,
        gemma_available=gemma_available,
    )
