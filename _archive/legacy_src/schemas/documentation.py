"""Documentation index schema (ILO, IOM, Palermo, national law).

See docs/architecture.md section 3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Provenance


class Provision(BaseModel):
    """A specific provision (section/article) inside a law or regulation."""

    identifier: str  # "Art. 7", "Sec. 6(a)", etc.
    title: str | None = None
    text: str
    key_terms: list[str] = Field(default_factory=list)


class Documentation(BaseModel):
    """A legal or regulatory document referenced by prompts and grades.

    Examples: ILO C181, UN Palermo Protocol, Saudi Labor Law Art. 40,
    Philippines RA 8042 Sec. 6, TVPA.
    """

    id: str
    title: str
    type: str  # "law", "regulation", "guideline", "convention", "report"
    organization: str
    summary: str
    full_text: str | None = None
    source_url: str | None = None
    jurisdiction: str  # "international", "regional", "national"
    countries: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    topics: list[str] = Field(default_factory=list)
    ilo_indicators: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    key_provisions: list[Provision] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    provenance: Provenance
