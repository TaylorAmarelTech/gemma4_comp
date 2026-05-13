"""Knowledge-pack manifest for the import_corpus harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the 21-leaf taxonomy in
docs/knowledge_module_schema.md. Validated by tests/test_harness_imports.py.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ('context_snippet',)
CONSUMES: tuple[str, ...] = ('upload_schema',)


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
