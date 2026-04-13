"""Evaluation result schema.

See docs/architecture.md section 3.4.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Grade
from .prompts import Issue


class EvaluationResult(BaseModel):
    """The output of a Grader or a runtime Judge.

    All runtime judges (llama.cpp, transformers, LiteRT) and all Graders
    produce one of these. Serves as the shared contract between training-
    time scoring and inference-time scoring.
    """

    prompt_id: str
    candidate_response: str
    grade: Grade
    score: float  # 0.0 .. 1.0
    explanation: str
    issues: list[Issue] = Field(default_factory=list)
    missed_indicators: list[str] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
    similarity_scores: dict[Grade, float] = Field(default_factory=dict)
    judge_model: str
    judge_method: str  # "llama_cpp" | "transformers" | "litert" | "rule_based" | ...
    eval_duration_ms: int = 0
