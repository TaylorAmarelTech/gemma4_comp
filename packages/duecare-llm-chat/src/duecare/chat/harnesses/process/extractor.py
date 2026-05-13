"""Entity regex patterns for the process harness."""
from __future__ import annotations

import re

ENTITY_PATTERNS: dict[str, re.Pattern] = {
    "AMOUNT": re.compile(
        r"\b(?:PHP|HKD|USD|SGD|AED|SAR)\s*[\d,]+(?:\.\d+)?\b",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(r"\+?\d[\d\-\s]{7,}\d"),
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "STATUTE": re.compile(
        r"\b(?:POEA\s+MC\s+\d{1,3}-\d{4}|"
        r"ILO\s+C\d{2,3}|"
        r"RA\s+\d{4,5}|"
        r"BP2MI\s+Reg\s+\d+-\d{4})\b",
        re.IGNORECASE,
    ),
    "CORRIDOR": re.compile(
        r"\b(PH|ID|NP|BD|VN|MM)[-\s]?"
        r"(?:HK|SG|MY|UAE|SA|KSA|KW|LB|JO)\b",
        re.IGNORECASE,
    ),
}
