"""Edge-filter PII detector shared by ``main`` and ``openclaw``.

Lives in its own module so the LLM evaluator (``openclaw.py``) can reuse the
regex without forcing a circular import on the FastAPI app.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_PASSPORT_RE = re.compile(
    r"\b(?:passport|visa|national\s+id|id\s+number)[:#\s-]*[A-Z0-9-]{5,}\b",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'-]+\s+"
    r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|drive|dr\.?)\b",
    re.IGNORECASE,
)


def detect_pii(text: str) -> set[str]:
    """Return PII detector labels found in ``text``."""
    findings: set[str] = set()
    if _EMAIL_RE.search(text):
        findings.add("email")
    if _PHONE_RE.search(text):
        findings.add("phone")
    if _PASSPORT_RE.search(text):
        findings.add("identity_document")
    if _ADDRESS_RE.search(text):
        findings.add("street_address")
    return findings


__all__ = ["detect_pii"]
