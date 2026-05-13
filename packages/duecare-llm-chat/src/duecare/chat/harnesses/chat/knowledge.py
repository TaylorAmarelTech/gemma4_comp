"""Knowledge-pack manifest for the chat harness.

Lists the KnowledgeObject types this harness emits and/or consumes,
so a knowledge-builder kernel can target this harness specifically
when generating training data or evaluation rubrics.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ()    # KO types this harness produces
CONSUMES: tuple[str, ...] = ()  # KO types this harness reads


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
