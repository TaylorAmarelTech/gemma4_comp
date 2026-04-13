"""DomainCard + Issue + ResponseExample schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from duecare.core.enums import Capability, Grade, Severity


class DomainCard(BaseModel):
    """Public-facing description of a domain pack."""

    id: str
    display_name: str
    version: str
    description: str = ""
    license: str = "MIT"
    citation: str | None = None
    owner: str = ""
    capabilities_required: set[Capability] = Field(default_factory=set)
    n_seed_prompts: int = 0
    n_evidence_items: int = 0
    n_indicators: int = 0
    n_categories: int = 0
    taxonomy_dimensions: list[str] = Field(default_factory=list)


class Issue(BaseModel):
    """A specific problem with an LLM response."""

    type: str                           # "missed_indicator", "provided_harmful_info", ...
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
    score: float                        # 0.0 .. 1.0
    explanation: str = ""
    issues: list[Issue] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
