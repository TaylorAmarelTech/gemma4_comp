"""
Fact extraction from raw document text.

Uses regex and keyword matching to extract structured facts:
legal citations, monetary amounts, country names, organisation names,
ILO indicators, and dates.

No LLM calls -- this is a fast, deterministic local extraction pass
designed to run before any optional LLM-enhanced step.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FactType(str, Enum):
    """Types of facts the extractor can identify."""
    LEGAL_CITATION = "legal_citation"
    MONETARY_AMOUNT = "monetary_amount"
    COUNTRY = "country"
    ORGANISATION = "organisation"
    ILO_INDICATOR = "ilo_indicator"
    DATE = "date"


class ExtractedFact(BaseModel):
    """A single fact extracted from a document."""
    fact_type: FactType
    value: str
    context: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    offset: Optional[int] = None


# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

_LEGAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bR\.?A\.?\s*(?:No\.?\s*)?(\d+)", re.I), "RA {0}"),
    (re.compile(r"\b(?:ILO\s+)?Convention\s+(?:No\.?\s*)?C?(\d+)", re.I), "ILO C{0}"),
    (re.compile(r"\bCap\.?\s*(\d+[A-Z]?)", re.I), "Cap. {0}"),
    (re.compile(r"\bProtocol\s+(?:of\s+)?(?:No\.?\s*)?P?(\d+)", re.I), "ILO P{0}"),
    (re.compile(r"\b(Palermo\s+Protocol)\b", re.I), "{0}"),
    (re.compile(r"\bG\.?R\.?\s*No\.?\s*(\d+[-\u2013]\d+)", re.I), "G.R. No. {0}"),
]

_MONEY_PATTERN = re.compile(
    r"(?:USD|PHP|HKD|SGD|MYR|SAR|AED|EUR|GBP|\$|P)\s?[\d,]+(?:\.\d{1,2})?"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\s*(?:pesos?|dollars?|USD|PHP|HKD)",
    re.I,
)

_DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.I,
)

_COUNTRIES: set[str] = {
    "Philippines", "Hong Kong", "Singapore", "Taiwan", "Malaysia",
    "Saudi Arabia", "United Arab Emirates", "UAE", "Qatar", "Kuwait",
    "Bahrain", "Oman", "Indonesia", "Thailand", "Vietnam", "Cambodia",
    "Myanmar", "Nepal", "Bangladesh", "Sri Lanka", "India", "Pakistan",
    "Ethiopia", "Kenya", "Nigeria", "Japan", "South Korea",
}

_COUNTRY_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in sorted(_COUNTRIES, key=len, reverse=True)) + r")\b",
    re.I,
)

_ORG_PATTERN = re.compile(
    r"\b(POEA|DOLE|OWWA|ILO|IOM|UNODC|IJM|ECPAT|BP2MI|Polaris\s+Project"
    r"|UN\s+Women|UNICEF|HRD\s+Nepal|La\s+Strada|Anti-Slavery\s+International"
    r"|Migrant\s+Forum\s+in\s+Asia|MFA)\b",
    re.I,
)

_ILO_INDICATORS: dict[str, list[str]] = {
    "abuse_of_vulnerability": ["didn't know", "no choice", "no papers", "undocumented", "afraid"],
    "deception": ["lied", "promised", "different job", "not what they said", "fake contract"],
    "restriction_of_movement": ["couldn't leave", "locked in", "not allowed to go", "confined"],
    "isolation": ["no contact", "took phone", "couldn't call", "no friends"],
    "retention_of_documents": ["took passport", "hold passport", "confiscate documents", "kept my papers"],
    "withholding_wages": ["no salary", "didn't pay", "wage deduction", "held back pay"],
    "debt_bondage": ["debt", "owe money", "pay back", "training fee", "interest on loan"],
    "excessive_overtime": ["no rest day", "work all day", "16 hours", "never stop", "no day off"],
    "threats_and_violence": ["beat", "threatened", "punish", "hit me", "scared"],
}


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def _ctx(text: str, start: int, *, window: int = 80) -> str:
    """Return a context snippet around *start*."""
    lo = max(0, start - window)
    hi = min(len(text), start + window)
    return text[lo:hi].replace("\n", " ").strip()


def extract_facts(text: str) -> list[ExtractedFact]:
    """
    Extract structured facts from *text*.

    Returns a list of ``ExtractedFact`` instances covering legal citations,
    monetary amounts, country names, organisations, ILO forced-labour
    indicators, and dates.

    Args:
        text: The raw document text to analyse.

    Returns:
        A list of extracted facts, sorted by offset.
    """
    facts: list[ExtractedFact] = []
    if not text:
        return facts

    # --- Legal citations ---
    for pattern, template in _LEGAL_PATTERNS:
        for m in pattern.finditer(text):
            value = template.format(m.group(1)) if "{0}" in template else m.group(0)
            facts.append(ExtractedFact(
                fact_type=FactType.LEGAL_CITATION,
                value=value,
                context=_ctx(text, m.start()),
                offset=m.start(),
            ))

    # --- Monetary amounts ---
    for m in _MONEY_PATTERN.finditer(text):
        facts.append(ExtractedFact(
            fact_type=FactType.MONETARY_AMOUNT,
            value=m.group(0).strip(),
            context=_ctx(text, m.start()),
            offset=m.start(),
        ))

    # --- Countries ---
    seen_countries: set[str] = set()
    for m in _COUNTRY_PATTERN.finditer(text):
        name = m.group(1)
        if name.lower() not in seen_countries:
            seen_countries.add(name.lower())
            facts.append(ExtractedFact(
                fact_type=FactType.COUNTRY,
                value=name,
                context=_ctx(text, m.start()),
                offset=m.start(),
            ))

    # --- Organisations ---
    seen_orgs: set[str] = set()
    for m in _ORG_PATTERN.finditer(text):
        name = m.group(1)
        if name.upper() not in seen_orgs:
            seen_orgs.add(name.upper())
            facts.append(ExtractedFact(
                fact_type=FactType.ORGANISATION,
                value=name,
                context=_ctx(text, m.start()),
                offset=m.start(),
            ))

    # --- ILO forced-labour indicators ---
    text_lower = text.lower()
    for indicator, keywords in _ILO_INDICATORS.items():
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                facts.append(ExtractedFact(
                    fact_type=FactType.ILO_INDICATOR,
                    value=indicator,
                    context=_ctx(text, idx),
                    confidence=0.7,
                    offset=idx,
                ))
                break  # one match per indicator type

    # --- Dates ---
    for m in _DATE_PATTERN.finditer(text):
        facts.append(ExtractedFact(
            fact_type=FactType.DATE,
            value=m.group(0).strip(),
            context=_ctx(text, m.start()),
            offset=m.start(),
        ))

    facts.sort(key=lambda f: f.offset or 0)
    return facts
