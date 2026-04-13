"""Quick Filter — Stage 1 triage for the enterprise waterfall.

Runs on every message/post/chat to decide whether to trigger
the full Gemma 4 DueCare analysis. Designed to be fast (< 1ms),
cheap (no model call), and high-recall (false positives are OK,
false negatives are not — better to over-flag than miss a trafficking
scenario).

Usage:
    from src.demo.quick_filter import QuickFilter

    qf = QuickFilter()
    result = qf.check("I need to pay $3000 to the agency before starting")
    if result.should_trigger:
        # Send to Gemma 4 for full analysis
        ...
"""

from __future__ import annotations

import re
from pydantic import BaseModel, Field
from typing import ClassVar



class FilterResult(BaseModel):
    """Result of the quick filter check."""

    should_trigger: bool
    score: float  # 0.0–1.0 confidence
    matched_keywords: list[str]
    matched_patterns: list[str]
    category_hints: list[str]  # which rubric categories likely apply


class QuickFilter:
    """Fast keyword + pattern-based pre-screener for exploitation indicators.

    Design goals:
    - HIGH RECALL: catch everything that might be exploitation
    - Acceptable false positive rate: ~20-30% is fine (Gemma handles the rest)
    - FAST: pure regex, no model calls, < 1ms per check
    - MULTILINGUAL: core patterns in English + Tagalog (Philippines corridor)
    """

    # ── Keyword categories ──

    RECRUITMENT_FEE_KEYWORDS: ClassVar[list[str]] = [
        "recruitment fee", "placement fee", "agency fee",
        "processing fee", "training fee", "advance payment",
        "salary deduction", "monthly deduction", "payroll deduction",
        "bayad muna",  # Tagalog: "pay first"
        "placement cost", "deposit required",
        "placement charge", "service charge",
        "pre-departure fee", "documentation fee",
    ]

    DOCUMENT_CONTROL_KEYWORDS: ClassVar[list[str]] = [
        "passport held", "hold passport", "keep passport",
        "confiscate passport", "surrender passport",
        "give me your passport", "passport retention",
        "visa control", "work permit held",
        "ibibigay mo ang passport",  # Tagalog
    ]

    COERCION_KEYWORDS: ClassVar[list[str]] = [
        "cannot leave", "cannot change jobs", "cannot transfer",
        "sponsor approval", "kafala", "sponsorship transfer",
        "exit permit", "no objection certificate",
        "runaway", "absconding",
        "contract substitution", "different contract",
        "bawal umalis",  # Tagalog: "cannot leave"
    ]

    DEBT_BONDAGE_KEYWORDS: ClassVar[list[str]] = [
        "debt bondage", "bonded labor", "bonded labour",
        "work off the debt", "pay off the loan",
        "salary advance", "loan deduction",
        "excessive fees", "illegal fees",
        "utang na loob",  # Tagalog: "debt of gratitude"
    ]

    WAGE_THEFT_KEYWORDS: ClassVar[list[str]] = [
        "unpaid wages", "withheld salary", "salary withheld",
        "no pay", "delayed payment", "wage theft",
        "garnished wages", "wage garnishment",
        "hindi binayaran",  # Tagalog: "not paid"
    ]

    FINANCIAL_CRIME_KEYWORDS: ClassVar[list[str]] = [
        "money laundering", "structuring", "smurfing",
        "shell company", "offshore account",
        "cryptocurrency mixer", "tornado cash",
        "proceeds of crime", "suspicious transaction",
    ]

    # ── Pattern-based detection ──

    FEE_AMOUNT_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"(?:fee|charge|cost|payment|deduction).*?"
        r"(?:PHP|USD|\$|₱)\s*[\d,]+|"
        r"[\d,]+\s*(?:PHP|pesos|dollars)",
        re.IGNORECASE,
    )

    PERCENTAGE_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"\d+%\s*(?:of\s+(?:salary|wage|pay|income))",
        re.IGNORECASE,
    )

    LEGAL_REFERENCE_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"(?:RA\s*(?:8042|10022)|ILO\s*C\d+|POEA|Employment\s+Ordinance|"
        r"Palermo\s+Protocol|kafala\s+(?:system|reform))",
        re.IGNORECASE,
    )

    # ── Category mapping ──

    KEYWORD_TO_CATEGORY: ClassVar[dict[str, str]] = {}

    def __init__(self) -> None:
        # Build reverse lookup
        for kw in self.RECRUITMENT_FEE_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "business_framed_exploitation"
        for kw in self.DOCUMENT_CONTROL_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "victim_revictimization"
        for kw in self.COERCION_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "victim_revictimization"
        for kw in self.DEBT_BONDAGE_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "financial_crime_blindness"
        for kw in self.WAGE_THEFT_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "financial_crime_blindness"
        for kw in self.FINANCIAL_CRIME_KEYWORDS:
            self.KEYWORD_TO_CATEGORY[kw] = "financial_crime_blindness"

        self._all_keywords = list(self.KEYWORD_TO_CATEGORY.keys())

    def check(self, text: str) -> FilterResult:
        """Check text for exploitation indicators. < 1ms."""
        text_lower = text.lower()

        # Keyword matching
        matched_kw = [kw for kw in self._all_keywords if kw in text_lower]

        # Pattern matching
        matched_patterns = []
        if self.FEE_AMOUNT_PATTERN.search(text):
            matched_patterns.append("fee_amount")
        if self.PERCENTAGE_PATTERN.search(text):
            matched_patterns.append("salary_percentage")
        if self.LEGAL_REFERENCE_PATTERN.search(text):
            matched_patterns.append("legal_reference")

        # Category hints
        categories = list({self.KEYWORD_TO_CATEGORY[kw] for kw in matched_kw})

        # Score: 0.0 (no match) to 1.0 (strong match)
        kw_score = min(len(matched_kw) / 3.0, 1.0)
        pattern_score = min(len(matched_patterns) / 2.0, 1.0)
        score = max(kw_score, pattern_score)

        # Trigger threshold: any keyword or pattern match
        should_trigger = len(matched_kw) > 0 or len(matched_patterns) > 0

        return FilterResult(
            should_trigger=should_trigger,
            score=round(score, 3),
            matched_keywords=matched_kw,
            matched_patterns=matched_patterns,
            category_hints=categories,
        )
