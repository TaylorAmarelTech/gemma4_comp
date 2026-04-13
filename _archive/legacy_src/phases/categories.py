"""The four capability test categories shared by every phase.

See docs/project_phases.md section "The four test categories".
"""

from __future__ import annotations

from enum import StrEnum


class CapabilityTest(StrEnum):
    """The four tests we run in every phase."""

    GUARDRAILS = "response_policy_guardrails"
    ANONYMIZATION = "anonymization"
    CLASSIFICATION = "document_classification"
    FACT_EXTRACTION = "key_fact_extraction"


# Metric definitions per capability test. The phase runners populate these
# after running their configured model(s) over the test data.
CAPABILITY_METRICS: dict[CapabilityTest, list[str]] = {
    CapabilityTest.GUARDRAILS: [
        "grade_exact_match",
        "grade_within_1",
        "ordinal_mae",
        "ilo_indicator_recall",
        "ilo_indicator_precision",
        "documentation_ref_precision",
        "refusal_rate",
        "harmful_phrase_rate",
    ],
    CapabilityTest.ANONYMIZATION: [
        "pii_span_recall",
        "pii_span_precision",
        "false_positive_rate",
        "non_latin_script_recall",
        "foreign_name_recall",
    ],
    CapabilityTest.CLASSIFICATION: [
        "sector_accuracy",
        "corridor_accuracy",
        "ilo_indicator_f1_multilabel",
        "attack_category_f1",
        "difficulty_agreement",
    ],
    CapabilityTest.FACT_EXTRACTION: [
        "entity_f1_person",
        "entity_f1_organization",
        "entity_f1_location",
        "entity_f1_currency",
        "date_accuracy",
        "citation_accuracy",
    ],
}


# Which components each capability test exercises. Used by phase runners
# to pick the right model calls and scorers.
COMPONENTS_PER_TEST: dict[CapabilityTest, list[str]] = {
    CapabilityTest.GUARDRAILS: [
        "src.inference",      # run the model
        "src.grading",        # score against graded examples
    ],
    CapabilityTest.ANONYMIZATION: [
        "src.inference",
        "src.data.anon",      # ground truth + verifier
    ],
    CapabilityTest.CLASSIFICATION: [
        "src.inference",
        "src.data.classify",  # taxonomy + scoring
    ],
    CapabilityTest.FACT_EXTRACTION: [
        "src.inference",
        "src.grading",        # custom extractor scorer
    ],
}
