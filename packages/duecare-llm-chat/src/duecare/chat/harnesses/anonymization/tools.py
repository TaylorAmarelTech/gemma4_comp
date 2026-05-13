"""Function-calling tools contributed by the anonymization harness.

Empty BY DESIGN: this harness is the PII safety gate; it must NOT
expose tools to Gemma (raw PII must not reach a language model from
this harness). Kept for contract uniformity. Do NOT add tools here
without revisiting the trust boundary in README.md.
"""
from __future__ import annotations


TOOLS: list[dict] = []


def list_tools() -> list[dict]:
    return list(TOOLS)
