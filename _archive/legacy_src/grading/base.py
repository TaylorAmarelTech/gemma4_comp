"""Grader protocol. See docs/architecture.md section 10.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.evaluation import EvaluationResult
from src.schemas.prompts import Prompt


@runtime_checkable
class Grader(Protocol):
    """Scores a candidate response against a prompt and returns an EvaluationResult.

    Graders are the core signal source: they are used both to populate
    graded response examples for the training dataset and to evaluate the
    fine-tuned judge at benchmark time.
    """

    name: str
    version: str

    def grade(self, prompt: Prompt, candidate_response: str) -> EvaluationResult:
        ...
