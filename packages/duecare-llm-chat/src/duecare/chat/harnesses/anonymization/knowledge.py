"""Knowledge-pack manifest for the anonymization harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the canonical taxonomy in
docs/knowledge_module_schema.md. Validated by workbench inventory tests.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ('audit_template', 'submission_schema')
CONSUMES: tuple[str, ...] = ('prompt_template',)


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
