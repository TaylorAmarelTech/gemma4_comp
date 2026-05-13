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
