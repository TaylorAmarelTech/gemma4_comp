"""Tests for the global protections curation-bundle validator."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


builder = _load(
    "build_global_protections_curation_bundle",
    _ROOT / "scripts" / "build_global_protections_curation_bundle.py",
)
validator = _load(
    "validate_global_protections_curation_bundle",
    _ROOT / "scripts" / "validate_global_protections_curation_bundle.py",
)


def _bundle_doc():
    return builder.build_curation_bundle()


def test_validator_accepts_current_curation_bundle():
    report = validator.validate_curation_bundle(_bundle_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["next_execution_phase_count"] == 5
    assert report["summary"]["jurisdiction_pack_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert report["summary"]["jurisdiction_pack_domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert report["summary"]["next_execution_phase_covered_actions"] == 34
    assert report["summary"]["next_actions_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["next_actions_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["next_actions_preserving_legal_anchor_source_channels"] == 34
    assert (
        report["summary"]["next_execution_phases_preserving_legal_anchor_source_channels"]
        == 5
    )
    assert report["summary"]["curator_execution_phase_count"] == 5
    assert report["summary"]["curator_execution_phase_covered_actions"] == 34
    assert report["summary"]["readiness_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["readiness_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["worker_verified_local_law_rows"] == 0
    assert report["summary"]["worker_source_object_tasks"] == 15
    assert report["summary"]["worker_scope_refinement_tasks"] == 8
    assert report["summary"]["regulatory_pattern_count"] == 11
    assert report["summary"]["regulatory_candidate_count"] == 10
    assert report["summary"]["regulatory_seed_scaffold_operations"] == 0
    assert report["summary"]["source_channel_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["source_channel_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["source_channel_review_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["source_channel_review_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curator_sprint_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["curator_sprint_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curator_sprint_items_preserving_legal_anchor_source_channels"] == 24
    assert (
        report["summary"][
            "curator_blocked_later_items_preserving_legal_anchor_source_channels"
        ]
        == 10
    )
    assert report["summary"]["curator_execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_scoring_flag_drift():
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_curation_bundle(doc)

    assert report["summary"]["valid"] is False
    assert "all_public_and_scoring_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_payload_or_url_dump():
    doc = _bundle_doc()
    doc["actions"] = [{"source_url": "https://example.invalid/private-case"}]

    report = validator.validate_curation_bundle(doc)

    assert report["summary"]["valid"] is False
    assert "raw_payload_sections_absent" in report["summary"]["failed_check_ids"]
    assert "bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_count_mismatch():
    doc = _bundle_doc()
    doc["summary"]["next_action_count"] = 999

    report = validator.validate_curation_bundle(doc)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" in report["summary"]["failed_check_ids"]


def test_validator_rejects_readiness_blocker_summary_mismatch():
    doc = _bundle_doc()
    doc["summary"]["worker_source_object_tasks"] = 14

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_readiness_regulatory_candidate_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["regulatory_candidate_count"] = 7
    doc["component_summaries"]["readiness_bundle"]["regulatory_candidate_count"] = 7

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]


def test_validator_rejects_readiness_seed_scaffold_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["regulatory_seed_scaffold_operations"] = 1
    doc["component_summaries"]["readiness_bundle"]["regulatory_seed_scaffold_operations"] = 1

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_blocking_counts_match" in report["summary"]["failed_check_ids"]
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_jurisdiction_pack_id_summary_mismatch():
    doc = _bundle_doc()
    doc["summary"]["jurisdiction_pack_scope_ids"] = ["stale_scope"]
    doc["summary"]["jurisdiction_pack_domain_lens_ids"] = ["stale_lens"]

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_regulatory_priority_queue_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["next_regulatory_priority_queue_items"] = 0
    doc["component_summaries"]["next_actions"]["regulatory_priority_queue_items"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]


def test_validator_rejects_component_readiness_flag_drift_without_current_chain():
    doc = _bundle_doc()
    doc["component_summaries"]["transition_gate"]["ready_for_model_response_capture"] = True

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_component_consistency_drift_without_current_chain():
    doc = _bundle_doc()
    doc["component_summaries"]["diagnostic_run_plan"]["consistency_ok"] = False

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_consistency_flags_ok" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_component_blocking_drift_without_current_chain():
    doc = _bundle_doc()
    doc["component_summaries"]["source_channel_review_packet"]["rows_ready_for_manifest_promotion"] = 1

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_blocking_counts_match" in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_jurisdiction_pack_slot_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["jurisdiction_pack_not_started_source_object_slots"] = 119
    doc["component_summaries"]["jurisdiction_pack_matrix"][
        "not_started_source_object_slots"
    ] = 119

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_blocking_counts_match" in report["summary"]["failed_check_ids"]
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_claim_anchor_count_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["source_channel_legal_claim_anchor_rows"] = 999
    doc["component_summaries"]["source_channel_matrix"]["legal_claim_anchor_rows"] = 999

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_lead_only_claim_count_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["source_channel_review_lead_only_claim_rows"] = 0
    doc["component_summaries"]["source_channel_review_packet"]["lead_only_claim_rows"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_channel_authenticity_control_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["source_channel_authenticity_volatility_control_rows"] = 59
    doc["component_summaries"]["source_channel_matrix"][
        "authenticity_volatility_control_rows"
    ] = 59

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_review_authenticity_control_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["source_channel_review_informal_authenticity_volatility_rows"] = 5
    doc["component_summaries"]["source_channel_review_packet"][
        "informal_authenticity_volatility_review_rows"
    ] = 5

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_grounding_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_task_source_grounding_contracts"] = 0
    doc["component_summaries"]["benchmark_blueprint"]["task_source_grounding_contract_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_grounding_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 11
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 11

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["eval_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["eval_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["eval_contract"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["eval_contract"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_matrix_legal_anchor_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["source_channel_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["source_channel_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["source_channel_matrix"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["source_channel_matrix"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_review_legal_anchor_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["source_channel_review_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["source_channel_review_legal_claim_anchor_source_channel_ids"] = list(
        broadened
    )
    doc["component_summaries"]["source_channel_review_packet"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["source_channel_review_packet"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_temporal_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 13
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 13
    doc["summary"]["eval_judge_output_fields"] = 13
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 13

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_language_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 15
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 15
    doc["summary"]["eval_judge_output_fields"] = 14
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 14

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_entity_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 17
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 17
    doc["summary"]["eval_judge_output_fields"] = 15
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 15

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_remedy_forum_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 19
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 19
    doc["summary"]["eval_judge_output_fields"] = 16
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 16

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_authority_hierarchy_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 21
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 21
    doc["summary"]["eval_judge_output_fields"] = 17
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 17

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_coverage_scope_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 23
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 23
    doc["summary"]["eval_judge_output_fields"] = 18
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 18

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_jurisdiction_chain_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 25
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 25
    doc["summary"]["eval_judge_output_fields"] = 19
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 19

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_implementation_access_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 27
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 27
    doc["summary"]["eval_judge_output_fields"] = 20
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 20

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_eval_procedural_burden_schema_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["eval_model_response_record_fields"] = 29
    doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] = 29
    doc["summary"]["eval_judge_output_fields"] = 21
    doc["component_summaries"]["eval_contract"]["judge_output_field_count"] = 21

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_temporal_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_temporal_validity"] = 0
    doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_temporal_validity"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_language_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_language_access_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_language_access_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_entity_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_entity_resolution_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_entity_resolution_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_remedy_forum_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_remedy_forum_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_remedy_forum_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_authority_hierarchy_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_authority_hierarchy_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_authority_hierarchy_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_coverage_scope_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_coverage_scope_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_coverage_scope_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_jurisdiction_chain_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_jurisdiction_chain_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_jurisdiction_chain_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_implementation_access_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_implementation_status_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_implementation_status_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_blueprint_procedural_burden_contract_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["benchmark_tasks_requiring_procedural_burden_review"] = 0
    doc["component_summaries"]["benchmark_blueprint"][
        "tasks_requiring_procedural_burden_review"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_grounding_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_source_grounding_cases"] = 0
    doc["component_summaries"]["judge_calibration_plan"]["source_grounding_calibration_cases"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["judge_calibration_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["judge_calibration_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["judge_calibration_plan"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["judge_calibration_plan"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_temporal_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_temporal_validity_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_temporal_validity_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_language_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_language_access_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_language_access_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_entity_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_entity_resolution_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_entity_resolution_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_remedy_forum_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_remedy_forum_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_remedy_forum_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_authority_hierarchy_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_authority_hierarchy_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_authority_hierarchy_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_coverage_scope_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_coverage_scope_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_coverage_scope_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_jurisdiction_chain_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_jurisdiction_chain_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_jurisdiction_chain_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_implementation_access_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_implementation_access_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_implementation_access_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_judge_calibration_procedural_burden_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["judge_calibration_cases_requiring_procedural_burden_fields"] = 0
    doc["component_summaries"]["judge_calibration_plan"][
        "cases_requiring_procedural_burden_fields"
    ] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_source_grounding_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_source_grounding_rows"] = 0
    doc["component_summaries"]["transition_gate"]["source_grounding_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["transition_gate_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["transition_gate_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["transition_gate"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["transition_gate"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_readiness_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["readiness_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["readiness_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["readiness_bundle"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["readiness_bundle"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_next_actions_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["next_actions_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["next_actions_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["next_actions"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["next_actions"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_curator_sprint_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["curator_sprint_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["curator_sprint_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["component_summaries"]["curator_sprint"][
        "legal_claim_anchor_source_channel_count"
    ] = 3
    doc["component_summaries"]["curator_sprint"][
        "legal_claim_anchor_source_channel_ids"
    ] = list(broadened)

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_temporal_validity_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_temporal_validity_rows"] = 0
    doc["component_summaries"]["transition_gate"]["temporal_validity_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_language_access_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_language_access_rows"] = 0
    doc["component_summaries"]["transition_gate"]["language_access_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_entity_resolution_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_entity_resolution_rows"] = 0
    doc["component_summaries"]["transition_gate"]["entity_resolution_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_remedy_forum_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_remedy_forum_rows"] = 0
    doc["component_summaries"]["transition_gate"]["remedy_forum_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_authority_hierarchy_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_authority_hierarchy_rows"] = 0
    doc["component_summaries"]["transition_gate"]["authority_hierarchy_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_coverage_scope_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_coverage_scope_rows"] = 0
    doc["component_summaries"]["transition_gate"]["coverage_scope_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_jurisdiction_chain_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_jurisdiction_chain_rows"] = 0
    doc["component_summaries"]["transition_gate"]["jurisdiction_chain_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_implementation_access_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_implementation_access_rows"] = 0
    doc["component_summaries"]["transition_gate"]["implementation_access_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_transition_procedural_burden_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["transition_gate_procedural_burden_rows"] = 0
    doc["component_summaries"]["transition_gate"]["procedural_burden_transition_count"] = 0

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_execution_phase_coverage_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["next_execution_phase_covered_actions"] = 29
    doc["component_summaries"]["next_actions"]["execution_phase_covered_action_count"] = 29

    report = validator.validate_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_provenance_counts_match" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_component_summaries" not in report["summary"]["failed_check_ids"]
    assert "component_summaries_match_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_cli_accepts_saved_bundle(tmp_path, capsys):
    out = tmp_path / "global_protections_curation_bundle.json"
    out.write_text(json.dumps(_bundle_doc(), indent=2), encoding="utf-8")

    assert validator.main([str(out), "--component-dir", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert "failed=0/" in printed
    assert "phase_coverage=next:5/34,curator:5/34" in printed


def test_validator_cli_rejects_malformed_bundle(tmp_path, capsys):
    out = tmp_path / "global_protections_curation_bundle.json"
    out.write_text(json.dumps({"summary": {"consistency_ok": False}}, indent=2), encoding="utf-8")

    assert validator.main([str(out), "--skip-current-chain"]) == 1
    printed = capsys.readouterr().out
    assert "valid=false" in printed
    assert "schema_version_matches" in printed
