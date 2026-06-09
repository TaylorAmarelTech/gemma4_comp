"""PII regex patterns used by the anonymization harness.

Corridor-aware: the phone/ID shapes below cover the formats that actually
appear in the corridors the corpus models (PH, ID, NP, BD, Gulf states),
not just Anglo formats. The Gemma residual-PII review pass remains the
backstop for shapes regex cannot catch (non-Latin names, free-text
addresses).
"""
from __future__ import annotations

import re

PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # Optional parenthesized country code first -- "(+63) 917-555-0144" --
    # then the generic international/local digit run that already covered
    # "+852 5123 4567" and "0917-555-0144" shapes.
    ("PHONE", re.compile(r"(?:\(\+?\d{1,3}\)[\s\-]?)?\+?\d[\d\-\s]{7,}\d")),
    ("AMOUNT", re.compile(
        r"\b(?:PHP|HKD|USD|SGD|AED|SAR)\s*[\d,]+(?:\.\d+)?\b",
        re.IGNORECASE,
    )),
    # Contextual date of birth (10_safety_gate: DOB is critical PII;
    # generalize to year). Keyed on birth context so case/filing dates in
    # narratives are not over-redacted.
    ("DOB", re.compile(
        r"\b(?:born(?:\s+on)?|birth\s*date|date\s+of\s+birth|d\.?o\.?b\.?)\s*[:\-]?\s*"
        r"\d{1,4}[\-/\. ]\d{1,2}[\-/\. ]\d{1,4}\b",
        re.IGNORECASE,
    )),
    # Government / travel document numbers: generic prefixed IDs, PH
    # passport (P1234567A), OFW e-card (E-1234567-8), Indonesian
    # 16-digit KTP.
    ("ID", re.compile(
        r"\b(?:[A-Z]{1,3}-?\d{6,}|[A-Z]\d{7,8}[A-Z]|[A-Z]-\d{6,8}-\d|\d{16})\b"
    )),
    ("PERSON", re.compile(
        r"\b(?:Ms\.|Mr\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    )),
]
