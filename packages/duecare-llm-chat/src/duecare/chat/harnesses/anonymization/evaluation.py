"""Per-harness grading rubric + golden examples for anonymization.

A bench-and-tune kernel picks ``rubric`` and ``examples`` from this
module to run targeted evaluations on this harness's safety task.
Rubric dimensions sum to weight 1.0; ``pass_criteria`` is the spec for
each dim's binary or graded score.
"""
from __future__ import annotations


rubric: list[dict] = [{'name': 'pii_recall', 'weight': 0.25, 'description': 'Catches PII present in the input', 'pass_criteria': 'all email / phone / amount / ID / person tokens in input are redacted'}, {'name': 'pii_precision', 'weight': 0.2, 'description': 'Does not over-redact non-PII text', 'pass_criteria': 'country names / statute citations / non-PII numerics survive'}, {'name': 'placeholder_stability', 'weight': 0.2, 'description': 'Same raw token redacts to the same placeholder within a salt scope', 'pass_criteria': "two occurrences of 'Ms. Jane Doe' produce identical <PERSON_xxxxxxxx>"}, {'name': 'audit_trail_completeness', 'weight': 0.2, 'description': 'Every redaction is captured in diffs[] with raw_sha256 + placeholder + range', 'pass_criteria': 'diffs[i].n_redactions == count of placeholders in redacted[i]'}, {'name': 'submission_envelope', 'weight': 0.15, 'description': 'Submit endpoint writes audit log AND records remote status', 'pass_criteria': 'audit JSONL row has transmitted + remote_status fields populated'}]

examples: list[dict] = [{'input': {'texts': ['Ms. Jane Doe at jane@example.com about PHP 30,000']}, 'expected_layers_fired': [], 'notes': 'PERSON + EMAIL + AMOUNT all caught; AMOUNT placeholder per salt; country PHP preserved.'}, {'input': {'texts': ['A1234567 passport stolen by Mr. John recruiter']}, 'expected_layers_fired': [], 'notes': "Passport ID + PERSON; should NOT over-redact 'recruiter'."}, {'input': {'texts': ['Working in Saudi Arabia under ILO C189']}, 'expected_layers_fired': [], 'notes': 'Negative example -- no PII; n_redactions == 0.'}]


def summary() -> dict:
    return {
        "harness": "anonymization",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
        "weight_total": sum(d.get("weight", 0) for d in rubric),
    }
