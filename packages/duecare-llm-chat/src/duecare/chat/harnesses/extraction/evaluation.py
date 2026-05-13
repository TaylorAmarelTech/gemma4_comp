"""Per-harness grading rubric + golden examples for extraction.

A bench-and-tune kernel picks ``rubric`` and ``examples`` from this
module to run targeted evaluations on this harness's safety task.
Rubric dimensions sum to weight 1.0; ``pass_criteria`` is the spec for
each dim's binary or graded score.
"""
from __future__ import annotations


rubric: list[dict] = [{'name': 'json_validity', 'weight': 0.25, 'description': 'Output envelope is valid KnowledgeObject JSON', 'pass_criteria': 'passes _ko_validate(): schema_version + ko_type + content dict + kebab-case id'}, {'name': 'schema_match', 'weight': 0.2, 'description': "Content field matches the target_type's expected shape", 'pass_criteria': 'for grep_rule: has pattern + category + severity; for fact_template: has fact + source'}, {'name': 'pii_safety', 'weight': 0.2, 'description': 'Anonymized when anonymize=True; original sha256 captured in provenance', 'pass_criteria': 'no email/phone/passport patterns survive in content; source_sha256 present'}, {'name': 'dedup_signal', 'weight': 0.15, 'description': 'applied_layers trace surfaces existing rule_ids when GREP fires on input', 'pass_criteria': 'extensions.applied_layers.grep.n_hits > 0 when raw_text matches existing rule'}, {'name': 'citation_grounding', 'weight': 0.2, 'description': 'When the input contains a statute/citation, the envelope tags it', 'pass_criteria': 'tags array includes a branch:grounding_knowledge entry when citation present'}]

examples: list[dict] = [{'input': {'raw_text': 'Recruiters charging more than 30000 PHP for HK domestic work', 'target_type': 'grep_rule'}, 'expected_layers_fired': ['grep'], 'notes': 'Should emit grep_rule with pattern + fee_bondage category.'}, {'input': {'raw_text': 'ILO C181 Art.7 prohibits agencies from charging worker fees', 'target_type': 'fact_template'}, 'expected_layers_fired': ['rag'], 'notes': 'Should emit fact_template citing the convention.'}, {'input': {'raw_text': 'jane.doe@example.com complained about employer', 'target_type': 'grep_rule', 'anonymize': True}, 'expected_layers_fired': ['grep'], 'notes': 'Email must be redacted to <EMAIL> before reaching Gemma + envelope.'}]


def summary() -> dict:
    return {
        "harness": "extraction",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
        "weight_total": sum(d.get("weight", 0) for d in rubric),
    }
