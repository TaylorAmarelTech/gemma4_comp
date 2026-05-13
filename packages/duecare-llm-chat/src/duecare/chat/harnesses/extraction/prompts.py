"""Extraction prompts."""
from __future__ import annotations

EXTRACTION_SYSTEM_PROMPT = (
    "You are DueCare's KnowledgeObject drafter. Given a raw fact, return "
    "JSON ONLY for the `content` field of a `{target_type}` KnowledgeObject. "
    "Anonymize any PII (names, emails, phones, IDs) with placeholders like "
    "<PERSON_a1b2c3d4>. Do not include any prose outside the JSON object."
)


def build_system_prompt(target_type: str) -> str:
    return EXTRACTION_SYSTEM_PROMPT.format(target_type=target_type)
