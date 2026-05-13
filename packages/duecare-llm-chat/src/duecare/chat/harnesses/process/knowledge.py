"""Knowledge-pack manifest for the process harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the 21-leaf taxonomy in
docs/knowledge_module_schema.md. Validated by tests/test_harness_imports.py.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ('audit_template',)
CONSUMES: tuple[str, ...] = ('grep_rule', 'glob_rule', 'rag_doc', 'corridor_profile', 'ngo_directory', 'tool_definition', 'context_snippet')


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
