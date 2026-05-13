"""Function-calling tools contributed by the extraction harness.

Empty by design: Gemma IS the tool here (it generates the envelope).
Kept for contract uniformity across harnesses.
"""
from __future__ import annotations


TOOLS: list[dict] = []


def list_tools() -> list[dict]:
    return list(TOOLS)
