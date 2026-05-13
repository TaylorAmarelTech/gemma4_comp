"""Harness contract.

Every harness module exposes the following from its ``__init__.py``:

REQUIRED
  name: str
      Canonical short name (chat / process / extraction / ...).

  applied_layers: tuple[str, ...]
      Which safety layers this harness composes via _layers.compose_layers.
      Allowed values: persona, grep, rag, tools, online. Empty tuple
      means "by design, no safety-layer fan-out" (e.g., the anonymization
      gate).

  register_routes(app) -> None
      Attaches this harness's FastAPI routes to ``app``. For notebook-
      style kernels with no FastAPI surface, this can be a no-op.

OPTIONAL (per-harness extensions)
  tools.list_tools() -> list[dict]
      Function-calling tools specific to this harness. Pulled into
      Gemma 4's function-call layer when toggles.tools is on.

  knowledge.manifest() -> dict
      KnowledgeObject types this harness emits and consumes.

  evaluation.rubric / evaluation.examples
      Per-harness grading rubric + golden examples. A bench-and-tune
      kernel can pick from this to run targeted evaluations.

  _training_log.log_interaction(harness=..., input_payload=...,
                                output_payload=..., applied_layers=...,
                                trace=..., anonymize=True)
      Per-harness JSONL training-data emission. Called from each
      harness's handler at completion. Default-on so every interaction
      becomes labeled training data for that specific safety task.

The optional extensions enable per-harness fine-tuning data, per-harness
evaluation runs, and per-harness tool composition without bloating the
core contract.
"""
from __future__ import annotations

from typing import Any, Protocol


class HarnessBase(Protocol):
    """Minimal contract every harness module implements."""

    name: str
    applied_layers: tuple[str, ...]

    def register_routes(self, app: Any) -> None:
        """Attach this harness's routes to a FastAPI app."""
        ...
