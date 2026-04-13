"""Judge protocol. See docs/architecture.md section 13.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.evaluation import EvaluationResult


@runtime_checkable
class Judge(Protocol):
    """Runtime judge: loads a fine-tuned model and scores (prompt, response) pairs.

    Implementations:
      - LlamaCppJudge      (primary, loads GGUF via llama-cpp-python)
      - TransformersJudge  (for eval baselines, full precision)
      - LiteRTJudge        (stretch goal, mobile/edge)
    """

    name: str
    model_version: str
    runtime: str  # "llama_cpp" | "transformers" | "litert"

    def warmup(self) -> None:
        """Optional: warm up the runtime before serving traffic."""
        ...

    def evaluate(self, prompt: str, candidate_response: str) -> EvaluationResult:
        ...

    def close(self) -> None:
        """Release underlying resources (model handles, file descriptors)."""
        ...
