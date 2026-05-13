"""Knowledge-pack manifest for the extraction harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the 21-leaf taxonomy in
docs/knowledge_module_schema.md. Validated by tests/test_harness_imports.py.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = (
    "grep_rule",         # drafts new regex patterns
    "fact_template",     # drafts factual entry templates
    "context_snippet",   # drafts glossary-style definitions
    "rubric_dimension",  # drafts ILO indicator scoring dims
    "citation_edge",     # drafts statute cross-references
    "envelope_schema",   # the typed envelope itself
)
CONSUMES: tuple[str, ...] = ("grep_rule", "rag_doc", "prompt_template", "fact_template")


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
