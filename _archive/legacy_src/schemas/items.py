"""Item lifecycle schemas: Raw -> Staging -> Classified -> Safe.

See docs/architecture.md section 3.2.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import AttackCategory, Difficulty, ItemType, Provenance


class RawItem(BaseModel):
    """Direct output of a Source connector. Untrusted, unstructured."""

    id: str
    type: ItemType
    content: dict
    provenance: Provenance


class StagingItem(BaseModel):
    """Post-normalization, pre-classification.

    Has canonical `text` + `structured` fields and a content checksum.
    Duplicates (by checksum) are linked via `duplicate_of`.
    """

    id: str
    type: ItemType
    text: str
    structured: dict = Field(default_factory=dict)
    provenance: Provenance
    duplicate_of: str | None = None


class ClassifiedItem(BaseModel):
    """Post-classification. Carries labels but still contains raw PII."""

    id: str
    type: ItemType
    text: str
    structured: dict = Field(default_factory=dict)
    sector: str | None = None
    corridor: str | None = None
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_categories: list[AttackCategory] = Field(default_factory=list)
    difficulty: Difficulty | None = None
    classifier_confidence: dict[str, float] = Field(default_factory=dict)
    unclassified: bool = False
    provenance: Provenance


class SafeItem(BaseModel):
    """Post-anonymization. The only item type allowed downstream of anon.

    Nothing that has not passed through the anonymization verifier may be
    written as a SafeItem.
    """

    id: str
    type: ItemType
    text: str  # redacted
    structured: dict = Field(default_factory=dict)  # redacted
    sector: str | None = None
    corridor: str | None = None
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_categories: list[AttackCategory] = Field(default_factory=list)
    difficulty: Difficulty | None = None
    provenance: Provenance
    anon_version: str
    anon_passed_verifier: bool
