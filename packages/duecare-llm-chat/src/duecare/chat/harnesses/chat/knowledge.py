"""Knowledge-pack manifest for the chat harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the 21-leaf taxonomy in
docs/knowledge_module_schema.md. Validated by tests/test_harness_imports.py.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = ()
CONSUMES: tuple[str, ...] = ('grep_rule', 'glob_rule', 'classifier_rule', 'heuristic_rule', 'rag_doc', 'citation_edge', 'corridor_profile', 'ngo_directory', 'persona_block', 'context_snippet', 'reasoning_step', 'rubric_dimension', 'tool_definition', 'tool_example')


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
