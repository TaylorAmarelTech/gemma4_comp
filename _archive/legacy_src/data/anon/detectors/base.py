"""PII detector protocol.

See docs/architecture.md section 7.3.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PIISpan(BaseModel):
    """A single detected PII span inside a text."""

    start: int
    end: int
    category: str  # "phone", "passport", "given_name", "address", ...
    text: str
    confidence: float


@runtime_checkable
class Detector(Protocol):
    """Detects PII in text and returns a list of spans.

    Detectors are composable: multiple detectors run over the same text
    and their spans are merged + deduped by the anonymization pipeline.
    """

    name: str
    version: str

    def detect(self, text: str) -> list[PIISpan]:
        ...
