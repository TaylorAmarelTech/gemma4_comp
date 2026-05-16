"""Knowledge-pack manifest for the import_corpus harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the canonical taxonomy in
docs/knowledge_module_schema.md. Validated by workbench inventory tests.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ('context_snippet',)
CONSUMES: tuple[str, ...] = ('upload_schema',)


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
