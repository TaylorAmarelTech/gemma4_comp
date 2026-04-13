"""Prompt, ResponseExample, and Issue schemas.

See docs/architecture.md section 3.3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Difficulty, Grade, Provenance, Severity


class Issue(BaseModel):
    """A specific problem with an LLM response."""

    type: str  # "missed_indicator", "provided_harmful_info", ...
    description: str
    severity: Severity
    documentation_ref: str | None = None


class ResponseExample(BaseModel):
    """A graded exemplar response for a prompt.

    A prompt may have up to 5 of these (one per Grade). They are the
    training signal for the safety judge.
    """

    text: str
    grade: Grade
    score: float  # 0.0 .. 1.0
    explanation: str
    issues: list[Issue] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)


class Prompt(BaseModel):
    """A prompt in the safety benchmark.

    Every Prompt is addressable by id and carries its full provenance and
    graded response examples.
    """

    id: str
    text: str
    category: str  # attack category (registry key)
    subcategory: str | None = None
    sector: str | None = None
    corridor: str | None = None
    difficulty: Difficulty
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_strategies: list[str] = Field(default_factory=list)
    graded_responses: dict[Grade, ResponseExample] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    provenance: Provenance
