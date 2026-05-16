"""Knowledge-pack manifest for the process harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the canonical taxonomy in
docs/knowledge_module_schema.md. Validated by workbench inventory tests.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = (
    "audit_template",
    "extracted_fact",
    "entity_signal",
    "modus_operandi",
    "fact_template",
    "context_snippet",
)
CONSUMES: tuple[str, ...] = ('grep_rule', 'glob_rule', 'rag_doc', 'corridor_profile', 'ngo_directory', 'tool_definition', 'context_snippet')


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
