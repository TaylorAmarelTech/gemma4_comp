"""Knowledge-pack manifest for the extraction harness.

Declares the KnowledgeObject types this harness reads (CONSUMES) and
produces (EMITS). Drawn from the canonical taxonomy in
docs/knowledge_module_schema.md. Validated by workbench inventory tests.
"""
from __future__ import annotations


EMITS: tuple[str, ...] = (
    "grep_rule",         # drafts new regex patterns
    "rag_doc",           # drafts source-backed retrieval docs
    "ngo_directory",     # drafts verified-contact placeholders
    "fact_template",     # drafts factual entry templates
    "extracted_fact",    # drafts non-PII trend facts from reviewed sources
    "entity_signal",     # drafts non-PII organization / actor signals
    "context_snippet",   # drafts glossary-style definitions
    "modus_operandi",    # drafts generalized abuse-pattern knowledge
    "rubric_dimension",  # drafts ILO indicator scoring dims
    "citation_edge",     # drafts statute cross-references
    "envelope_schema",   # the typed envelope itself
)
CONSUMES: tuple[str, ...] = ("grep_rule", "rag_doc", "prompt_template", "fact_template")


def manifest() -> dict:
    return {"emits": list(EMITS), "consumes": list(CONSUMES)}
