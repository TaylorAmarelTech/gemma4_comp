"""Real-world case schema. See docs/architecture.md section 3."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Provenance


class CaseSource(BaseModel):
    """A citation for a real-world case (news article, court doc, NGO report)."""

    title: str
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    type: str  # "news", "court_doc", "ngo_report", "academic", "official"


class RealWorldCase(BaseModel):
    """A documented, anonymized trafficking / forced-labor case.

    Real-world cases are used both as training data and as a source of
    grounded prompts via the from_case prompt generator.
    """

    id: str
    title: str
    summary: str
    sector: str | None = None
    corridor: str | None = None
    origin_country: str | None = None
    destination_country: str | None = None
    year: int | None = None
    exploitation_methods: list[str] = Field(default_factory=list)
    ilo_indicators: list[str] = Field(default_factory=list)
    victim_count: int | None = None
    sources: list[CaseSource] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
    derived_prompt_ids: list[str] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)
    anonymized: bool = True
    verified: bool = False
    provenance: Provenance
