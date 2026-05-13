"""PII regex patterns used by the anonymization harness."""
from __future__ import annotations

import re

PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"\+?\d[\d\-\s]{7,}\d")),
    ("AMOUNT", re.compile(
        r"\b(?:PHP|HKD|USD|SGD|AED|SAR)\s*[\d,]+(?:\.\d+)?\b",
        re.IGNORECASE,
    )),
    ("ID", re.compile(r"\b[A-Z]{1,3}-?\d{6,}\b")),
    ("PERSON", re.compile(
        r"\b(?:Ms\.|Mr\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
    )),
]
