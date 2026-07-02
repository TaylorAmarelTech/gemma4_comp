"""Tests for the global protections top-level curation bundle."""
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


bundle = _load(
    "build_global_protections_curation_bundle",
    _ROOT / "scripts" / "build_global_protections_curation_bundle.py",
)


def test_global_protections_curation_bundle_summarizes_full_chain():
    doc = bundle.build_curation_bundle()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["safe_for_project_planning"] is True
    assert summary["registered_seed_domain_count"] == 1
    assert summary["regulatory_candidates_found_count"] == 11
    assert summary["jurisdiction_pack_scopes"] == 8
    assert summary["jurisdiction_pack_domain_lenses"] == 3
    assert summary["jurisdiction_pack_cells"] == 24
    assert summary["jurisdiction_pack_source_object_slots"] == 120
    assert summary["jurisdiction_pack_not_started_source_object_slots"] == 120
    assert summary["jurisdiction_pack_language_review_cells"] == 24
    assert summary["jurisdiction_pack_scope_resolution_cells"] == 3
    assert summary["jurisdiction_pack_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert summary["jurisdiction_pack_domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert summary["worker_prompt_count"] == 12
    assert summary["worker_prompts_blocked_for_comparable_run"] == 12
    assert summary["worker_verified_local_law_rows"] == 0
    assert summary["worker_source_object_tasks"] == 15
    assert summary["worker_scope_refinement_tasks"] == 8
    assert summary["regulatory_pattern_count"] == 11
    assert summary["regulatory_candidate_count"] == 10
    assert summary["regulatory_seed_scaffold_operations"] == 0
    assert summary["readiness_legal_claim_anchor_source_channel_count"] == 2
    assert summary["readiness_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["source_channel_matrix_rows"] == 70
    assert summary["source_channel_count"] == 10
    assert summary["source_channel_authority_tiers"] == 10
    assert summary["informal_publication_lead_rows"] == 7
    assert summary["source_channel_legal_claim_anchor_rows"] == 14
    assert summary["source_channel_legal_claim_anchor_source_channel_count"] == 2
    assert summary["source_channel_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["source_channel_authenticity_volatility_control_rows"] == 70
    assert summary["informal_publication_authenticity_volatility_control_rows"] == 7
    assert summary["source_channel_review_rows"] == 70
    assert summary["source_channel_review_not_started_rows"] == 70
    assert summary["source_channel_review_legal_claim_anchor_rows"] == 14
    assert summary["source_channel_review_legal_claim_anchor_source_channel_count"] == 2
    assert summary["source_channel_review_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["source_channel_review_lead_only_claim_rows"] == 7
    assert summary["source_channel_review_authenticity_volatility_rows"] == 70
    assert summary["source_channel_review_informal_authenticity_volatility_rows"] == 7
    assert summary["benchmark_task_blueprints"] == 7
    assert summary["benchmark_blueprints_blocked"] == 7
    assert summary["benchmark_scoring_dimensions"] == 6
    assert summary["benchmark_abstention_rules"] == 5
    assert summary["benchmark_task_source_grounding_contracts"] == 7
    assert summary["benchmark_tasks_requiring_legal_claim_anchor"] == 7
    assert summary["benchmark_legal_claim_anchor_source_channel_count"] == 2
    assert summary["benchmark_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["benchmark_tasks_requiring_source_gap_marker"] == 7
    assert summary["benchmark_tasks_barring_informal_standalone_claims"] == 7
    assert summary["benchmark_tasks_requiring_temporal_validity"] == 7
    assert summary["benchmark_tasks_requiring_language_access_review"] == 7
    assert summary["benchmark_tasks_requiring_entity_resolution_review"] == 7
    assert summary["benchmark_tasks_requiring_remedy_forum_review"] == 7
    assert summary["benchmark_tasks_requiring_authority_hierarchy_review"] == 7
    assert summary["benchmark_tasks_requiring_coverage_scope_review"] == 7
    assert summary["benchmark_tasks_requiring_jurisdiction_chain_review"] == 7
    assert summary["benchmark_tasks_requiring_implementation_status_review"] == 7
    assert summary["benchmark_tasks_requiring_procedural_burden_review"] == 7
    assert summary["eval_judge_dimension_contracts"] == 6
    assert summary["eval_failure_modes"] == 16
    assert summary["eval_run_gates"] == 18
    assert summary["eval_task_source_grounding_contracts"] == 7
    assert summary["eval_tasks_requiring_legal_claim_anchor"] == 7
    assert summary["eval_legal_claim_anchor_source_channel_count"] == 2
    assert summary["eval_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["eval_tasks_requiring_source_gap_marker"] == 7
    assert summary["eval_tasks_barring_informal_standalone_claims"] == 7
    assert summary["eval_tasks_requiring_temporal_validity"] == 7
    assert summary["eval_tasks_requiring_language_access_review"] == 7
    assert summary["eval_tasks_requiring_entity_resolution_review"] == 7
    assert summary["eval_tasks_requiring_remedy_forum_review"] == 7
    assert summary["eval_tasks_requiring_authority_hierarchy_review"] == 7
    assert summary["eval_tasks_requiring_coverage_scope_review"] == 7
    assert summary["eval_tasks_requiring_jurisdiction_chain_review"] == 7
    assert summary["eval_tasks_requiring_implementation_status_review"] == 7
    assert summary["eval_tasks_requiring_procedural_burden_review"] == 7
    assert summary["eval_model_response_record_fields"] == 32
    assert summary["eval_judge_output_fields"] == 22
    assert summary["diagnostic_cells"] == 7
    assert summary["diagnostic_cells_blocked"] == 7
    assert summary["diagnostic_failure_modes"] == 16
    assert summary["diagnostic_legal_claim_anchor_source_channel_count"] == 2
    assert summary["diagnostic_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["judge_calibration_cases"] == 16
    assert summary["judge_calibration_cases_blocked"] == 16
    assert summary["judge_calibration_critical_cases"] == 2
    assert summary["judge_calibration_source_grounding_failure_modes"] == 14
    assert summary["judge_calibration_source_grounding_cases"] == 14
    assert summary["judge_calibration_legal_claim_anchor_source_channel_count"] == 2
    assert summary["judge_calibration_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["judge_calibration_cases_requiring_source_grounding_findings"] == 16
    assert summary["judge_calibration_cases_requiring_legal_anchor_or_gap"] == 16
    assert summary["judge_calibration_cases_requiring_legal_anchor_source_channels"] == 16
    assert summary["judge_calibration_cases_requiring_temporal_validity_fields"] == 16
    assert summary["judge_calibration_cases_requiring_temporal_validity_findings"] == 16
    assert summary["judge_calibration_cases_requiring_language_access_fields"] == 16
    assert summary["judge_calibration_cases_requiring_language_access_findings"] == 16
    assert summary["judge_calibration_cases_requiring_entity_resolution_fields"] == 16
    assert summary["judge_calibration_cases_requiring_entity_resolution_findings"] == 16
    assert summary["judge_calibration_cases_requiring_remedy_forum_fields"] == 16
    assert summary["judge_calibration_cases_requiring_remedy_forum_findings"] == 16
    assert summary["judge_calibration_cases_requiring_authority_hierarchy_fields"] == 16
    assert summary["judge_calibration_cases_requiring_authority_hierarchy_findings"] == 16
    assert summary["judge_calibration_cases_requiring_coverage_scope_fields"] == 16
    assert summary["judge_calibration_cases_requiring_coverage_scope_findings"] == 16
    assert summary["judge_calibration_cases_requiring_jurisdiction_chain_fields"] == 16
    assert summary["judge_calibration_cases_requiring_jurisdiction_chain_findings"] == 16
    assert summary["judge_calibration_cases_requiring_implementation_access_fields"] == 16
    assert summary["judge_calibration_cases_requiring_implementation_access_findings"] == 16
    assert summary["judge_calibration_cases_requiring_procedural_burden_fields"] == 16
    assert summary["judge_calibration_cases_requiring_procedural_burden_findings"] == 16
    assert summary["transition_gate_rows"] == 9
    assert summary["transition_gate_blocked_rows"] == 9
    assert summary["transition_gate_source_grounding_rows"] == 4
    assert summary["transition_gate_temporal_validity_rows"] == 5
    assert summary["transition_gate_language_access_rows"] == 5
    assert summary["transition_gate_entity_resolution_rows"] == 5
    assert summary["transition_gate_remedy_forum_rows"] == 5
    assert summary["transition_gate_authority_hierarchy_rows"] == 5
    assert summary["transition_gate_coverage_scope_rows"] == 5
    assert summary["transition_gate_jurisdiction_chain_rows"] == 5
    assert summary["transition_gate_implementation_access_rows"] == 5
    assert summary["transition_gate_procedural_burden_rows"] == 5
    assert summary["transition_gate_legal_claim_anchor_source_channel_count"] == 2
    assert summary["transition_gate_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["transition_gate_rows_preserving_legal_anchor_source_channels"] == 9
    assert summary["next_action_count"] == 34
    assert summary["next_execution_phase_count"] == 5
    assert summary["next_execution_phase_covered_actions"] == 34
    assert summary["next_actions_legal_claim_anchor_source_channel_count"] == 2
    assert summary["next_actions_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["next_actions_preserving_legal_anchor_source_channels"] == 34
    assert summary["next_execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert summary["next_immediate_action_count"] == 24
    assert summary["next_blocked_action_count"] == 10
    assert summary["next_regulatory_priority_queue_items"] == 10
    assert summary["next_regulatory_top_candidate_id"]
    assert summary["curator_sprint_item_count"] == 24
    assert summary["curator_execution_phase_count"] == 5
    assert summary["curator_execution_phase_covered_actions"] == 34
    assert summary["curator_sprint_legal_claim_anchor_source_channel_count"] == 2
    assert summary["curator_sprint_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["curator_sprint_items_preserving_legal_anchor_source_channels"] == 24
    assert summary["curator_blocked_later_items_preserving_legal_anchor_source_channels"] == 10
    assert summary["curator_execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert summary["curator_regulatory_priority_queue_items"] == 10
    assert summary["curator_regulatory_top_candidate_id"] == summary["next_regulatory_top_candidate_id"]
    assert summary["curator_blocked_later_items"] == 10
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_global_protections_curation_bundle_keeps_payload_compact_and_safe():
    doc = bundle.build_curation_bundle()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert doc["component_summaries"]["project_plan"]["registered_seed_domain_count"] == 1
    assert doc["component_summaries"]["jurisdiction_pack_matrix"]["pack_cell_count"] == 24
    assert doc["component_summaries"]["jurisdiction_pack_matrix"]["jurisdiction_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert doc["component_summaries"]["jurisdiction_pack_matrix"]["domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert (
        doc["component_summaries"]["jurisdiction_pack_matrix"]["source_object_slot_count"]
        == 120
    )
    assert (
        doc["component_summaries"]["jurisdiction_pack_matrix"][
            "not_started_source_object_slots"
        ]
        == 120
    )
    assert doc["component_summaries"]["jurisdiction_pack_matrix"]["ready_for_comparable_scoring"] is False
    assert doc["component_summaries"]["source_channel_matrix"]["matrix_row_count"] == 70
    assert doc["component_summaries"]["source_channel_matrix"]["authority_tier_count"] == 10
    assert doc["component_summaries"]["source_channel_matrix"]["legal_claim_anchor_rows"] == 14
    assert (
        doc["component_summaries"]["source_channel_matrix"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["source_channel_matrix"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert (
        doc["component_summaries"]["source_channel_matrix"][
            "authenticity_volatility_control_rows"
        ]
        == 70
    )
    assert (
        doc["component_summaries"]["source_channel_matrix"][
            "informal_authenticity_volatility_control_rows"
        ]
        == 7
    )
    assert doc["component_summaries"]["source_channel_matrix"]["ready_for_manifest_promotion"] is False
    assert doc["component_summaries"]["source_channel_review_packet"]["review_row_count"] == 70
    assert doc["component_summaries"]["source_channel_review_packet"]["legal_claim_anchor_rows"] == 14
    assert (
        doc["component_summaries"]["source_channel_review_packet"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["source_channel_review_packet"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert doc["component_summaries"]["source_channel_review_packet"]["lead_only_claim_rows"] == 7
    assert (
        doc["component_summaries"]["source_channel_review_packet"][
            "authenticity_volatility_review_rows"
        ]
        == 70
    )
    assert (
        doc["component_summaries"]["source_channel_review_packet"][
            "informal_authenticity_volatility_review_rows"
        ]
        == 7
    )
    assert doc["component_summaries"]["source_channel_review_packet"]["ready_for_manifest_promotion"] is False
    assert doc["component_summaries"]["benchmark_blueprint"]["task_blueprint_count"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["blocked_task_blueprints"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["task_source_grounding_contract_count"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_legal_claim_anchor"] == 7
    assert (
        doc["component_summaries"]["benchmark_blueprint"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_source_gap_marker"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_barring_informal_standalone_claims"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_temporal_validity"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_language_access_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_entity_resolution_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_remedy_forum_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_authority_hierarchy_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_coverage_scope_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_jurisdiction_chain_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_implementation_status_review"] == 7
    assert doc["component_summaries"]["benchmark_blueprint"]["tasks_requiring_procedural_burden_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["judge_dimension_contract_count"] == 6
    assert doc["component_summaries"]["eval_contract"]["failure_mode_count"] == 16
    assert doc["component_summaries"]["eval_contract"]["task_source_grounding_contract_count"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_legal_claim_anchor"] == 7
    assert (
        doc["component_summaries"]["eval_contract"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_source_gap_marker"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_barring_informal_standalone_claims"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_temporal_validity"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_language_access_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_entity_resolution_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_remedy_forum_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_authority_hierarchy_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_coverage_scope_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_jurisdiction_chain_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_implementation_status_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["tasks_requiring_procedural_burden_review"] == 7
    assert doc["component_summaries"]["eval_contract"]["model_response_record_field_count"] == 32
    assert doc["component_summaries"]["eval_contract"]["judge_output_field_count"] == 22
    assert doc["component_summaries"]["eval_contract"]["ready_for_model_response_capture"] is False
    assert doc["component_summaries"]["eval_contract"]["ready_for_judge_calibration"] is False
    assert doc["component_summaries"]["diagnostic_run_plan"]["diagnostic_cell_count"] == 7
    assert doc["component_summaries"]["diagnostic_run_plan"]["blocked_diagnostic_cells"] == 7
    assert (
        doc["component_summaries"]["diagnostic_run_plan"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["diagnostic_run_plan"]["ready_for_model_response_capture"] is False
    assert doc["component_summaries"]["diagnostic_run_plan"]["ready_for_judge_calibration"] is False
    assert doc["component_summaries"]["judge_calibration_plan"]["calibration_case_count"] == 16
    assert doc["component_summaries"]["judge_calibration_plan"]["blocked_calibration_cases"] == 16
    assert (
        doc["component_summaries"]["judge_calibration_plan"]["source_grounding_failure_mode_count"]
        == 14
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"]["source_grounding_calibration_cases"]
        == 14
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["judge_calibration_plan"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_source_grounding_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_legal_anchor_or_gap"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_legal_anchor_source_channels"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_temporal_validity_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_temporal_validity_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_language_access_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_language_access_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_entity_resolution_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_entity_resolution_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_remedy_forum_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_remedy_forum_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_authority_hierarchy_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_authority_hierarchy_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_coverage_scope_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_coverage_scope_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_jurisdiction_chain_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_jurisdiction_chain_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_implementation_access_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_implementation_access_findings"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_procedural_burden_fields"
        ]
        == 16
    )
    assert (
        doc["component_summaries"]["judge_calibration_plan"][
            "cases_requiring_procedural_burden_findings"
        ]
        == 16
    )
    assert doc["component_summaries"]["judge_calibration_plan"]["ready_for_judge_calibration"] is False
    assert doc["component_summaries"]["judge_calibration_plan"]["ready_for_model_response_capture"] is False
    assert doc["component_summaries"]["transition_gate"]["transition_count"] == 9
    assert doc["component_summaries"]["transition_gate"]["blocked_transition_count"] == 9
    assert doc["component_summaries"]["transition_gate"]["source_grounding_transition_count"] == 4
    assert doc["component_summaries"]["transition_gate"]["temporal_validity_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["language_access_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["entity_resolution_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["remedy_forum_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["authority_hierarchy_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["coverage_scope_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["jurisdiction_chain_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["implementation_access_transition_count"] == 5
    assert doc["component_summaries"]["transition_gate"]["procedural_burden_transition_count"] == 5
    assert (
        doc["component_summaries"]["transition_gate"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["transition_gate"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert (
        doc["component_summaries"]["transition_gate"][
            "transitions_preserving_legal_anchor_source_channels"
        ]
        == 9
    )
    assert doc["component_summaries"]["transition_gate"]["ready_for_manifest_promotion"] is False
    assert doc["component_summaries"]["transition_gate"]["ready_for_model_response_capture"] is False
    assert doc["component_summaries"]["transition_gate"]["ready_for_judge_calibration"] is False
    assert doc["component_summaries"]["readiness_bundle"]["ready_for_prompt_generation"] is False
    assert doc["component_summaries"]["readiness_bundle"]["ready_for_training_use"] is False
    assert doc["component_summaries"]["readiness_bundle"]["ready_for_public_claims"] is False
    assert doc["component_summaries"]["readiness_bundle"]["ready_for_worker_facing_use"] is False
    assert doc["component_summaries"]["readiness_bundle"]["worker_source_object_tasks"] == 15
    assert doc["component_summaries"]["readiness_bundle"]["worker_scope_refinement_tasks"] == 8
    assert doc["component_summaries"]["readiness_bundle"]["regulatory_pattern_count"] == 11
    assert doc["component_summaries"]["readiness_bundle"]["regulatory_candidate_count"] == 10
    assert doc["component_summaries"]["readiness_bundle"]["regulatory_seed_scaffold_operations"] == 0
    assert (
        doc["component_summaries"]["readiness_bundle"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["readiness_bundle"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert doc["component_summaries"]["next_actions"]["action_count"] == 34
    assert doc["component_summaries"]["next_actions"]["execution_phase_count"] == 5
    assert doc["component_summaries"]["next_actions"]["execution_phase_covered_action_count"] == 34
    assert (
        doc["component_summaries"]["next_actions"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["next_actions"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert (
        doc["component_summaries"]["next_actions"][
            "actions_preserving_legal_anchor_source_channels"
        ]
        == 34
    )
    assert (
        doc["component_summaries"]["next_actions"][
            "execution_phases_preserving_legal_anchor_source_channels"
        ]
        == 5
    )
    assert doc["component_summaries"]["next_actions"]["regulatory_priority_queue_items"] == 10
    assert doc["component_summaries"]["next_actions"]["regulatory_top_candidate_id"]
    assert doc["component_summaries"]["curator_sprint"]["sprint_item_count"] == 24
    assert doc["component_summaries"]["curator_sprint"]["execution_phase_count"] == 5
    assert (
        doc["component_summaries"]["curator_sprint"]["execution_phase_covered_action_count"]
        == 34
    )
    assert (
        doc["component_summaries"]["curator_sprint"][
            "legal_claim_anchor_source_channel_count"
        ]
        == 2
    )
    assert doc["component_summaries"]["curator_sprint"][
        "legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert (
        doc["component_summaries"]["curator_sprint"][
            "sprint_items_preserving_legal_anchor_source_channels"
        ]
        == 24
    )
    assert (
        doc["component_summaries"]["curator_sprint"][
            "blocked_later_items_preserving_legal_anchor_source_channels"
        ]
        == 10
    )
    assert (
        doc["component_summaries"]["curator_sprint"][
            "execution_phases_preserving_legal_anchor_source_channels"
        ]
        == 5
    )
    assert doc["component_summaries"]["curator_sprint"]["regulatory_priority_queue_items"] == 10
    assert (
        doc["component_summaries"]["curator_sprint"]["regulatory_top_candidate_id"]
        == doc["component_summaries"]["next_actions"]["regulatory_top_candidate_id"]
    )
    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert "actions" not in doc
    assert "scope_resolution_items" not in doc
    assert "source_review_items" not in doc
    assert "_readiness_chain" not in doc


def test_global_protections_curation_bundle_markdown_lists_checks_and_paths():
    doc = bundle.build_curation_bundle()
    report = bundle.build_markdown_report(doc)

    assert "# Global Protections Curation Bundle" in report
    assert "Ready for comparable scoring" in report
    assert "Jurisdiction-pack cells" in report
    assert "Jurisdiction-pack scope IDs" in report
    assert "Jurisdiction-pack domain lens IDs" in report
    assert "Jurisdiction-pack source-object slots" in report
    assert "jurisdiction_pack_matrix_consistency_ok" in report
    assert "next_actions_match_curator_sprint" in report
    assert "regulatory_priority_queue_matches_curator_sprint" in report
    assert "Next regulatory top candidate" in report
    assert "Next execution phases" in report
    assert "Next phase-covered actions" in report
    assert "Next-actions legal-claim anchor source channels" in report
    assert "Next-actions preserving legal-anchor source channels" in report
    assert "Next execution phases preserving legal-anchor source channels" in report
    assert "Source-channel legal-claim anchor source channels" in report
    assert "Source-channel review legal-claim anchor source channels" in report
    assert "source_channel_matrix_legal_anchor_channels_match_source_policy" in report
    assert "source_channel_review_legal_anchor_channels_match_source_matrix" in report
    assert "next_actions_legal_anchor_channels_match_eval_contract" in report
    assert "Curator regulatory top candidate" in report
    assert "Curator execution phases" in report
    assert "Curator phase-covered actions" in report
    assert "Curator sprint legal-claim anchor source channels" in report
    assert "Curator sprint items preserving legal-anchor source channels" in report
    assert "Curator execution phases preserving legal-anchor source channels" in report
    assert "curator_sprint_legal_anchor_channels_match_next_actions" in report
    assert "worker_prompts_still_blocked" in report
    assert "Readiness legal-claim anchor source channels" in report
    assert "readiness_legal_anchor_channels_match_source_matrix" in report
    assert "Source-channel matrix rows" in report
    assert "Source-channel authenticity/volatility control rows" in report
    assert "Source-channel review rows" in report
    assert "Source-channel review authenticity/volatility rows" in report
    assert "Benchmark task blueprints" in report
    assert "Benchmark task source-grounding contracts" in report
    assert "Benchmark legal-claim anchor source channels" in report
    assert "Benchmark tasks barring informal standalone claims" in report
    assert "Benchmark tasks requiring temporal validity" in report
    assert "Benchmark tasks requiring language-access review" in report
    assert "Benchmark tasks requiring entity-resolution review" in report
    assert "Benchmark tasks requiring remedy/forum review" in report
    assert "Benchmark tasks requiring authority-hierarchy review" in report
    assert "Benchmark tasks requiring coverage-scope review" in report
    assert "Benchmark tasks requiring jurisdiction-chain review" in report
    assert "Benchmark tasks requiring implementation-status review" in report
    assert "Benchmark tasks requiring procedural-burden review" in report
    assert "benchmark_blueprint_consistency_ok" in report
    assert "Eval judge dimension contracts" in report
    assert "Eval task source-grounding contracts" in report
    assert "Eval legal-claim anchor source channels" in report
    assert "Eval tasks requiring temporal validity" in report
    assert "Eval tasks requiring language-access review" in report
    assert "Eval tasks requiring entity-resolution review" in report
    assert "Eval tasks requiring remedy/forum review" in report
    assert "Eval tasks requiring authority-hierarchy review" in report
    assert "Eval tasks requiring coverage-scope review" in report
    assert "Eval tasks requiring jurisdiction-chain review" in report
    assert "Eval tasks requiring implementation-status review" in report
    assert "Eval tasks requiring procedural-burden review" in report
    assert "Eval model response record fields" in report
    assert "eval_contract_consistency_ok" in report
    assert "Diagnostic cells" in report
    assert "Diagnostic legal-claim anchor source channels" in report
    assert "diagnostic_run_plan_consistency_ok" in report
    assert "Judge calibration cases" in report
    assert "Judge calibration source-grounding cases" in report
    assert "Judge calibration legal-claim anchor source channels" in report
    assert "Judge calibration cases requiring legal-anchor source channels" in report
    assert "Judge calibration cases requiring temporal-validity fields" in report
    assert "Judge calibration cases requiring language-access fields" in report
    assert "Judge calibration cases requiring entity-resolution fields" in report
    assert "Judge calibration cases requiring remedy/forum fields" in report
    assert "Judge calibration cases requiring authority-hierarchy fields" in report
    assert "Judge calibration cases requiring coverage-scope fields" in report
    assert "Judge calibration cases requiring jurisdiction-chain fields" in report
    assert "Judge calibration cases requiring implementation-access fields" in report
    assert "Judge calibration cases requiring procedural-burden fields" in report
    assert "judge_calibration_plan_consistency_ok" in report
    assert "Transition gate rows" in report
    assert "Transition gate source-grounding rows" in report
    assert "Transition gate temporal-validity rows" in report
    assert "Transition gate language-access rows" in report
    assert "Transition gate entity-resolution rows" in report
    assert "Transition gate remedy/forum rows" in report
    assert "Transition gate authority-hierarchy rows" in report
    assert "Transition gate coverage-scope rows" in report
    assert "Transition gate jurisdiction-chain rows" in report
    assert "Transition gate implementation-access rows" in report
    assert "Transition gate procedural-burden rows" in report
    assert "Transition gate legal-claim anchor source channels" in report
    assert "Transition gate rows preserving legal-anchor source channels" in report
    assert "transition_gate_consistency_ok" in report
    assert "Worker verified local-law rows" in report
    assert "Worker source-object tasks" in report
    assert "Worker scope-refinement tasks" in report
    assert "Regulatory patterns" in report
    assert "Regulatory candidate domains" in report
    assert "Regulatory seed scaffold operations" in report
    assert "global_protections_curator_sprint_json" in report
    assert "not comparable benchmark evidence" in report


def test_global_protections_curation_bundle_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    md_out = tmp_path / "bundle.md"

    assert bundle.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "24 sprint items" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["curator_sprint_item_count"] == 24
    assert md_out.exists()
    assert "# Global Protections Curation Bundle" in md_out.read_text(encoding="utf-8")


def test_global_protections_curation_bundle_can_write_components_to_custom_dir(tmp_path):
    out = tmp_path / "bundle.json"
    component_dir = tmp_path / "components"

    assert bundle.main([
        "--out",
        str(out),
        "--no-md",
        "--write-components",
        "--component-dir",
        str(component_dir),
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["global_protections_project_plan_json"] == (
        "external/global_protections_project_plan.json"
    )
    assert doc["artifact_paths"]["global_protections_jurisdiction_pack_matrix_json"] == (
        "external/global_protections_jurisdiction_pack_matrix.json"
    )
    assert doc["artifact_paths"]["global_protections_source_channel_review_packet_json"] == (
        "external/global_protections_source_channel_review_packet.json"
    )
    assert doc["artifact_paths"]["global_protections_benchmark_blueprint_json"] == (
        "external/global_protections_benchmark_blueprint.json"
    )
    assert doc["artifact_paths"]["global_protections_eval_contract_json"] == (
        "external/global_protections_eval_contract.json"
    )
    assert doc["artifact_paths"]["global_protections_diagnostic_run_plan_json"] == (
        "external/global_protections_diagnostic_run_plan.json"
    )
    assert doc["artifact_paths"]["global_protections_judge_calibration_plan_json"] == (
        "external/global_protections_judge_calibration_plan.json"
    )
    assert doc["artifact_paths"]["global_protections_transition_gate_json"] == (
        "external/global_protections_transition_gate.json"
    )
    assert doc["artifact_paths"]["global_protections_curation_bundle_json"] == "external/bundle.json"
    assert (component_dir / "global_protections_project_plan.json").exists()
    assert (component_dir / "global_protections_jurisdiction_pack_matrix.json").exists()
    assert (component_dir / "global_protections_source_channel_matrix.json").exists()
    assert (component_dir / "global_protections_source_channel_review_packet.json").exists()
    assert (component_dir / "global_protections_benchmark_blueprint.json").exists()
    assert (component_dir / "global_protections_eval_contract.json").exists()
    assert (component_dir / "global_protections_diagnostic_run_plan.json").exists()
    assert (component_dir / "global_protections_judge_calibration_plan.json").exists()
    assert (component_dir / "global_protections_transition_gate.json").exists()
    assert (component_dir / "global_protections_readiness_bundle.json").exists()
    assert (component_dir / "global_protections_next_actions.json").exists()
    assert (component_dir / "global_protections_curator_sprint.json").exists()


def test_global_protections_curation_bundle_can_write_all_components_to_custom_dir(tmp_path):
    out = tmp_path / "bundle.json"
    component_dir = tmp_path / "components"

    assert bundle.main([
        "--out",
        str(out),
        "--no-md",
        "--write-all-components",
        "--component-dir",
        str(component_dir),
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["domain_curation_bundle_json"] == (
        "external/developing_country_worker_protections_curation_bundle.json"
    )
    assert doc["artifact_paths"]["source_review_validation_json"] == (
        "external/developing_country_worker_protections_source_review_validation.json"
    )
    assert doc["artifact_paths"]["domain_seed_proposal_json"] == (
        "external/regulatory_domain_seed_proposal.json"
    )
    assert doc["artifact_paths"]["global_protections_curation_bundle_json"] == "external/bundle.json"
    assert (component_dir / "developing_country_worker_protections_curation_bundle.json").exists()
    assert (component_dir / "developing_country_worker_protections_source_review_validation.json").exists()
    assert (component_dir / "regulatory_curation_bundle.json").exists()
    assert (component_dir / "regulatory_domain_seed_proposal.json").exists()
