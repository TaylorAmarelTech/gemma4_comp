"""Extraction prompts."""
from __future__ import annotations

_SCHEMAS = {
    "grep_rule": (
        "Return fields: category, severity, pattern, description, "
        "test_phrases, false_positive_notes."
    ),
    "rag_doc": (
        "Return fields: title, jurisdiction, source_url, text, citation_label, "
        "claim_type."
    ),
    "context_snippet": (
        "Return fields: applies_to_corridors, applies_to_indicators, text, "
        "response_guidance, citation_ids."
    ),
    "fact_template": (
        "Return fields: label, applies_to_indicators, fields, source_excerpt. "
        "This is a reusable schema for future facts, not a single fact record."
    ),
    "extracted_fact": (
        "Return fields: fact_type, corridor, amount, currency, entity_names, "
        "locations, indicators, journey_stage, evidence_quote, confidence_0_10, "
        "share_scope, aggregation_keys."
    ),
    "entity_signal": (
        "Return fields: entity_name, entity_type, corridor, signal_types, "
        "evidence_quote, source_context, confidence_0_10, pii_status, "
        "aggregation_keys."
    ),
    "modus_operandi": (
        "Return fields: pattern_name, short_description, stages, indicators, "
        "generalized_pattern, non_pii_example, applicable_corridors, "
        "chart_dimensions, related_fact_types."
    ),
    "ngo_directory": (
        "Return fields: name, jurisdiction, phone, email, url, "
        "verification_note. Do not claim contact details are current unless the "
        "source explicitly verifies currency."
    ),
    "rubric_dimension": (
        "Return fields: label, question, scale, weight, applicability_logic, "
        "pass_criteria, fail_criteria."
    ),
}

EXTRACTION_SYSTEM_PROMPT = (
    "You are DueCare's KnowledgeObject drafter. Given a raw fact, return "
    "JSON ONLY for the `content` field of a `{target_type}` KnowledgeObject. "
    "{schema_hint} "
    "Separate case-specific facts from reusable generalized patterns. "
    "For organizations, agencies, employers, recruiters, training centers, "
    "money lenders, and payment recipients, preserve non-PII entity names when "
    "they are useful for trend analysis. Anonymize personal PII (individual "
    "worker names, emails, phones, passport or national IDs) with placeholders "
    "like <PERSON_a1b2c3d4>. Include aggregation_keys when the object can feed "
    "charts, maps, entity graphs, corridor trends, or server-side vetting. "
    "Do not include any prose outside the JSON object."
)


def build_system_prompt(target_type: str) -> str:
    return EXTRACTION_SYSTEM_PROMPT.format(
        target_type=target_type,
        schema_hint=_SCHEMAS.get(target_type, "Return a structured JSON object."),
    )
