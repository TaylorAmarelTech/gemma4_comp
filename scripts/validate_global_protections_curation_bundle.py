#!/usr/bin/env python3
"""Validate a saved global protections curation bundle artifact.

The curation-bundle builder proves the project stack in memory. This validator
checks a saved JSON artifact before anyone treats it as a current handoff:
shape, safety gates, compactness, privacy scan, artifact-path hygiene, and
summary counts against the current source-gated chain.

Offline + deterministic. No model, no network, no credits. Read-only.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_global_protections_curation_bundle as curation_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402

DEFAULT_BUNDLE = curation_builder.OUT
DEFAULT_DOMAIN = curation_builder.DEFAULT_DOMAIN

REQUIRED_TOP_LEVEL = frozenset({
    "_meta",
    "summary",
    "component_summaries",
    "checks",
    "artifact_paths",
})
REQUIRED_COMPONENTS = frozenset({
    "project_plan",
    "jurisdiction_pack_matrix",
    "source_channel_matrix",
    "source_channel_review_packet",
    "benchmark_blueprint",
    "eval_contract",
    "diagnostic_run_plan",
    "judge_calibration_plan",
    "transition_gate",
    "readiness_bundle",
    "next_actions",
    "curator_sprint",
})
REQUIRED_ARTIFACT_KEYS = frozenset({
    "global_protections_project_plan_json",
    "global_protections_project_plan_markdown",
    "global_protections_jurisdiction_pack_matrix_json",
    "global_protections_jurisdiction_pack_matrix_markdown",
    "global_protections_source_channel_matrix_json",
    "global_protections_source_channel_matrix_markdown",
    "global_protections_source_channel_review_packet_json",
    "global_protections_source_channel_review_packet_markdown",
    "global_protections_benchmark_blueprint_json",
    "global_protections_benchmark_blueprint_markdown",
    "global_protections_eval_contract_json",
    "global_protections_eval_contract_markdown",
    "global_protections_diagnostic_run_plan_json",
    "global_protections_diagnostic_run_plan_markdown",
    "global_protections_judge_calibration_plan_json",
    "global_protections_judge_calibration_plan_markdown",
    "global_protections_transition_gate_json",
    "global_protections_transition_gate_markdown",
    "global_protections_readiness_bundle_json",
    "global_protections_readiness_bundle_markdown",
    "global_protections_next_actions_json",
    "global_protections_next_actions_markdown",
    "global_protections_curator_sprint_json",
    "global_protections_curator_sprint_markdown",
    "global_protections_curation_bundle_json",
    "global_protections_curation_bundle_markdown",
    "domain",
})
RAW_PAYLOAD_KEYS = frozenset({
    "_domain_chain",
    "_readiness_chain",
    "_regulatory_chain",
    "actions",
    "scope_resolution_items",
    "source_review_items",
    "regulatory_candidate_intake_items",
    "blocked_later_items",
})
READY_FLAG_KEYS = (
    "ready_for_prompt_generation",
    "ready_for_training_use",
    "ready_for_public_claims",
    "ready_for_worker_facing_use",
    "ready_for_comparable_scoring",
)
COMPONENTS_WITH_CONSISTENCY = frozenset({
    "jurisdiction_pack_matrix",
    "source_channel_matrix",
    "source_channel_review_packet",
    "benchmark_blueprint",
    "eval_contract",
    "diagnostic_run_plan",
    "judge_calibration_plan",
    "transition_gate",
    "readiness_bundle",
    "next_actions",
    "curator_sprint",
})
COMPONENT_BLOCKING_RULES = (
    ("jurisdiction_pack_matrix", "not_started_source_object_slots", "source_object_slot_count"),
    ("source_channel_review_packet", "not_started_rows", "review_row_count"),
    ("benchmark_blueprint", "blocked_task_blueprints", "task_blueprint_count"),
    ("diagnostic_run_plan", "blocked_diagnostic_cells", "diagnostic_cell_count"),
    ("judge_calibration_plan", "blocked_calibration_cases", "calibration_case_count"),
    ("transition_gate", "blocked_transition_count", "transition_count"),
    ("readiness_bundle", "worker_prompts_blocked_for_comparable_run", "worker_prompt_count"),
)
COMPONENT_ZERO_RULES = (
    ("source_channel_review_packet", "rows_ready_for_manifest_promotion", 0),
    ("readiness_bundle", "worker_verified_local_law_rows", 0),
    ("readiness_bundle", "regulatory_seed_scaffold_operations", 0),
)
DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]
_URL = re.compile(r"\b(?:https?://|www\.)", re.I)
_LOCAL_ABS = re.compile(r"(?:^[A-Za-z]:[\\/]|^\\\\|^/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|^~[\\/])", re.I)


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def _failed_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [str(check["id"]) for check in checks if check.get("ok") is not True]


def _unsafe_artifact_paths(paths: Any) -> list[dict[str, str]]:
    if not isinstance(paths, dict):
        return [{"key": "$", "value": "artifact_paths_not_object"}]
    findings: list[dict[str, str]] = []
    for key, value in paths.items():
        if key == "domain":
            continue
        if not isinstance(value, str) or not value.strip():
            findings.append({"key": str(key), "value": "missing_or_not_string"})
            continue
        if _URL.search(value) or _LOCAL_ABS.search(value) or "\\" in value:
            findings.append({"key": str(key), "value": value})
    return findings


def _count_mismatches(doc: dict[str, Any]) -> list[dict[str, Any]]:
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    components = doc.get("component_summaries") if isinstance(doc.get("component_summaries"), dict) else {}
    project = components.get("project_plan") if isinstance(components.get("project_plan"), dict) else {}
    jurisdiction_pack = (
        components.get("jurisdiction_pack_matrix")
        if isinstance(components.get("jurisdiction_pack_matrix"), dict)
        else {}
    )
    source_matrix = (
        components.get("source_channel_matrix")
        if isinstance(components.get("source_channel_matrix"), dict)
        else {}
    )
    source_review = (
        components.get("source_channel_review_packet")
        if isinstance(components.get("source_channel_review_packet"), dict)
        else {}
    )
    benchmark_blueprint = (
        components.get("benchmark_blueprint")
        if isinstance(components.get("benchmark_blueprint"), dict)
        else {}
    )
    eval_contract = (
        components.get("eval_contract")
        if isinstance(components.get("eval_contract"), dict)
        else {}
    )
    diagnostic_run_plan = (
        components.get("diagnostic_run_plan")
        if isinstance(components.get("diagnostic_run_plan"), dict)
        else {}
    )
    judge_calibration_plan = (
        components.get("judge_calibration_plan")
        if isinstance(components.get("judge_calibration_plan"), dict)
        else {}
    )
    transition_gate = (
        components.get("transition_gate")
        if isinstance(components.get("transition_gate"), dict)
        else {}
    )
    readiness = components.get("readiness_bundle") if isinstance(components.get("readiness_bundle"), dict) else {}
    next_actions = components.get("next_actions") if isinstance(components.get("next_actions"), dict) else {}
    sprint = components.get("curator_sprint") if isinstance(components.get("curator_sprint"), dict) else {}
    pairs = [
        ("registered_seed_domain_count", project, "registered_seed_domain_count"),
        ("regulatory_candidates_found_count", project, "regulatory_candidates_found_count"),
        ("jurisdiction_pack_scopes", jurisdiction_pack, "jurisdiction_scope_count"),
        ("jurisdiction_pack_scope_ids", jurisdiction_pack, "jurisdiction_scope_ids"),
        ("jurisdiction_pack_domain_lenses", jurisdiction_pack, "domain_lens_count"),
        ("jurisdiction_pack_domain_lens_ids", jurisdiction_pack, "domain_lens_ids"),
        ("jurisdiction_pack_cells", jurisdiction_pack, "pack_cell_count"),
        (
            "jurisdiction_pack_source_object_slots",
            jurisdiction_pack,
            "source_object_slot_count",
        ),
        (
            "jurisdiction_pack_not_started_source_object_slots",
            jurisdiction_pack,
            "not_started_source_object_slots",
        ),
        (
            "jurisdiction_pack_language_review_cells",
            jurisdiction_pack,
            "language_review_required_cells",
        ),
        (
            "jurisdiction_pack_scope_resolution_cells",
            jurisdiction_pack,
            "scope_resolution_required_cells",
        ),
        ("source_channel_matrix_rows", source_matrix, "matrix_row_count"),
        ("source_channel_count", source_matrix, "source_channel_count"),
        ("source_channel_authority_tiers", source_matrix, "authority_tier_count"),
        ("informal_publication_lead_rows", source_matrix, "informal_publication_rows"),
        ("source_channel_legal_claim_anchor_rows", source_matrix, "legal_claim_anchor_rows"),
        (
            "source_channel_legal_claim_anchor_source_channel_count",
            source_matrix,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "source_channel_legal_claim_anchor_source_channel_ids",
            source_matrix,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "source_channel_authenticity_volatility_control_rows",
            source_matrix,
            "authenticity_volatility_control_rows",
        ),
        (
            "informal_publication_authenticity_volatility_control_rows",
            source_matrix,
            "informal_authenticity_volatility_control_rows",
        ),
        ("source_channel_review_rows", source_review, "review_row_count"),
        ("source_channel_review_not_started_rows", source_review, "not_started_rows"),
        ("source_channel_review_legal_claim_anchor_rows", source_review, "legal_claim_anchor_rows"),
        (
            "source_channel_review_legal_claim_anchor_source_channel_count",
            source_review,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "source_channel_review_legal_claim_anchor_source_channel_ids",
            source_review,
            "legal_claim_anchor_source_channel_ids",
        ),
        ("source_channel_review_lead_only_claim_rows", source_review, "lead_only_claim_rows"),
        (
            "source_channel_review_authenticity_volatility_rows",
            source_review,
            "authenticity_volatility_review_rows",
        ),
        (
            "source_channel_review_informal_authenticity_volatility_rows",
            source_review,
            "informal_authenticity_volatility_review_rows",
        ),
        ("benchmark_task_blueprints", benchmark_blueprint, "task_blueprint_count"),
        ("benchmark_blueprints_blocked", benchmark_blueprint, "blocked_task_blueprints"),
        ("benchmark_scoring_dimensions", benchmark_blueprint, "scoring_dimension_count"),
        ("benchmark_abstention_rules", benchmark_blueprint, "abstention_rule_count"),
        (
            "benchmark_task_source_grounding_contracts",
            benchmark_blueprint,
            "task_source_grounding_contract_count",
        ),
        (
            "benchmark_tasks_requiring_legal_claim_anchor",
            benchmark_blueprint,
            "tasks_requiring_legal_claim_anchor",
        ),
        (
            "benchmark_legal_claim_anchor_source_channel_count",
            benchmark_blueprint,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "benchmark_legal_claim_anchor_source_channel_ids",
            benchmark_blueprint,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "benchmark_tasks_requiring_source_gap_marker",
            benchmark_blueprint,
            "tasks_requiring_source_gap_marker",
        ),
        (
            "benchmark_tasks_barring_informal_standalone_claims",
            benchmark_blueprint,
            "tasks_barring_informal_standalone_claims",
        ),
        (
            "benchmark_tasks_requiring_temporal_validity",
            benchmark_blueprint,
            "tasks_requiring_temporal_validity",
        ),
        (
            "benchmark_tasks_requiring_language_access_review",
            benchmark_blueprint,
            "tasks_requiring_language_access_review",
        ),
        (
            "benchmark_tasks_requiring_entity_resolution_review",
            benchmark_blueprint,
            "tasks_requiring_entity_resolution_review",
        ),
        (
            "benchmark_tasks_requiring_remedy_forum_review",
            benchmark_blueprint,
            "tasks_requiring_remedy_forum_review",
        ),
        (
            "benchmark_tasks_requiring_authority_hierarchy_review",
            benchmark_blueprint,
            "tasks_requiring_authority_hierarchy_review",
        ),
        (
            "benchmark_tasks_requiring_coverage_scope_review",
            benchmark_blueprint,
            "tasks_requiring_coverage_scope_review",
        ),
        (
            "benchmark_tasks_requiring_jurisdiction_chain_review",
            benchmark_blueprint,
            "tasks_requiring_jurisdiction_chain_review",
        ),
        (
            "benchmark_tasks_requiring_implementation_status_review",
            benchmark_blueprint,
            "tasks_requiring_implementation_status_review",
        ),
        (
            "benchmark_tasks_requiring_procedural_burden_review",
            benchmark_blueprint,
            "tasks_requiring_procedural_burden_review",
        ),
        ("eval_judge_dimension_contracts", eval_contract, "judge_dimension_contract_count"),
        ("eval_failure_modes", eval_contract, "failure_mode_count"),
        ("eval_run_gates", eval_contract, "run_gate_count"),
        (
            "eval_task_source_grounding_contracts",
            eval_contract,
            "task_source_grounding_contract_count",
        ),
        (
            "eval_tasks_requiring_legal_claim_anchor",
            eval_contract,
            "tasks_requiring_legal_claim_anchor",
        ),
        (
            "eval_legal_claim_anchor_source_channel_count",
            eval_contract,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "eval_legal_claim_anchor_source_channel_ids",
            eval_contract,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "eval_tasks_requiring_source_gap_marker",
            eval_contract,
            "tasks_requiring_source_gap_marker",
        ),
        (
            "eval_tasks_barring_informal_standalone_claims",
            eval_contract,
            "tasks_barring_informal_standalone_claims",
        ),
        (
            "eval_tasks_requiring_temporal_validity",
            eval_contract,
            "tasks_requiring_temporal_validity",
        ),
        (
            "eval_tasks_requiring_language_access_review",
            eval_contract,
            "tasks_requiring_language_access_review",
        ),
        (
            "eval_tasks_requiring_entity_resolution_review",
            eval_contract,
            "tasks_requiring_entity_resolution_review",
        ),
        (
            "eval_tasks_requiring_remedy_forum_review",
            eval_contract,
            "tasks_requiring_remedy_forum_review",
        ),
        (
            "eval_tasks_requiring_authority_hierarchy_review",
            eval_contract,
            "tasks_requiring_authority_hierarchy_review",
        ),
        (
            "eval_tasks_requiring_coverage_scope_review",
            eval_contract,
            "tasks_requiring_coverage_scope_review",
        ),
        (
            "eval_tasks_requiring_jurisdiction_chain_review",
            eval_contract,
            "tasks_requiring_jurisdiction_chain_review",
        ),
        (
            "eval_tasks_requiring_implementation_status_review",
            eval_contract,
            "tasks_requiring_implementation_status_review",
        ),
        (
            "eval_tasks_requiring_procedural_burden_review",
            eval_contract,
            "tasks_requiring_procedural_burden_review",
        ),
        ("eval_model_response_record_fields", eval_contract, "model_response_record_field_count"),
        ("eval_judge_output_fields", eval_contract, "judge_output_field_count"),
        ("diagnostic_cells", diagnostic_run_plan, "diagnostic_cell_count"),
        ("diagnostic_cells_blocked", diagnostic_run_plan, "blocked_diagnostic_cells"),
        ("diagnostic_failure_modes", diagnostic_run_plan, "failure_mode_count"),
        (
            "diagnostic_legal_claim_anchor_source_channel_count",
            diagnostic_run_plan,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "diagnostic_legal_claim_anchor_source_channel_ids",
            diagnostic_run_plan,
            "legal_claim_anchor_source_channel_ids",
        ),
        ("judge_calibration_cases", judge_calibration_plan, "calibration_case_count"),
        ("judge_calibration_cases_blocked", judge_calibration_plan, "blocked_calibration_cases"),
        ("judge_calibration_critical_cases", judge_calibration_plan, "critical_calibration_cases"),
        (
            "judge_calibration_source_grounding_failure_modes",
            judge_calibration_plan,
            "source_grounding_failure_mode_count",
        ),
        (
            "judge_calibration_source_grounding_cases",
            judge_calibration_plan,
            "source_grounding_calibration_cases",
        ),
        (
            "judge_calibration_legal_claim_anchor_source_channel_count",
            judge_calibration_plan,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "judge_calibration_legal_claim_anchor_source_channel_ids",
            judge_calibration_plan,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "judge_calibration_cases_requiring_source_grounding_findings",
            judge_calibration_plan,
            "cases_requiring_source_grounding_findings",
        ),
        (
            "judge_calibration_cases_requiring_legal_anchor_or_gap",
            judge_calibration_plan,
            "cases_requiring_legal_anchor_or_gap",
        ),
        (
            "judge_calibration_cases_requiring_legal_anchor_source_channels",
            judge_calibration_plan,
            "cases_requiring_legal_anchor_source_channels",
        ),
        (
            "judge_calibration_cases_requiring_temporal_validity_fields",
            judge_calibration_plan,
            "cases_requiring_temporal_validity_fields",
        ),
        (
            "judge_calibration_cases_requiring_temporal_validity_findings",
            judge_calibration_plan,
            "cases_requiring_temporal_validity_findings",
        ),
        (
            "judge_calibration_cases_requiring_language_access_fields",
            judge_calibration_plan,
            "cases_requiring_language_access_fields",
        ),
        (
            "judge_calibration_cases_requiring_language_access_findings",
            judge_calibration_plan,
            "cases_requiring_language_access_findings",
        ),
        (
            "judge_calibration_cases_requiring_entity_resolution_fields",
            judge_calibration_plan,
            "cases_requiring_entity_resolution_fields",
        ),
        (
            "judge_calibration_cases_requiring_entity_resolution_findings",
            judge_calibration_plan,
            "cases_requiring_entity_resolution_findings",
        ),
        (
            "judge_calibration_cases_requiring_remedy_forum_fields",
            judge_calibration_plan,
            "cases_requiring_remedy_forum_fields",
        ),
        (
            "judge_calibration_cases_requiring_remedy_forum_findings",
            judge_calibration_plan,
            "cases_requiring_remedy_forum_findings",
        ),
        (
            "judge_calibration_cases_requiring_authority_hierarchy_fields",
            judge_calibration_plan,
            "cases_requiring_authority_hierarchy_fields",
        ),
        (
            "judge_calibration_cases_requiring_authority_hierarchy_findings",
            judge_calibration_plan,
            "cases_requiring_authority_hierarchy_findings",
        ),
        (
            "judge_calibration_cases_requiring_coverage_scope_fields",
            judge_calibration_plan,
            "cases_requiring_coverage_scope_fields",
        ),
        (
            "judge_calibration_cases_requiring_coverage_scope_findings",
            judge_calibration_plan,
            "cases_requiring_coverage_scope_findings",
        ),
        (
            "judge_calibration_cases_requiring_jurisdiction_chain_fields",
            judge_calibration_plan,
            "cases_requiring_jurisdiction_chain_fields",
        ),
        (
            "judge_calibration_cases_requiring_jurisdiction_chain_findings",
            judge_calibration_plan,
            "cases_requiring_jurisdiction_chain_findings",
        ),
        (
            "judge_calibration_cases_requiring_implementation_access_fields",
            judge_calibration_plan,
            "cases_requiring_implementation_access_fields",
        ),
        (
            "judge_calibration_cases_requiring_implementation_access_findings",
            judge_calibration_plan,
            "cases_requiring_implementation_access_findings",
        ),
        (
            "judge_calibration_cases_requiring_procedural_burden_fields",
            judge_calibration_plan,
            "cases_requiring_procedural_burden_fields",
        ),
        (
            "judge_calibration_cases_requiring_procedural_burden_findings",
            judge_calibration_plan,
            "cases_requiring_procedural_burden_findings",
        ),
        ("transition_gate_rows", transition_gate, "transition_count"),
        ("transition_gate_blocked_rows", transition_gate, "blocked_transition_count"),
        ("transition_gate_source_grounding_rows", transition_gate, "source_grounding_transition_count"),
        ("transition_gate_temporal_validity_rows", transition_gate, "temporal_validity_transition_count"),
        ("transition_gate_language_access_rows", transition_gate, "language_access_transition_count"),
        ("transition_gate_entity_resolution_rows", transition_gate, "entity_resolution_transition_count"),
        ("transition_gate_remedy_forum_rows", transition_gate, "remedy_forum_transition_count"),
        (
            "transition_gate_authority_hierarchy_rows",
            transition_gate,
            "authority_hierarchy_transition_count",
        ),
        ("transition_gate_coverage_scope_rows", transition_gate, "coverage_scope_transition_count"),
        ("transition_gate_jurisdiction_chain_rows", transition_gate, "jurisdiction_chain_transition_count"),
        ("transition_gate_implementation_access_rows", transition_gate, "implementation_access_transition_count"),
        ("transition_gate_procedural_burden_rows", transition_gate, "procedural_burden_transition_count"),
        (
            "transition_gate_legal_claim_anchor_source_channel_count",
            transition_gate,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "transition_gate_legal_claim_anchor_source_channel_ids",
            transition_gate,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "transition_gate_rows_preserving_legal_anchor_source_channels",
            transition_gate,
            "transitions_preserving_legal_anchor_source_channels",
        ),
        ("worker_prompt_count", readiness, "worker_prompt_count"),
        ("worker_prompts_blocked_for_comparable_run", readiness, "worker_prompts_blocked_for_comparable_run"),
        ("worker_verified_local_law_rows", readiness, "worker_verified_local_law_rows"),
        ("worker_source_object_tasks", readiness, "worker_source_object_tasks"),
        ("worker_scope_refinement_tasks", readiness, "worker_scope_refinement_tasks"),
        ("regulatory_pattern_count", readiness, "regulatory_pattern_count"),
        ("regulatory_candidate_count", readiness, "regulatory_candidate_count"),
        (
            "regulatory_seed_scaffold_operations",
            readiness,
            "regulatory_seed_scaffold_operations",
        ),
        (
            "readiness_legal_claim_anchor_source_channel_count",
            readiness,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "readiness_legal_claim_anchor_source_channel_ids",
            readiness,
            "legal_claim_anchor_source_channel_ids",
        ),
        ("next_action_count", next_actions, "action_count"),
        ("next_execution_phase_count", next_actions, "execution_phase_count"),
        (
            "next_execution_phase_covered_actions",
            next_actions,
            "execution_phase_covered_action_count",
        ),
        (
            "next_actions_legal_claim_anchor_source_channel_count",
            next_actions,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "next_actions_legal_claim_anchor_source_channel_ids",
            next_actions,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "next_actions_preserving_legal_anchor_source_channels",
            next_actions,
            "actions_preserving_legal_anchor_source_channels",
        ),
        (
            "next_execution_phases_preserving_legal_anchor_source_channels",
            next_actions,
            "execution_phases_preserving_legal_anchor_source_channels",
        ),
        ("next_immediate_action_count", next_actions, "immediate_action_count"),
        ("next_blocked_action_count", next_actions, "blocked_action_count"),
        (
            "next_regulatory_priority_queue_items",
            next_actions,
            "regulatory_priority_queue_items",
        ),
        ("next_regulatory_top_candidate_id", next_actions, "regulatory_top_candidate_id"),
        ("curator_sprint_item_count", sprint, "sprint_item_count"),
        ("curator_execution_phase_count", sprint, "execution_phase_count"),
        (
            "curator_execution_phase_covered_actions",
            sprint,
            "execution_phase_covered_action_count",
        ),
        (
            "curator_sprint_legal_claim_anchor_source_channel_count",
            sprint,
            "legal_claim_anchor_source_channel_count",
        ),
        (
            "curator_sprint_legal_claim_anchor_source_channel_ids",
            sprint,
            "legal_claim_anchor_source_channel_ids",
        ),
        (
            "curator_sprint_items_preserving_legal_anchor_source_channels",
            sprint,
            "sprint_items_preserving_legal_anchor_source_channels",
        ),
        (
            "curator_blocked_later_items_preserving_legal_anchor_source_channels",
            sprint,
            "blocked_later_items_preserving_legal_anchor_source_channels",
        ),
        (
            "curator_execution_phases_preserving_legal_anchor_source_channels",
            sprint,
            "execution_phases_preserving_legal_anchor_source_channels",
        ),
        (
            "curator_regulatory_priority_queue_items",
            sprint,
            "regulatory_priority_queue_items",
        ),
        ("curator_regulatory_top_candidate_id", sprint, "regulatory_top_candidate_id"),
        ("curator_blocked_later_items", sprint, "blocked_later_items"),
    ]
    mismatches: list[dict[str, Any]] = []
    for summary_key, component_summary, component_key in pairs:
        actual = summary.get(summary_key)
        expected = component_summary.get(component_key)
        if actual != expected:
            mismatches.append({
                "summary_key": summary_key,
                "component_key": component_key,
                "expected": expected,
                "actual": actual,
            })
    return mismatches


def _component_provenance_mismatches(components: Any) -> list[dict[str, Any]]:
    if not isinstance(components, dict):
        return [{"component": "$", "actual": "component_summaries_not_object"}]
    mismatches: list[dict[str, Any]] = []
    jurisdiction_pack = components.get("jurisdiction_pack_matrix")
    source_matrix = components.get("source_channel_matrix")
    source_review = components.get("source_channel_review_packet")
    benchmark_blueprint = components.get("benchmark_blueprint")
    eval_contract = components.get("eval_contract")
    diagnostic_run_plan = components.get("diagnostic_run_plan")
    judge_calibration = components.get("judge_calibration_plan")
    transition_gate = components.get("transition_gate")
    readiness = components.get("readiness_bundle")
    project_plan = components.get("project_plan")
    next_actions = components.get("next_actions")
    curator_sprint = components.get("curator_sprint")
    if not isinstance(project_plan, dict):
        mismatches.append({
            "component": "project_plan",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        project_plan = {}
    if not isinstance(jurisdiction_pack, dict):
        mismatches.append({
            "component": "jurisdiction_pack_matrix",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        jurisdiction_pack = {}
    if not isinstance(source_matrix, dict):
        mismatches.append({
            "component": "source_channel_matrix",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        source_matrix = {}

    pack_cell_count = jurisdiction_pack.get("pack_cell_count")
    scope_count = jurisdiction_pack.get("jurisdiction_scope_count")
    lens_count = jurisdiction_pack.get("domain_lens_count")
    expected_pack_cells = (
        scope_count * lens_count
        if isinstance(scope_count, int) and isinstance(lens_count, int)
        else "jurisdiction_scope_count * domain_lens_count"
    )
    if pack_cell_count != expected_pack_cells:
        mismatches.append({
            "component": "jurisdiction_pack_matrix",
            "rule": "pack_cell_count_equals_scope_lens_cross_product",
            "expected": expected_pack_cells,
            "actual": pack_cell_count,
        })
    pack_slots = jurisdiction_pack.get("source_object_slot_count")
    not_started_slots = jurisdiction_pack.get("not_started_source_object_slots")
    if not_started_slots != pack_slots:
        mismatches.append({
            "component": "jurisdiction_pack_matrix",
            "rule": "not_started_source_object_slots_match_total_slots",
            "expected": pack_slots,
            "actual": not_started_slots,
        })
    if not isinstance(source_review, dict):
        mismatches.append({
            "component": "source_channel_review_packet",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        source_review = {}
    if not isinstance(benchmark_blueprint, dict):
        mismatches.append({
            "component": "benchmark_blueprint",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        benchmark_blueprint = {}
    if not isinstance(eval_contract, dict):
        mismatches.append({
            "component": "eval_contract",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        eval_contract = {}
    if not isinstance(diagnostic_run_plan, dict):
        mismatches.append({
            "component": "diagnostic_run_plan",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        diagnostic_run_plan = {}
    if not isinstance(judge_calibration, dict):
        mismatches.append({
            "component": "judge_calibration_plan",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        judge_calibration = {}
    if not isinstance(transition_gate, dict):
        mismatches.append({
            "component": "transition_gate",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        transition_gate = {}
    if not isinstance(readiness, dict):
        mismatches.append({
            "component": "readiness_bundle",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        readiness = {}
    if not isinstance(next_actions, dict):
        mismatches.append({
            "component": "next_actions",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        next_actions = {}
    if not isinstance(curator_sprint, dict):
        mismatches.append({
            "component": "curator_sprint",
            "rule": "summary_object_present",
            "expected": "component_summary_object",
            "actual": "missing_or_not_object",
        })
        curator_sprint = {}

    source_channel_count = source_matrix.get("source_channel_count")
    authority_tier_count = source_matrix.get("authority_tier_count")
    if authority_tier_count != source_channel_count:
        mismatches.append({
            "component": "source_channel_matrix",
            "rule": "authority_tier_count_equals_source_channel_count",
            "expected": source_channel_count,
            "actual": authority_tier_count,
        })

    jurisdiction_family_count = source_matrix.get("jurisdiction_family_count")
    expected_anchor_rows = (
        jurisdiction_family_count * 2
        if isinstance(jurisdiction_family_count, int)
        else "two official anchor channels per jurisdiction family"
    )
    matrix_anchor_rows = source_matrix.get("legal_claim_anchor_rows")
    if matrix_anchor_rows != expected_anchor_rows:
        mismatches.append({
            "component": "source_channel_matrix",
            "rule": "legal_claim_anchor_rows_equal_two_per_jurisdiction_family",
            "expected": expected_anchor_rows,
            "actual": matrix_anchor_rows,
        })

    matrix_row_count = source_matrix.get("matrix_row_count")
    matrix_authenticity_rows = source_matrix.get("authenticity_volatility_control_rows")
    if matrix_authenticity_rows != matrix_row_count:
        mismatches.append({
            "component": "source_channel_matrix",
            "rule": "authenticity_volatility_control_rows_match_matrix_rows",
            "expected": matrix_row_count,
            "actual": matrix_authenticity_rows,
        })

    expected_regulatory_queue = None
    regulatory_candidates = project_plan.get("regulatory_candidates_found_count")
    seed_domains = project_plan.get("registered_seed_domain_count")
    if isinstance(regulatory_candidates, int) and isinstance(seed_domains, int):
        expected_regulatory_queue = regulatory_candidates - seed_domains
    readiness_pattern_count = readiness.get("regulatory_pattern_count")
    if isinstance(regulatory_candidates, int) and readiness_pattern_count != regulatory_candidates:
        mismatches.append({
            "component": "readiness_bundle",
            "rule": "regulatory_pattern_count_matches_project_candidates_found",
            "expected": regulatory_candidates,
            "actual": readiness_pattern_count,
        })
    readiness_candidate_count = readiness.get("regulatory_candidate_count")
    if expected_regulatory_queue is not None and readiness_candidate_count != expected_regulatory_queue:
        mismatches.append({
            "component": "readiness_bundle",
            "rule": "regulatory_candidate_count_excludes_active_seed_domains",
            "expected": expected_regulatory_queue,
            "actual": readiness_candidate_count,
        })
    if readiness.get("regulatory_seed_scaffold_operations") != 0:
        mismatches.append({
            "component": "readiness_bundle",
            "rule": "regulatory_seed_scaffold_operations_remain_zero",
            "expected": 0,
            "actual": readiness.get("regulatory_seed_scaffold_operations"),
        })
    for component_name, component in (
        ("next_actions", next_actions),
        ("curator_sprint", curator_sprint),
    ):
        actual = component.get("regulatory_priority_queue_items")
        if expected_regulatory_queue is not None and actual != expected_regulatory_queue:
            mismatches.append({
                "component": component_name,
                "rule": "regulatory_priority_queue_items_equal_candidate_count",
                "expected": expected_regulatory_queue,
                "actual": actual,
            })
    next_top = next_actions.get("regulatory_top_candidate_id")
    sprint_top = curator_sprint.get("regulatory_top_candidate_id")
    if not next_top or next_top != sprint_top:
        mismatches.append({
            "component": "next_actions/curator_sprint",
            "rule": "regulatory_top_candidate_ids_match_and_are_present",
            "expected": next_top or "nonempty_top_candidate",
            "actual": sprint_top,
        })
    next_phase_count = next_actions.get("execution_phase_count")
    sprint_phase_count = curator_sprint.get("execution_phase_count")
    if next_phase_count != sprint_phase_count:
        mismatches.append({
            "component": "next_actions/curator_sprint",
            "rule": "execution_phase_counts_match",
            "expected": next_phase_count,
            "actual": sprint_phase_count,
        })
    next_action_count = next_actions.get("action_count")
    next_phase_covered = next_actions.get("execution_phase_covered_action_count")
    if next_phase_covered != next_action_count:
        mismatches.append({
            "component": "next_actions",
            "rule": "execution_phase_covered_action_count_matches_action_count",
            "expected": next_action_count,
            "actual": next_phase_covered,
        })
    next_preserving_channels = next_actions.get(
        "actions_preserving_legal_anchor_source_channels"
    )
    if next_preserving_channels != next_action_count:
        mismatches.append({
            "component": "next_actions",
            "rule": "actions_preserving_legal_anchor_source_channels_match_action_count",
            "expected": next_action_count,
            "actual": next_preserving_channels,
        })
    next_phases_preserving_channels = next_actions.get(
        "execution_phases_preserving_legal_anchor_source_channels"
    )
    if next_phases_preserving_channels != next_phase_count:
        mismatches.append({
            "component": "next_actions",
            "rule": (
                "execution_phases_preserving_legal_anchor_source_channels_match_phase_count"
            ),
            "expected": next_phase_count,
            "actual": next_phases_preserving_channels,
        })
    sprint_phase_covered = curator_sprint.get("execution_phase_covered_action_count")
    sprint_item_count = curator_sprint.get("sprint_item_count")
    blocked_later = curator_sprint.get("blocked_later_items")
    expected_sprint_phase_covered = (
        sprint_item_count + blocked_later
        if isinstance(sprint_item_count, int) and isinstance(blocked_later, int)
        else "sprint_item_count + blocked_later_items"
    )
    if sprint_phase_covered != expected_sprint_phase_covered:
        mismatches.append({
            "component": "curator_sprint",
            "rule": "execution_phase_covered_action_count_matches_sprint_plus_blocked",
            "expected": expected_sprint_phase_covered,
            "actual": sprint_phase_covered,
        })
    sprint_items_preserving_channels = curator_sprint.get(
        "sprint_items_preserving_legal_anchor_source_channels"
    )
    if sprint_items_preserving_channels != sprint_item_count:
        mismatches.append({
            "component": "curator_sprint",
            "rule": "sprint_items_preserving_legal_anchor_source_channels_match_sprint_items",
            "expected": sprint_item_count,
            "actual": sprint_items_preserving_channels,
        })
    sprint_blocked_later_preserving_channels = curator_sprint.get(
        "blocked_later_items_preserving_legal_anchor_source_channels"
    )
    if sprint_blocked_later_preserving_channels != blocked_later:
        mismatches.append({
            "component": "curator_sprint",
            "rule": "blocked_later_items_preserving_legal_anchor_source_channels_match_blocked_items",
            "expected": blocked_later,
            "actual": sprint_blocked_later_preserving_channels,
        })
    sprint_phases_preserving_channels = curator_sprint.get(
        "execution_phases_preserving_legal_anchor_source_channels"
    )
    if sprint_phases_preserving_channels != sprint_phase_count:
        mismatches.append({
            "component": "curator_sprint",
            "rule": (
                "execution_phases_preserving_legal_anchor_source_channels_match_phase_count"
            ),
            "expected": sprint_phase_count,
            "actual": sprint_phases_preserving_channels,
        })
    if next_phase_covered != sprint_phase_covered:
        mismatches.append({
            "component": "next_actions/curator_sprint",
            "rule": "execution_phase_covered_action_counts_match",
            "expected": next_phase_covered,
            "actual": sprint_phase_covered,
        })

    matrix_informal_rows = source_matrix.get("informal_publication_rows")
    matrix_informal_authenticity_rows = source_matrix.get(
        "informal_authenticity_volatility_control_rows"
    )
    if matrix_informal_authenticity_rows != matrix_informal_rows:
        mismatches.append({
            "component": "source_channel_matrix",
            "rule": "informal_authenticity_volatility_rows_match_informal_rows",
            "expected": matrix_informal_rows,
            "actual": matrix_informal_authenticity_rows,
        })

    review_anchor_rows = source_review.get("legal_claim_anchor_rows")
    if review_anchor_rows != matrix_anchor_rows:
        mismatches.append({
            "component": "source_channel_review_packet",
            "rule": "legal_claim_anchor_rows_match_matrix",
            "expected": matrix_anchor_rows,
            "actual": review_anchor_rows,
        })

    review_lead_only_rows = source_review.get("lead_only_claim_rows")
    expected_lead_only_rows = source_review.get("informal_publication_rows")
    if review_lead_only_rows != expected_lead_only_rows:
        mismatches.append({
            "component": "source_channel_review_packet",
            "rule": "lead_only_claim_rows_match_informal_publication_rows",
            "expected": expected_lead_only_rows,
            "actual": review_lead_only_rows,
        })

    review_row_count = source_review.get("review_row_count")
    review_authenticity_rows = source_review.get("authenticity_volatility_review_rows")
    if review_authenticity_rows != review_row_count:
        mismatches.append({
            "component": "source_channel_review_packet",
            "rule": "authenticity_volatility_review_rows_match_review_rows",
            "expected": review_row_count,
            "actual": review_authenticity_rows,
        })

    review_informal_rows = source_review.get("informal_publication_rows")
    review_informal_authenticity_rows = source_review.get(
        "informal_authenticity_volatility_review_rows"
    )
    if review_informal_authenticity_rows != review_informal_rows:
        mismatches.append({
            "component": "source_channel_review_packet",
            "rule": "informal_authenticity_volatility_rows_match_informal_rows",
            "expected": review_informal_rows,
            "actual": review_informal_authenticity_rows,
        })

    task_count = benchmark_blueprint.get("task_blueprint_count")
    for key in (
        "task_source_grounding_contract_count",
        "tasks_requiring_legal_claim_anchor",
        "tasks_requiring_source_gap_marker",
        "tasks_barring_informal_standalone_claims",
        "tasks_requiring_temporal_validity",
        "tasks_requiring_language_access_review",
        "tasks_requiring_entity_resolution_review",
        "tasks_requiring_remedy_forum_review",
        "tasks_requiring_authority_hierarchy_review",
        "tasks_requiring_coverage_scope_review",
        "tasks_requiring_jurisdiction_chain_review",
        "tasks_requiring_implementation_status_review",
        "tasks_requiring_procedural_burden_review",
    ):
        actual = benchmark_blueprint.get(key)
        if actual != task_count:
            mismatches.append({
                "component": "benchmark_blueprint",
                "rule": f"{key}_equals_task_blueprint_count",
                "expected": task_count,
                "actual": actual,
            })
    for key in (
        "task_source_grounding_contract_count",
        "tasks_requiring_legal_claim_anchor",
        "tasks_requiring_source_gap_marker",
        "tasks_barring_informal_standalone_claims",
        "tasks_requiring_temporal_validity",
        "tasks_requiring_language_access_review",
        "tasks_requiring_entity_resolution_review",
        "tasks_requiring_remedy_forum_review",
        "tasks_requiring_authority_hierarchy_review",
        "tasks_requiring_coverage_scope_review",
        "tasks_requiring_jurisdiction_chain_review",
        "tasks_requiring_implementation_status_review",
        "tasks_requiring_procedural_burden_review",
    ):
        actual = eval_contract.get(key)
        if actual != task_count:
            mismatches.append({
                "component": "eval_contract",
                "rule": f"{key}_equals_benchmark_task_blueprint_count",
                "expected": task_count,
                "actual": actual,
            })
    anchor_channel_ids = benchmark_blueprint.get("legal_claim_anchor_source_channel_ids")
    for component, component_summary in (
        ("source_channel_matrix", source_matrix),
        ("source_channel_review_packet", source_review),
        ("eval_contract", eval_contract),
        ("diagnostic_run_plan", diagnostic_run_plan),
        ("judge_calibration_plan", judge_calibration),
        ("transition_gate", transition_gate),
        ("readiness_bundle", readiness),
        ("next_actions", next_actions),
        ("curator_sprint", curator_sprint),
    ):
        if component_summary.get("legal_claim_anchor_source_channel_ids") != anchor_channel_ids:
            mismatches.append({
                "component": component,
                "rule": "legal_claim_anchor_source_channel_ids_match_benchmark_blueprint",
                "expected": anchor_channel_ids,
                "actual": component_summary.get("legal_claim_anchor_source_channel_ids"),
            })
        if component_summary.get("legal_claim_anchor_source_channel_count") != len(anchor_channel_ids or []):
            mismatches.append({
                "component": component,
                "rule": "legal_claim_anchor_source_channel_count_matches_benchmark_blueprint",
                "expected": len(anchor_channel_ids or []),
                "actual": component_summary.get("legal_claim_anchor_source_channel_count"),
            })
    if eval_contract.get("model_response_record_field_count", 0) < 32:
        mismatches.append({
            "component": "eval_contract",
            "rule": "model_response_schema_tracks_source_grounding",
            "expected": (
                "at least 32 fields including legal-anchor object IDs, legal-anchor source-channel IDs, source-grounding status, "
                "temporal-validity status, current-law basis, language/translation review status, "
                "entity-resolution status, remedy/forum competence status, authority hierarchy status, "
                "coverage-scope status, jurisdiction-chain status, implementation-access status, "
                "and procedural-burden status"
            ),
            "actual": eval_contract.get("model_response_record_field_count"),
        })
    if eval_contract.get("judge_output_field_count", 0) < 22:
        mismatches.append({
            "component": "eval_contract",
            "rule": "judge_output_schema_tracks_source_grounding",
            "expected": (
                "at least 22 fields including source-grounding, temporal-validity, "
                "language-access, entity-resolution, forum-competence, authority-hierarchy, "
                "coverage-scope, jurisdiction-chain, implementation-access, procedural-burden, "
                "and remedy-routing findings"
            ),
            "actual": eval_contract.get("judge_output_field_count"),
        })
    source_grounding_failure_modes = judge_calibration.get("source_grounding_failure_mode_count")
    source_grounding_cases = judge_calibration.get("source_grounding_calibration_cases")
    if source_grounding_cases != source_grounding_failure_modes:
        mismatches.append({
            "component": "judge_calibration_plan",
            "rule": "source_grounding_cases_cover_source_grounding_failure_modes",
            "expected": source_grounding_failure_modes,
            "actual": source_grounding_cases,
        })
    calibration_case_count = judge_calibration.get("calibration_case_count")
    for key in (
        "cases_requiring_source_grounding_findings",
        "cases_requiring_legal_anchor_or_gap",
        "cases_requiring_legal_anchor_source_channels",
        "cases_requiring_temporal_validity_fields",
        "cases_requiring_temporal_validity_findings",
        "cases_requiring_language_access_fields",
        "cases_requiring_language_access_findings",
        "cases_requiring_entity_resolution_fields",
        "cases_requiring_entity_resolution_findings",
        "cases_requiring_remedy_forum_fields",
        "cases_requiring_remedy_forum_findings",
        "cases_requiring_authority_hierarchy_fields",
        "cases_requiring_authority_hierarchy_findings",
        "cases_requiring_coverage_scope_fields",
        "cases_requiring_coverage_scope_findings",
        "cases_requiring_jurisdiction_chain_fields",
        "cases_requiring_jurisdiction_chain_findings",
        "cases_requiring_implementation_access_fields",
        "cases_requiring_implementation_access_findings",
        "cases_requiring_procedural_burden_fields",
        "cases_requiring_procedural_burden_findings",
    ):
        actual = judge_calibration.get(key)
        if actual != calibration_case_count:
            mismatches.append({
                "component": "judge_calibration_plan",
                "rule": f"{key}_equals_calibration_case_count",
                "expected": calibration_case_count,
                "actual": actual,
            })
    if transition_gate.get("source_grounding_transition_count") != 4:
        mismatches.append({
            "component": "transition_gate",
            "rule": "source_grounding_transition_count_equals_required_chain_steps",
            "expected": 4,
            "actual": transition_gate.get("source_grounding_transition_count"),
        })
    if transition_gate.get("temporal_validity_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "temporal_validity_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("temporal_validity_transition_count"),
        })
    if transition_gate.get("language_access_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "language_access_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("language_access_transition_count"),
        })
    if transition_gate.get("entity_resolution_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "entity_resolution_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("entity_resolution_transition_count"),
        })
    if transition_gate.get("remedy_forum_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "remedy_forum_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("remedy_forum_transition_count"),
        })
    if transition_gate.get("authority_hierarchy_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "authority_hierarchy_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("authority_hierarchy_transition_count"),
        })
    if transition_gate.get("coverage_scope_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "coverage_scope_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("coverage_scope_transition_count"),
        })
    if transition_gate.get("jurisdiction_chain_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "jurisdiction_chain_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("jurisdiction_chain_transition_count"),
        })
    if transition_gate.get("implementation_access_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "implementation_access_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("implementation_access_transition_count"),
        })
    if transition_gate.get("procedural_burden_transition_count") != 5:
        mismatches.append({
            "component": "transition_gate",
            "rule": "procedural_burden_transition_count_equals_required_chain_steps",
            "expected": 5,
            "actual": transition_gate.get("procedural_burden_transition_count"),
        })
    if (
        transition_gate.get("transitions_preserving_legal_anchor_source_channels")
        != transition_gate.get("transition_count")
    ):
        mismatches.append({
            "component": "transition_gate",
            "rule": "transitions_preserving_legal_anchor_source_channels_match_transition_count",
            "expected": transition_gate.get("transition_count"),
            "actual": transition_gate.get(
                "transitions_preserving_legal_anchor_source_channels"
            ),
        })
    return mismatches


def _component_ready_flag_findings(components: Any) -> list[dict[str, Any]]:
    if not isinstance(components, dict):
        return [{"component": "$", "flag": "component_summaries", "actual": "not_object"}]
    findings: list[dict[str, Any]] = []
    for component, summary in sorted(components.items()):
        if not isinstance(summary, dict):
            findings.append({
                "component": str(component),
                "flag": "$",
                "actual": "summary_not_object",
            })
            continue
        for key, value in sorted(summary.items()):
            if key.startswith("ready_for_") and value is not False:
                findings.append({
                    "component": str(component),
                    "flag": str(key),
                    "actual": value,
                })
    return findings


def _component_consistency_findings(components: Any) -> list[dict[str, Any]]:
    if not isinstance(components, dict):
        return [{"component": "$", "flag": "component_summaries", "actual": "not_object"}]
    findings: list[dict[str, Any]] = []
    for component in sorted(COMPONENTS_WITH_CONSISTENCY):
        summary = components.get(component)
        actual = summary.get("consistency_ok") if isinstance(summary, dict) else "component_missing"
        if actual is not True:
            findings.append({
                "component": component,
                "flag": "consistency_ok",
                "expected": True,
                "actual": actual,
            })
    return findings


def _component_blocking_mismatches(components: Any) -> list[dict[str, Any]]:
    if not isinstance(components, dict):
        return [{"component": "$", "actual": "component_summaries_not_object"}]
    mismatches: list[dict[str, Any]] = []
    for component, blocked_key, total_key in COMPONENT_BLOCKING_RULES:
        summary = components.get(component)
        if not isinstance(summary, dict):
            mismatches.append({
                "component": component,
                "rule": f"{blocked_key}_equals_{total_key}",
                "expected": "component_summary_object",
                "actual": "missing_or_not_object",
            })
            continue
        expected = summary.get(total_key)
        actual = summary.get(blocked_key)
        if actual != expected:
            mismatches.append({
                "component": component,
                "rule": f"{blocked_key}_equals_{total_key}",
                "expected": expected,
                "actual": actual,
            })
    for component, key, expected in COMPONENT_ZERO_RULES:
        summary = components.get(component)
        actual = summary.get(key) if isinstance(summary, dict) else "missing_or_not_object"
        if actual != expected:
            mismatches.append({
                "component": component,
                "rule": f"{key}_equals_{expected}",
                "expected": expected,
                "actual": actual,
            })
    source_matrix = components.get("source_channel_matrix")
    if isinstance(source_matrix, dict):
        expected = source_matrix.get("informal_publication_rows")
        actual = source_matrix.get("lead_only_rows")
        if actual != expected:
            mismatches.append({
                "component": "source_channel_matrix",
                "rule": "lead_only_rows_equals_informal_publication_rows",
                "expected": expected,
                "actual": actual,
            })
    next_actions = components.get("next_actions")
    sprint = components.get("curator_sprint")
    if isinstance(next_actions, dict) and isinstance(sprint, dict):
        expected = next_actions.get("blocked_action_count")
        actual = sprint.get("blocked_later_items")
        if actual != expected:
            mismatches.append({
                "component": "next_actions/curator_sprint",
                "rule": "blocked_later_counts_match",
                "expected": expected,
                "actual": actual,
            })
    return mismatches


def _contains_disallowed_text(doc: Any) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def _build_expected_doc(
    *,
    domain_id: str,
    project_config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
    component_dir: pathlib.Path | None,
) -> dict[str, Any] | None:
    try:
        chain = curation_builder.build_global_protections_chain(
            domain_id=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
        return curation_builder.build_curation_bundle(
            chain=chain,
            domain_id=domain_id,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
    except Exception:
        return None


def validate_curation_bundle(
    doc: Any,
    *,
    bundle_path: pathlib.Path = DEFAULT_BUNDLE,
    expected_domain: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
    compare_current_chain: bool = True,
) -> dict[str, Any]:
    """Return a read-only validation report for a saved curation bundle."""
    is_object = isinstance(doc, dict)
    obj = doc if is_object else {}
    meta = obj.get("_meta") if isinstance(obj.get("_meta"), dict) else {}
    summary = obj.get("summary") if isinstance(obj.get("summary"), dict) else {}
    components = obj.get("component_summaries") if isinstance(obj.get("component_summaries"), dict) else {}
    artifact_paths = obj.get("artifact_paths") if isinstance(obj.get("artifact_paths"), dict) else {}
    bundle_checks = obj.get("checks") if isinstance(obj.get("checks"), list) else []
    ready_flags = {key: summary.get(key) for key in READY_FLAG_KEYS}
    component_ready_findings = _component_ready_flag_findings(components)
    component_consistency_findings = _component_consistency_findings(components)
    component_blocking_mismatches = _component_blocking_mismatches(components)
    component_provenance_mismatches = _component_provenance_mismatches(components)
    expected_doc = (
        _build_expected_doc(
            domain_id=expected_domain,
            project_config_path=project_config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
        if compare_current_chain
        else None
    )

    checks = [
        _check("bundle_is_object", is_object, expected=True, actual=is_object),
        _check(
            "schema_version_matches",
            meta.get("schema_version") == "global_protections_curation_bundle.v1",
            expected="global_protections_curation_bundle.v1",
            actual=meta.get("schema_version"),
        ),
        _check(
            "domain_matches_expected",
            meta.get("domain") == expected_domain and artifact_paths.get("domain") == expected_domain,
            expected=expected_domain,
            actual={"meta": meta.get("domain"), "artifact_paths": artifact_paths.get("domain")},
        ),
        _check(
            "required_top_level_sections_present",
            REQUIRED_TOP_LEVEL.issubset(set(obj)),
            expected=sorted(REQUIRED_TOP_LEVEL),
            actual=sorted(set(obj) & REQUIRED_TOP_LEVEL),
        ),
        _check(
            "required_components_present",
            REQUIRED_COMPONENTS.issubset(set(components)),
            expected=sorted(REQUIRED_COMPONENTS),
            actual=sorted(set(components) & REQUIRED_COMPONENTS),
        ),
        _check(
            "raw_payload_sections_absent",
            not (set(obj) & RAW_PAYLOAD_KEYS),
            expected=[],
            actual=sorted(set(obj) & RAW_PAYLOAD_KEYS),
        ),
        _check(
            "summary_consistency_ok_true",
            summary.get("consistency_ok") is True,
            expected=True,
            actual=summary.get("consistency_ok"),
        ),
        _check(
            "all_bundle_checks_ok",
            bool(bundle_checks) and all(
                isinstance(check, dict) and check.get("ok") is True for check in bundle_checks
            ),
            expected=True,
            actual=[
                check.get("id")
                for check in bundle_checks
                if not isinstance(check, dict) or check.get("ok") is not True
            ],
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            ready_flags and all(value is False for value in ready_flags.values()),
            expected={key: False for key in READY_FLAG_KEYS},
            actual=ready_flags,
        ),
    ]
    count_mismatches = _count_mismatches(obj)
    unsafe_artifact_paths = _unsafe_artifact_paths(artifact_paths)
    missing_artifact_keys = sorted(REQUIRED_ARTIFACT_KEYS - set(artifact_paths))
    disallowed_terms = _contains_disallowed_text(obj)
    privacy_scan = project_plan_builder._scan_privacy(obj)
    checks.extend([
        _check(
            "summary_counts_match_component_summaries",
            not count_mismatches,
            expected=[],
            actual=count_mismatches,
        ),
        _check(
            "component_readiness_flags_blocked",
            not component_ready_findings,
            expected=[],
            actual=component_ready_findings,
        ),
        _check(
            "component_consistency_flags_ok",
            not component_consistency_findings,
            expected=[],
            actual=component_consistency_findings,
        ),
        _check(
            "component_blocking_counts_match",
            not component_blocking_mismatches,
            expected=[],
            actual=component_blocking_mismatches,
        ),
        _check(
            "component_provenance_counts_match",
            not component_provenance_mismatches,
            expected=[],
            actual=component_provenance_mismatches,
        ),
        _check(
            "artifact_path_set_complete",
            not missing_artifact_keys,
            expected=[],
            actual=missing_artifact_keys,
        ),
        _check(
            "artifact_paths_are_repo_relative_or_external",
            not unsafe_artifact_paths,
            expected=[],
            actual=unsafe_artifact_paths,
        ),
        _check(
            "bundle_contains_no_disallowed_text",
            not disallowed_terms,
            expected=[],
            actual=disallowed_terms,
        ),
        _check(
            "privacy_scan_ok",
            privacy_scan.get("ok") is True,
            expected=True,
            actual=privacy_scan.get("ok"),
        ),
    ])
    if compare_current_chain:
        checks.extend([
            _check(
                "current_chain_rebuild_available",
                expected_doc is not None,
                expected=True,
                actual=expected_doc is not None,
            ),
            _check(
                "summary_matches_current_chain",
                expected_doc is not None and summary == expected_doc.get("summary"),
                expected=(expected_doc or {}).get("summary"),
                actual=summary,
            ),
            _check(
                "component_summaries_match_current_chain",
                expected_doc is not None and components == expected_doc.get("component_summaries"),
                expected=(expected_doc or {}).get("component_summaries"),
                actual=components,
            ),
        ])

    failed = _failed_ids(checks)
    return {
        "_meta": {
            "schema_version": "global_protections_curation_bundle_validation.v1",
            "bundle_path": _display_path(bundle_path),
            "domain": expected_domain,
            "status": (
                "read-only curation-bundle validation; not legal advice, not source "
                "verification, and not comparable benchmark evidence"
            ),
        },
        "summary": {
            "valid": not failed,
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "failed_check_ids": failed,
            "domain": expected_domain,
            "next_execution_phase_count": summary.get("next_execution_phase_count"),
            "jurisdiction_pack_scope_ids": summary.get("jurisdiction_pack_scope_ids"),
            "jurisdiction_pack_domain_lens_ids": summary.get(
                "jurisdiction_pack_domain_lens_ids"
            ),
            "next_execution_phase_covered_actions": summary.get(
                "next_execution_phase_covered_actions"
            ),
            "readiness_legal_claim_anchor_source_channel_count": summary.get(
                "readiness_legal_claim_anchor_source_channel_count"
            ),
            "readiness_legal_claim_anchor_source_channel_ids": summary.get(
                "readiness_legal_claim_anchor_source_channel_ids"
            ),
            "worker_verified_local_law_rows": summary.get("worker_verified_local_law_rows"),
            "worker_source_object_tasks": summary.get("worker_source_object_tasks"),
            "worker_scope_refinement_tasks": summary.get("worker_scope_refinement_tasks"),
            "regulatory_pattern_count": summary.get("regulatory_pattern_count"),
            "regulatory_candidate_count": summary.get("regulatory_candidate_count"),
            "regulatory_seed_scaffold_operations": summary.get(
                "regulatory_seed_scaffold_operations"
            ),
            "source_channel_legal_claim_anchor_source_channel_count": summary.get(
                "source_channel_legal_claim_anchor_source_channel_count"
            ),
            "source_channel_legal_claim_anchor_source_channel_ids": summary.get(
                "source_channel_legal_claim_anchor_source_channel_ids"
            ),
            "source_channel_review_legal_claim_anchor_source_channel_count": summary.get(
                "source_channel_review_legal_claim_anchor_source_channel_count"
            ),
            "source_channel_review_legal_claim_anchor_source_channel_ids": summary.get(
                "source_channel_review_legal_claim_anchor_source_channel_ids"
            ),
            "next_actions_legal_claim_anchor_source_channel_count": summary.get(
                "next_actions_legal_claim_anchor_source_channel_count"
            ),
            "next_actions_legal_claim_anchor_source_channel_ids": summary.get(
                "next_actions_legal_claim_anchor_source_channel_ids"
            ),
            "next_actions_preserving_legal_anchor_source_channels": summary.get(
                "next_actions_preserving_legal_anchor_source_channels"
            ),
            "next_execution_phases_preserving_legal_anchor_source_channels": summary.get(
                "next_execution_phases_preserving_legal_anchor_source_channels"
            ),
            "curator_execution_phase_count": summary.get("curator_execution_phase_count"),
            "curator_execution_phase_covered_actions": summary.get(
                "curator_execution_phase_covered_actions"
            ),
            "curator_sprint_legal_claim_anchor_source_channel_count": summary.get(
                "curator_sprint_legal_claim_anchor_source_channel_count"
            ),
            "curator_sprint_legal_claim_anchor_source_channel_ids": summary.get(
                "curator_sprint_legal_claim_anchor_source_channel_ids"
            ),
            "curator_sprint_items_preserving_legal_anchor_source_channels": summary.get(
                "curator_sprint_items_preserving_legal_anchor_source_channels"
            ),
            "curator_blocked_later_items_preserving_legal_anchor_source_channels": summary.get(
                "curator_blocked_later_items_preserving_legal_anchor_source_channels"
            ),
            "curator_execution_phases_preserving_legal_anchor_source_channels": summary.get(
                "curator_execution_phases_preserving_legal_anchor_source_channels"
            ),
            "ready_for_comparable_scoring": summary.get("ready_for_comparable_scoring"),
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bundle", nargs="?", type=pathlib.Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=curation_builder.OUT_DIR)
    ap.add_argument(
        "--skip-current-chain",
        action="store_true",
        help="validate the artifact shape and safety gates without rebuilding the current chain",
    )
    ap.add_argument("--json", action="store_true", help="print the full validation report as JSON")
    args = ap.parse_args(argv)

    doc = _load_json(args.bundle)
    report = validate_curation_bundle(
        doc,
        bundle_path=args.bundle,
        expected_domain=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
        compare_current_chain=not args.skip_current_chain,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        summary = report["summary"]
        print(
            "[global-protections-curation-bundle-validation] "
            f"valid={str(bool(summary['valid'])).lower()}; "
            f"failed={summary['failed_check_count']}/{summary['check_count']}; "
            f"phase_coverage=next:{summary['next_execution_phase_count']}/"
            f"{summary['next_execution_phase_covered_actions']},"
            f"curator:{summary['curator_execution_phase_count']}/"
            f"{summary['curator_execution_phase_covered_actions']}; "
            f"domain={summary['domain']}; "
            f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.bundle}"
        )
        if summary["failed_check_ids"]:
            print("failed_check_ids=" + ",".join(summary["failed_check_ids"]))
    return 0 if report["summary"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
