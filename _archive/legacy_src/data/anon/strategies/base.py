"""Anonymization strategy protocol.

See docs/architecture.md section 7.4.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.data.anon.detectors.base import PIISpan


@runtime_checkable
class AnonymizationStrategy(Protocol):
    """Applies an anonymization transform to a text, guided by detected spans.

    Strategies are composable: a pipeline may apply the Redactor to phone
    numbers, the Tokenizer to names, and the Generalizer to locations, all
    in one pass.
    """

    name: str
    version: str

    def apply(self, text: str, spans: list[PIISpan]) -> str:
        ...
