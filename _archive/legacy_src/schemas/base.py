"""Shared enums, base types, and Provenance.

All cross-component Pydantic models import from here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Grade(StrEnum):
    WORST = "worst"
    BAD = "bad"
    NEUTRAL = "neutral"
    GOOD = "good"
    BEST = "best"

    @property
    def ordinal(self) -> int:
        return {"worst": 0, "bad": 1, "neutral": 2, "good": 3, "best": 4}[self.value]


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Difficulty(StrEnum):
    BASIC = "basic"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class AttackCategory(StrEnum):
    COGNITIVE = "cognitive"
    AUTHORITY = "authority"
    FRAMING = "framing"
    ENCODING = "encoding"
    MULTI_TURN = "multi_turn"
    REGULATORY = "regulatory"
    MORAL_RELIGIOUS = "moral_religious"
    FINANCIAL = "financial"


class ItemType(StrEnum):
    PROMPT = "prompt"
    RESPONSE = "response"
    CASE = "case"
    DOCUMENT = "document"
    LAW = "law"
    STATUTE = "statute"


class Provenance(BaseModel):
    """Tracks a record's full journey from source to final split.

    Every record in the pipeline carries one of these. The pipeline refuses
    to write a record without a populated Provenance.
    """

    source_id: str
    source_row_id: str
    ingested_at: datetime
    ingestion_script_version: str
    classifier_versions: dict[str, str] = Field(default_factory=dict)
    anonymizer_version: str | None = None
    anonymizer_actions: list[str] = Field(default_factory=list)
    split: str | None = None
    checksum: str
