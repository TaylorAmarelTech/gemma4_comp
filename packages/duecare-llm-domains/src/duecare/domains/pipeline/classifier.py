"""
Classify extracted facts by sector, corridor, exploitation type, and severity.

Operates on ``ExtractedFact`` instances produced by ``extractor.py`` but does
NOT import from it -- both modules communicate through Pydantic models only.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Sector(str, Enum):
    """Employment sector."""
    DOMESTIC_WORK = "domestic_work"
    CONSTRUCTION = "construction"
    FISHING = "fishing"
    AGRICULTURE = "agriculture"
    MANUFACTURING = "manufacturing"
    HOSPITALITY = "hospitality"
    ENTERTAINMENT = "entertainment"
    UNKNOWN = "unknown"


class ExploitationType(str, Enum):
    """Exploitation type aligned with ILO indicator categories."""
    DEBT_BONDAGE = "debt_bondage"
    PASSPORT_RETENTION = "passport_retention"
    WAGE_THEFT = "wage_theft"
    EXCESSIVE_FEES = "excessive_fees"
    FORCED_OVERTIME = "forced_overtime"
    RESTRICTION_OF_MOVEMENT = "restriction_of_movement"
    DECEPTION = "deception"
    THREATS_AND_VIOLENCE = "threats_and_violence"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Severity rating for a classified fact."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Classified fact model
# ---------------------------------------------------------------------------

class ClassifiedFact(BaseModel):
    """A fact annotated with sector, corridor, exploitation type, and severity."""
    fact_type: str
    value: str
    context: str = ""
    sector: Sector = Sector.UNKNOWN
    corridor: str = ""
    exploitation_type: ExploitationType = ExploitationType.UNKNOWN
    severity: Severity = Severity.MEDIUM
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Keyword lookup tables
# ---------------------------------------------------------------------------

_SECTOR_KEYWORDS: dict[Sector, list[str]] = {
    Sector.DOMESTIC_WORK: ["domestic worker", "maid", "household", "helper", "caregiver", "nanny"],
    Sector.CONSTRUCTION: ["construction", "building", "scaffolding", "laborer", "mason"],
    Sector.FISHING: ["fishing", "vessel", "trawler", "seafarer", "boat", "catch"],
    Sector.AGRICULTURE: ["farm", "plantation", "harvest", "crop", "agriculture", "picker"],
    Sector.MANUFACTURING: ["factory", "garment", "assembly", "manufacturing", "sweatshop"],
    Sector.HOSPITALITY: ["hotel", "restaurant", "resort", "hospitality", "kitchen"],
    Sector.ENTERTAINMENT: ["entertainment", "bar", "nightclub", "massage", "karaoke"],
}

_EXPLOITATION_KEYWORDS: dict[ExploitationType, list[str]] = {
    ExploitationType.DEBT_BONDAGE: ["debt", "owe", "loan", "bondage", "pay back", "interest", "training fee"],
    ExploitationType.PASSPORT_RETENTION: ["passport", "confiscate", "documents", "kept my papers", "surrender id"],
    ExploitationType.WAGE_THEFT: ["no salary", "didn't pay", "wage deduction", "withholding", "underpay"],
    ExploitationType.EXCESSIVE_FEES: ["placement fee", "recruitment fee", "processing fee", "agency fee", "service charge"],
    ExploitationType.FORCED_OVERTIME: ["no rest", "no day off", "16 hours", "excessive hours", "overtime"],
    ExploitationType.RESTRICTION_OF_MOVEMENT: ["locked", "couldn't leave", "confined", "not allowed to go"],
    ExploitationType.DECEPTION: ["lied", "promised", "different job", "fake", "not what they said"],
    ExploitationType.THREATS_AND_VIOLENCE: ["beat", "threaten", "punish", "violence", "hit", "scared"],
}

_HIGH_SEVERITY_TYPES: set[ExploitationType] = {
    ExploitationType.DEBT_BONDAGE,
    ExploitationType.PASSPORT_RETENTION,
    ExploitationType.THREATS_AND_VIOLENCE,
    ExploitationType.RESTRICTION_OF_MOVEMENT,
}

_CORRIDOR_PAIRS: dict[str, str] = {
    "philippines.*hong kong": "PH-HK",
    "philippines.*saudi": "PH-SA",
    "philippines.*singapore": "PH-SG",
    "philippines.*uae": "PH-AE",
    "indonesia.*malaysia": "ID-MY",
    "indonesia.*saudi": "ID-SA",
    "nepal.*qatar": "NP-QA",
    "nepal.*malaysia": "NP-MY",
    "bangladesh.*saudi": "BD-SA",
    "ethiopia.*saudi": "ET-SA",
    "myanmar.*thailand": "MM-TH",
    "cambodia.*thailand": "KH-TH",
    "vietnam.*taiwan": "VN-TW",
}


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def _detect_sector(text: str) -> Sector:
    text_lower = text.lower()
    for sector, keywords in _SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return sector
    return Sector.UNKNOWN


def _detect_exploitation(text: str) -> ExploitationType:
    text_lower = text.lower()
    for etype, keywords in _EXPLOITATION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return etype
    return ExploitationType.UNKNOWN


def _detect_corridor(text: str) -> str:
    text_lower = text.lower()
    for pattern, code in _CORRIDOR_PAIRS.items():
        if re.search(pattern, text_lower):
            return code
    return ""


def _assess_severity(exploitation_type: ExploitationType, context: str) -> Severity:
    if exploitation_type in _HIGH_SEVERITY_TYPES:
        return Severity.HIGH
    text_lower = context.lower()
    critical_signals = ["death", "suicide", "murder", "killed", "died"]
    if any(s in text_lower for s in critical_signals):
        return Severity.CRITICAL
    if exploitation_type == ExploitationType.UNKNOWN:
        return Severity.LOW
    return Severity.MEDIUM


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_fact(
    *,
    fact_type: str,
    value: str,
    context: str = "",
    confidence: float = 0.8,
) -> ClassifiedFact:
    """
    Classify an extracted fact by sector, corridor, exploitation type, and severity.

    Args:
        fact_type: The original fact type string (e.g. ``"ilo_indicator"``).
        value: The extracted value.
        context: Surrounding text for richer classification.
        confidence: Upstream extraction confidence.

    Returns:
        A ``ClassifiedFact`` with all classification fields populated.
    """
    combined = f"{value} {context}"
    sector = _detect_sector(combined)
    exploitation_type = _detect_exploitation(combined)
    corridor = _detect_corridor(combined)
    severity = _assess_severity(exploitation_type, combined)

    return ClassifiedFact(
        fact_type=fact_type,
        value=value,
        context=context,
        sector=sector,
        corridor=corridor,
        exploitation_type=exploitation_type,
        severity=severity,
        confidence=confidence * 0.9,  # slight discount for classification step
    )
