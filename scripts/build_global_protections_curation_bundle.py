#!/usr/bin/env python3
"""Build the top-level curation bundle for the global protections sister project.

This command composes the full non-mutating project stack:

1. project plan
2. jurisdiction-pack matrix
3. source-channel matrix
4. source-channel review packet
5. benchmark blueprint
6. evaluation contract
7. diagnostic run plan
8. judge-calibration plan
9. transition gate
10. readiness bundle
11. next-actions backlog
12. curator sprint packet

It emits one compact status artifact for project planning and curator handoff
tracking. It does not fetch sources, verify law, create prompts, edit manifests,
create domain files, train models, or authorize comparable scoring.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from artifact_path_policy import handoff_artifact_path  # noqa: E402
import build_global_protections_curator_sprint as curator_sprint_builder  # noqa: E402
import build_global_protections_benchmark_blueprint as benchmark_blueprint_builder  # noqa: E402
import build_global_protections_diagnostic_run_plan as diagnostic_run_builder  # noqa: E402
import build_global_protections_eval_contract as eval_contract_builder  # noqa: E402
import build_global_protections_judge_calibration_plan as judge_calibration_builder  # noqa: E402
import build_global_protections_jurisdiction_pack_matrix as jurisdiction_pack_builder  # noqa: E402
import build_global_protections_next_actions as next_actions_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_channel_builder  # noqa: E402
import build_global_protections_source_channel_review_packet as source_review_builder  # noqa: E402
import build_global_protections_transition_gate as transition_gate_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_curation_bundle.json"
MD_OUT = OUT_DIR / "global_protections_curation_bundle.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

_DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "https://",
    "www.",
]


def _artifact_path(path: pathlib.Path) -> str:
    return handoff_artifact_path(path, root=_ROOT)


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _check(check_id: str, ok: bool, *, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": bool(ok),
        "expected": expected,
        "actual": actual,
    }


def component_paths(
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
) -> dict[str, str]:
    """Return default artifact paths for the top-level global protections chain."""
    base = output_dir or OUT_DIR
    stems = {
        "global_protections_project_plan": "global_protections_project_plan",
        "global_protections_jurisdiction_pack_matrix": "global_protections_jurisdiction_pack_matrix",
        "global_protections_source_channel_matrix": "global_protections_source_channel_matrix",
        "global_protections_source_channel_review_packet": "global_protections_source_channel_review_packet",
        "global_protections_benchmark_blueprint": "global_protections_benchmark_blueprint",
        "global_protections_eval_contract": "global_protections_eval_contract",
        "global_protections_diagnostic_run_plan": "global_protections_diagnostic_run_plan",
        "global_protections_judge_calibration_plan": "global_protections_judge_calibration_plan",
        "global_protections_transition_gate": "global_protections_transition_gate",
        "global_protections_readiness_bundle": "global_protections_readiness_bundle",
        "global_protections_next_actions": "global_protections_next_actions",
        "global_protections_curator_sprint": "global_protections_curator_sprint",
        "global_protections_curation_bundle": "global_protections_curation_bundle",
    }
    paths: dict[str, str] = {}
    for key, stem in stems.items():
        paths[f"{key}_json"] = _artifact_path(base / f"{stem}.json")
        paths[f"{key}_markdown"] = _artifact_path(base / f"{stem}.md")
    paths["domain"] = domain_id
    return paths


def build_global_protections_chain(
    *,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the composed global protections curation chain in memory."""
    readiness_chain = readiness_builder.build_readiness_chain(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    readiness_doc = readiness_builder.build_readiness_bundle(
        chain=readiness_chain,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    source_channel_doc = source_channel_builder.build_source_channel_matrix(
        project_doc=readiness_chain["project_plan"],
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    jurisdiction_pack_doc = jurisdiction_pack_builder.build_jurisdiction_pack_matrix(
        project_doc=readiness_chain["project_plan"],
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    source_review_doc = source_review_builder.build_source_channel_review_packet(
        matrix_doc=source_channel_doc,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
    benchmark_blueprint_doc = benchmark_blueprint_builder.build_benchmark_blueprint(
        project_doc=readiness_chain["project_plan"],
        source_review_doc=source_review_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    eval_contract_doc = eval_contract_builder.build_eval_contract(
        blueprint_doc=benchmark_blueprint_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    diagnostic_run_doc = diagnostic_run_builder.build_diagnostic_run_plan(
        blueprint_doc=benchmark_blueprint_doc,
        eval_contract_doc=eval_contract_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    judge_calibration_doc = judge_calibration_builder.build_judge_calibration_plan(
        eval_contract_doc=eval_contract_doc,
        diagnostic_doc=diagnostic_run_doc,
        domain_id=domain_id,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    transition_gate_doc = transition_gate_builder.build_transition_gate(
        source_review_doc=source_review_doc,
        blueprint_doc=benchmark_blueprint_doc,
        eval_contract_doc=eval_contract_doc,
        diagnostic_doc=diagnostic_run_doc,
        calibration_doc=judge_calibration_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    next_actions_doc = next_actions_builder.build_next_actions(
        chain=readiness_chain,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    curator_sprint_doc = curator_sprint_builder.build_curator_sprint(
        chain=readiness_chain,
        next_actions_doc=next_actions_doc,
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    return {
        "project_plan": readiness_chain["project_plan"],
        "jurisdiction_pack_matrix": jurisdiction_pack_doc,
        "source_channel_matrix": source_channel_doc,
        "source_channel_review_packet": source_review_doc,
        "benchmark_blueprint": benchmark_blueprint_doc,
        "eval_contract": eval_contract_doc,
        "diagnostic_run_plan": diagnostic_run_doc,
        "judge_calibration_plan": judge_calibration_doc,
        "transition_gate": transition_gate_doc,
        "readiness_bundle": readiness_doc,
        "next_actions": next_actions_doc,
        "curator_sprint": curator_sprint_doc,
        "_readiness_chain": readiness_chain,
    }


def _component_summaries(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    project_summary = chain["project_plan"]["summary"]
    jurisdiction_pack_summary = chain["jurisdiction_pack_matrix"]["summary"]
    source_summary = chain["source_channel_matrix"]["summary"]
    source_review_summary = chain["source_channel_review_packet"]["summary"]
    benchmark_summary = chain["benchmark_blueprint"]["summary"]
    eval_contract_summary = chain["eval_contract"]["summary"]
    diagnostic_summary = chain["diagnostic_run_plan"]["summary"]
    judge_calibration_summary = chain["judge_calibration_plan"]["summary"]
    transition_summary = chain["transition_gate"]["summary"]
    readiness_summary = chain["readiness_bundle"]["summary"]
    next_summary = chain["next_actions"]["summary"]
    sprint_summary = chain["curator_sprint"]["summary"]
    next_phase_covered_actions = sum(
        len(phase.get("action_ids") or [])
        for phase in chain["next_actions"].get("execution_phases", [])
        if isinstance(phase, dict)
    )
    sprint_phase_covered_actions = sum(
        len(phase.get("sprint_action_ids") or [])
        + len(phase.get("blocked_later_action_ids") or [])
        for phase in chain["curator_sprint"].get("execution_phase_summary", [])
        if isinstance(phase, dict)
    )
    return {
        "project_plan": {
            "safe_for_project_planning": project_summary["safe_for_project_planning"],
            "registered_seed_domain_count": project_summary["registered_seed_domain_count"],
            "regulatory_candidates_found_count": project_summary[
                "regulatory_candidates_found_count"
            ],
            "ready_for_comparable_scoring": project_summary["ready_for_comparable_scoring"],
        },
        "jurisdiction_pack_matrix": {
            "consistency_ok": jurisdiction_pack_summary["consistency_ok"],
            "safe_for_pack_planning": jurisdiction_pack_summary["safe_for_pack_planning"],
            "jurisdiction_scope_count": jurisdiction_pack_summary["jurisdiction_scope_count"],
            "jurisdiction_scope_ids": list(
                jurisdiction_pack_summary["jurisdiction_scope_ids"]
            ),
            "domain_lens_count": jurisdiction_pack_summary["domain_lens_count"],
            "domain_lens_ids": list(jurisdiction_pack_summary["domain_lens_ids"]),
            "pack_cell_count": jurisdiction_pack_summary["pack_cell_count"],
            "source_object_slot_count": jurisdiction_pack_summary["source_object_slot_count"],
            "not_started_source_object_slots": jurisdiction_pack_summary[
                "not_started_source_object_slots"
            ],
            "language_review_required_cells": jurisdiction_pack_summary[
                "language_review_required_cells"
            ],
            "scope_resolution_required_cells": jurisdiction_pack_summary[
                "scope_resolution_required_cells"
            ],
            "ready_for_comparable_scoring": jurisdiction_pack_summary[
                "ready_for_comparable_scoring"
            ],
        },
        "source_channel_matrix": {
            "consistency_ok": source_summary["consistency_ok"],
            "jurisdiction_family_count": source_summary["jurisdiction_family_count"],
            "source_channel_count": source_summary["source_channel_count"],
            "authority_tier_count": source_summary["authority_tier_count"],
            "matrix_row_count": source_summary["matrix_row_count"],
            "informal_publication_rows": source_summary["informal_publication_rows"],
            "lead_only_rows": source_summary["lead_only_rows"],
            "legal_claim_anchor_rows": source_summary["legal_claim_anchor_rows"],
            "legal_claim_anchor_source_channel_count": source_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                source_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "authenticity_volatility_control_rows": source_summary[
                "authenticity_volatility_control_rows"
            ],
            "informal_authenticity_volatility_control_rows": source_summary[
                "informal_authenticity_volatility_control_rows"
            ],
            "ready_for_manifest_promotion": source_summary["ready_for_manifest_promotion"],
            "ready_for_comparable_scoring": source_summary["ready_for_comparable_scoring"],
        },
        "source_channel_review_packet": {
            "consistency_ok": source_review_summary["consistency_ok"],
            "review_row_count": source_review_summary["review_row_count"],
            "not_started_rows": source_review_summary["not_started_rows"],
            "informal_publication_rows": source_review_summary["informal_publication_rows"],
            "legal_claim_anchor_rows": source_review_summary["legal_claim_anchor_rows"],
            "legal_claim_anchor_source_channel_count": source_review_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                source_review_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "lead_only_claim_rows": source_review_summary["lead_only_claim_rows"],
            "authenticity_volatility_review_rows": source_review_summary[
                "authenticity_volatility_review_rows"
            ],
            "informal_authenticity_volatility_review_rows": source_review_summary[
                "informal_authenticity_volatility_review_rows"
            ],
            "rows_ready_for_manifest_promotion": source_review_summary[
                "rows_ready_for_manifest_promotion"
            ],
            "ready_for_manifest_promotion": source_review_summary["ready_for_manifest_promotion"],
            "ready_for_comparable_scoring": source_review_summary["ready_for_comparable_scoring"],
        },
        "benchmark_blueprint": {
            "consistency_ok": benchmark_summary["consistency_ok"],
            "task_blueprint_count": benchmark_summary["task_blueprint_count"],
            "blocked_task_blueprints": benchmark_summary["blocked_task_blueprints"],
            "scoring_dimension_count": benchmark_summary["scoring_dimension_count"],
            "abstention_rule_count": benchmark_summary["abstention_rule_count"],
            "task_source_grounding_contract_count": benchmark_summary[
                "task_source_grounding_contract_count"
            ],
            "tasks_requiring_legal_claim_anchor": benchmark_summary[
                "tasks_requiring_legal_claim_anchor"
            ],
            "legal_claim_anchor_source_channel_count": benchmark_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                benchmark_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "tasks_requiring_source_gap_marker": benchmark_summary[
                "tasks_requiring_source_gap_marker"
            ],
            "tasks_barring_informal_standalone_claims": benchmark_summary[
                "tasks_barring_informal_standalone_claims"
            ],
            "tasks_requiring_temporal_validity": benchmark_summary[
                "tasks_requiring_temporal_validity"
            ],
            "tasks_requiring_language_access_review": benchmark_summary[
                "tasks_requiring_language_access_review"
            ],
            "tasks_requiring_entity_resolution_review": benchmark_summary[
                "tasks_requiring_entity_resolution_review"
            ],
            "tasks_requiring_remedy_forum_review": benchmark_summary[
                "tasks_requiring_remedy_forum_review"
            ],
            "tasks_requiring_authority_hierarchy_review": benchmark_summary[
                "tasks_requiring_authority_hierarchy_review"
            ],
            "tasks_requiring_coverage_scope_review": benchmark_summary[
                "tasks_requiring_coverage_scope_review"
            ],
            "tasks_requiring_jurisdiction_chain_review": benchmark_summary[
                "tasks_requiring_jurisdiction_chain_review"
            ],
            "tasks_requiring_implementation_status_review": benchmark_summary[
                "tasks_requiring_implementation_status_review"
            ],
            "tasks_requiring_procedural_burden_review": benchmark_summary[
                "tasks_requiring_procedural_burden_review"
            ],
            "ready_for_comparable_scoring": benchmark_summary["ready_for_comparable_scoring"],
        },
        "eval_contract": {
            "consistency_ok": eval_contract_summary["consistency_ok"],
            "task_source_grounding_contract_count": eval_contract_summary[
                "task_source_grounding_contract_count"
            ],
            "tasks_requiring_legal_claim_anchor": eval_contract_summary[
                "tasks_requiring_legal_claim_anchor"
            ],
            "legal_claim_anchor_source_channel_count": eval_contract_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                eval_contract_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "tasks_requiring_source_gap_marker": eval_contract_summary[
                "tasks_requiring_source_gap_marker"
            ],
            "tasks_barring_informal_standalone_claims": eval_contract_summary[
                "tasks_barring_informal_standalone_claims"
            ],
            "tasks_requiring_temporal_validity": eval_contract_summary[
                "tasks_requiring_temporal_validity"
            ],
            "tasks_requiring_language_access_review": eval_contract_summary[
                "tasks_requiring_language_access_review"
            ],
            "tasks_requiring_entity_resolution_review": eval_contract_summary[
                "tasks_requiring_entity_resolution_review"
            ],
            "tasks_requiring_remedy_forum_review": eval_contract_summary[
                "tasks_requiring_remedy_forum_review"
            ],
            "tasks_requiring_authority_hierarchy_review": eval_contract_summary[
                "tasks_requiring_authority_hierarchy_review"
            ],
            "tasks_requiring_coverage_scope_review": eval_contract_summary[
                "tasks_requiring_coverage_scope_review"
            ],
            "tasks_requiring_jurisdiction_chain_review": eval_contract_summary[
                "tasks_requiring_jurisdiction_chain_review"
            ],
            "tasks_requiring_implementation_status_review": eval_contract_summary[
                "tasks_requiring_implementation_status_review"
            ],
            "tasks_requiring_procedural_burden_review": eval_contract_summary[
                "tasks_requiring_procedural_burden_review"
            ],
            "judge_dimension_contract_count": eval_contract_summary["judge_dimension_contract_count"],
            "failure_mode_count": eval_contract_summary["failure_mode_count"],
            "run_gate_count": eval_contract_summary["run_gate_count"],
            "model_response_record_field_count": eval_contract_summary[
                "model_response_record_field_count"
            ],
            "judge_output_field_count": eval_contract_summary["judge_output_field_count"],
            "ready_for_model_response_capture": eval_contract_summary[
                "ready_for_model_response_capture"
            ],
            "ready_for_judge_calibration": eval_contract_summary["ready_for_judge_calibration"],
            "ready_for_comparable_scoring": eval_contract_summary["ready_for_comparable_scoring"],
        },
        "diagnostic_run_plan": {
            "consistency_ok": diagnostic_summary["consistency_ok"],
            "diagnostic_cell_count": diagnostic_summary["diagnostic_cell_count"],
            "blocked_diagnostic_cells": diagnostic_summary["blocked_diagnostic_cells"],
            "run_gate_count": diagnostic_summary["run_gate_count"],
            "failure_mode_count": diagnostic_summary["failure_mode_count"],
            "legal_claim_anchor_source_channel_count": diagnostic_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                diagnostic_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "ready_for_model_response_capture": diagnostic_summary[
                "ready_for_model_response_capture"
            ],
            "ready_for_judge_calibration": diagnostic_summary["ready_for_judge_calibration"],
            "ready_for_comparable_scoring": diagnostic_summary["ready_for_comparable_scoring"],
        },
        "judge_calibration_plan": {
            "consistency_ok": judge_calibration_summary["consistency_ok"],
            "calibration_case_count": judge_calibration_summary["calibration_case_count"],
            "blocked_calibration_cases": judge_calibration_summary["blocked_calibration_cases"],
            "critical_calibration_cases": judge_calibration_summary["critical_calibration_cases"],
            "source_grounding_failure_mode_count": judge_calibration_summary[
                "source_grounding_failure_mode_count"
            ],
            "source_grounding_calibration_cases": judge_calibration_summary[
                "source_grounding_calibration_cases"
            ],
            "legal_claim_anchor_source_channel_count": judge_calibration_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                judge_calibration_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "cases_requiring_source_grounding_findings": judge_calibration_summary[
                "cases_requiring_source_grounding_findings"
            ],
            "cases_requiring_legal_anchor_or_gap": judge_calibration_summary[
                "cases_requiring_legal_anchor_or_gap"
            ],
            "cases_requiring_legal_anchor_source_channels": judge_calibration_summary[
                "cases_requiring_legal_anchor_source_channels"
            ],
            "cases_requiring_temporal_validity_fields": judge_calibration_summary[
                "cases_requiring_temporal_validity_fields"
            ],
            "cases_requiring_temporal_validity_findings": judge_calibration_summary[
                "cases_requiring_temporal_validity_findings"
            ],
            "cases_requiring_language_access_fields": judge_calibration_summary[
                "cases_requiring_language_access_fields"
            ],
            "cases_requiring_language_access_findings": judge_calibration_summary[
                "cases_requiring_language_access_findings"
            ],
            "cases_requiring_entity_resolution_fields": judge_calibration_summary[
                "cases_requiring_entity_resolution_fields"
            ],
            "cases_requiring_entity_resolution_findings": judge_calibration_summary[
                "cases_requiring_entity_resolution_findings"
            ],
            "cases_requiring_remedy_forum_fields": judge_calibration_summary[
                "cases_requiring_remedy_forum_fields"
            ],
            "cases_requiring_remedy_forum_findings": judge_calibration_summary[
                "cases_requiring_remedy_forum_findings"
            ],
            "cases_requiring_authority_hierarchy_fields": judge_calibration_summary[
                "cases_requiring_authority_hierarchy_fields"
            ],
            "cases_requiring_authority_hierarchy_findings": judge_calibration_summary[
                "cases_requiring_authority_hierarchy_findings"
            ],
            "cases_requiring_coverage_scope_fields": judge_calibration_summary[
                "cases_requiring_coverage_scope_fields"
            ],
            "cases_requiring_coverage_scope_findings": judge_calibration_summary[
                "cases_requiring_coverage_scope_findings"
            ],
            "cases_requiring_jurisdiction_chain_fields": judge_calibration_summary[
                "cases_requiring_jurisdiction_chain_fields"
            ],
            "cases_requiring_jurisdiction_chain_findings": judge_calibration_summary[
                "cases_requiring_jurisdiction_chain_findings"
            ],
            "cases_requiring_implementation_access_fields": judge_calibration_summary[
                "cases_requiring_implementation_access_fields"
            ],
            "cases_requiring_implementation_access_findings": judge_calibration_summary[
                "cases_requiring_implementation_access_findings"
            ],
            "cases_requiring_procedural_burden_fields": judge_calibration_summary[
                "cases_requiring_procedural_burden_fields"
            ],
            "cases_requiring_procedural_burden_findings": judge_calibration_summary[
                "cases_requiring_procedural_burden_findings"
            ],
            "ready_for_judge_calibration": judge_calibration_summary[
                "ready_for_judge_calibration"
            ],
            "ready_for_model_response_capture": judge_calibration_summary[
                "ready_for_model_response_capture"
            ],
            "ready_for_comparable_scoring": judge_calibration_summary["ready_for_comparable_scoring"],
        },
        "transition_gate": {
            "consistency_ok": transition_summary["consistency_ok"],
            "transition_count": transition_summary["transition_count"],
            "blocked_transition_count": transition_summary["blocked_transition_count"],
            "source_grounding_transition_count": transition_summary[
                "source_grounding_transition_count"
            ],
            "temporal_validity_transition_count": transition_summary[
                "temporal_validity_transition_count"
            ],
            "language_access_transition_count": transition_summary[
                "language_access_transition_count"
            ],
            "entity_resolution_transition_count": transition_summary[
                "entity_resolution_transition_count"
            ],
            "remedy_forum_transition_count": transition_summary[
                "remedy_forum_transition_count"
            ],
            "authority_hierarchy_transition_count": transition_summary[
                "authority_hierarchy_transition_count"
            ],
            "coverage_scope_transition_count": transition_summary[
                "coverage_scope_transition_count"
            ],
            "jurisdiction_chain_transition_count": transition_summary[
                "jurisdiction_chain_transition_count"
            ],
            "implementation_access_transition_count": transition_summary[
                "implementation_access_transition_count"
            ],
            "procedural_burden_transition_count": transition_summary[
                "procedural_burden_transition_count"
            ],
            "legal_claim_anchor_source_channel_count": transition_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                transition_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "transitions_preserving_legal_anchor_source_channels": transition_summary[
                "transitions_preserving_legal_anchor_source_channels"
            ],
            "ready_for_manifest_promotion": transition_summary["ready_for_manifest_promotion"],
            "ready_for_model_response_capture": transition_summary[
                "ready_for_model_response_capture"
            ],
            "ready_for_judge_calibration": transition_summary["ready_for_judge_calibration"],
            "ready_for_comparable_scoring": transition_summary["ready_for_comparable_scoring"],
        },
        "readiness_bundle": {
            "consistency_ok": readiness_summary["consistency_ok"],
            "worker_prompt_count": readiness_summary["worker_prompt_count"],
            "worker_prompts_blocked_for_comparable_run": readiness_summary[
                "worker_prompts_blocked_for_comparable_run"
            ],
            "worker_verified_local_law_rows": readiness_summary[
                "worker_verified_local_law_rows"
            ],
            "worker_source_object_tasks": readiness_summary["worker_source_object_tasks"],
            "worker_scope_refinement_tasks": readiness_summary[
                "worker_scope_refinement_tasks"
            ],
            "regulatory_pattern_count": readiness_summary["regulatory_pattern_count"],
            "regulatory_candidate_count": readiness_summary["regulatory_candidate_count"],
            "regulatory_seed_scaffold_operations": readiness_summary[
                "regulatory_seed_scaffold_operations"
            ],
            "ready_for_prompt_generation": readiness_summary["ready_for_prompt_generation"],
            "ready_for_training_use": readiness_summary["ready_for_training_use"],
            "ready_for_public_claims": readiness_summary["ready_for_public_claims"],
            "ready_for_worker_facing_use": readiness_summary["ready_for_worker_facing_use"],
            "legal_claim_anchor_source_channel_count": readiness_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                readiness_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "ready_for_comparable_scoring": readiness_summary["ready_for_comparable_scoring"],
        },
        "next_actions": {
            "consistency_ok": next_summary["consistency_ok"],
            "action_count": next_summary["action_count"],
            "execution_phase_count": next_summary["execution_phase_count"],
            "execution_phase_covered_action_count": next_phase_covered_actions,
            "legal_claim_anchor_source_channel_count": next_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                next_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "actions_preserving_legal_anchor_source_channels": next_summary[
                "actions_preserving_legal_anchor_source_channels"
            ],
            "execution_phases_preserving_legal_anchor_source_channels": next_summary[
                "execution_phases_preserving_legal_anchor_source_channels"
            ],
            "immediate_action_count": next_summary["immediate_action_count"],
            "blocked_action_count": next_summary["blocked_action_count"],
            "regulatory_priority_queue_items": next_summary[
                "regulatory_priority_queue_items"
            ],
            "regulatory_top_candidate_id": next_summary["regulatory_top_candidate_id"],
            "ready_for_comparable_scoring": next_summary["ready_for_comparable_scoring"],
        },
        "curator_sprint": {
            "consistency_ok": sprint_summary["consistency_ok"],
            "sprint_item_count": sprint_summary["sprint_item_count"],
            "execution_phase_count": sprint_summary["execution_phase_count"],
            "execution_phase_covered_action_count": sprint_phase_covered_actions,
            "legal_claim_anchor_source_channel_count": sprint_summary[
                "legal_claim_anchor_source_channel_count"
            ],
            "legal_claim_anchor_source_channel_ids": list(
                sprint_summary["legal_claim_anchor_source_channel_ids"]
            ),
            "sprint_items_preserving_legal_anchor_source_channels": sprint_summary[
                "sprint_items_preserving_legal_anchor_source_channels"
            ],
            "blocked_later_items_preserving_legal_anchor_source_channels": sprint_summary[
                "blocked_later_items_preserving_legal_anchor_source_channels"
            ],
            "execution_phases_preserving_legal_anchor_source_channels": sprint_summary[
                "execution_phases_preserving_legal_anchor_source_channels"
            ],
            "regulatory_priority_queue_items": sprint_summary[
                "regulatory_priority_queue_items"
            ],
            "regulatory_top_candidate_id": sprint_summary["regulatory_top_candidate_id"],
            "blocked_later_items": sprint_summary["blocked_later_items"],
            "ready_for_comparable_scoring": sprint_summary["ready_for_comparable_scoring"],
        },
    }


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in _DISALLOWED_TERMS if term in encoded]


def build_curation_bundle(
    *,
    chain: dict[str, dict[str, Any]] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    project_config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a compact top-level curation bundle for the sister-project stack."""
    chain = chain or build_global_protections_chain(
        domain_id=domain_id,
        project_config_path=project_config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    project_summary = chain["project_plan"]["summary"]
    jurisdiction_pack_summary = chain["jurisdiction_pack_matrix"]["summary"]
    source_summary = chain["source_channel_matrix"]["summary"]
    source_review_summary = chain["source_channel_review_packet"]["summary"]
    benchmark_summary = chain["benchmark_blueprint"]["summary"]
    eval_contract_summary = chain["eval_contract"]["summary"]
    diagnostic_summary = chain["diagnostic_run_plan"]["summary"]
    judge_calibration_summary = chain["judge_calibration_plan"]["summary"]
    transition_summary = chain["transition_gate"]["summary"]
    readiness_summary = chain["readiness_bundle"]["summary"]
    next_summary = chain["next_actions"]["summary"]
    sprint_summary = chain["curator_sprint"]["summary"]
    next_phase_covered_actions = sum(
        len(phase.get("action_ids") or [])
        for phase in chain["next_actions"].get("execution_phases", [])
        if isinstance(phase, dict)
    )
    sprint_phase_covered_actions = sum(
        len(phase.get("sprint_action_ids") or [])
        + len(phase.get("blocked_later_action_ids") or [])
        for phase in chain["curator_sprint"].get("execution_phase_summary", [])
        if isinstance(phase, dict)
    )
    ready_flags = {
        "prompt_generation": readiness_summary["ready_for_prompt_generation"],
        "training_use": readiness_summary["ready_for_training_use"],
        "public_claims": readiness_summary["ready_for_public_claims"],
        "worker_facing_use": readiness_summary["ready_for_worker_facing_use"],
        "comparable_scoring": readiness_summary["ready_for_comparable_scoring"],
    }
    summary = {
        "consistency_ok": False,
        "safe_for_project_planning": project_summary["safe_for_project_planning"],
        "registered_seed_domain_count": project_summary["registered_seed_domain_count"],
        "regulatory_candidates_found_count": project_summary[
            "regulatory_candidates_found_count"
        ],
        "jurisdiction_pack_scopes": jurisdiction_pack_summary["jurisdiction_scope_count"],
        "jurisdiction_pack_scope_ids": list(jurisdiction_pack_summary["jurisdiction_scope_ids"]),
        "jurisdiction_pack_domain_lenses": jurisdiction_pack_summary["domain_lens_count"],
        "jurisdiction_pack_domain_lens_ids": list(jurisdiction_pack_summary["domain_lens_ids"]),
        "jurisdiction_pack_cells": jurisdiction_pack_summary["pack_cell_count"],
        "jurisdiction_pack_source_object_slots": jurisdiction_pack_summary[
            "source_object_slot_count"
        ],
        "jurisdiction_pack_not_started_source_object_slots": jurisdiction_pack_summary[
            "not_started_source_object_slots"
        ],
        "jurisdiction_pack_language_review_cells": jurisdiction_pack_summary[
            "language_review_required_cells"
        ],
        "jurisdiction_pack_scope_resolution_cells": jurisdiction_pack_summary[
            "scope_resolution_required_cells"
        ],
        "worker_prompt_count": readiness_summary["worker_prompt_count"],
        "worker_prompts_blocked_for_comparable_run": readiness_summary[
            "worker_prompts_blocked_for_comparable_run"
        ],
        "worker_verified_local_law_rows": readiness_summary[
            "worker_verified_local_law_rows"
        ],
        "worker_source_object_tasks": readiness_summary["worker_source_object_tasks"],
        "worker_scope_refinement_tasks": readiness_summary[
            "worker_scope_refinement_tasks"
        ],
        "regulatory_pattern_count": readiness_summary["regulatory_pattern_count"],
        "regulatory_candidate_count": readiness_summary["regulatory_candidate_count"],
        "regulatory_seed_scaffold_operations": readiness_summary[
            "regulatory_seed_scaffold_operations"
        ],
        "readiness_legal_claim_anchor_source_channel_count": readiness_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "readiness_legal_claim_anchor_source_channel_ids": list(
            readiness_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "source_channel_matrix_rows": source_summary["matrix_row_count"],
        "source_channel_count": source_summary["source_channel_count"],
        "source_channel_authority_tiers": source_summary["authority_tier_count"],
        "informal_publication_lead_rows": source_summary["informal_publication_rows"],
        "source_channel_legal_claim_anchor_rows": source_summary["legal_claim_anchor_rows"],
        "source_channel_legal_claim_anchor_source_channel_count": source_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "source_channel_legal_claim_anchor_source_channel_ids": list(
            source_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "source_channel_authenticity_volatility_control_rows": source_summary[
            "authenticity_volatility_control_rows"
        ],
        "informal_publication_authenticity_volatility_control_rows": source_summary[
            "informal_authenticity_volatility_control_rows"
        ],
        "source_channel_review_rows": source_review_summary["review_row_count"],
        "source_channel_review_not_started_rows": source_review_summary["not_started_rows"],
        "source_channel_review_legal_claim_anchor_rows": source_review_summary[
            "legal_claim_anchor_rows"
        ],
        "source_channel_review_legal_claim_anchor_source_channel_count": (
            source_review_summary["legal_claim_anchor_source_channel_count"]
        ),
        "source_channel_review_legal_claim_anchor_source_channel_ids": list(
            source_review_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "source_channel_review_lead_only_claim_rows": source_review_summary[
            "lead_only_claim_rows"
        ],
        "source_channel_review_authenticity_volatility_rows": source_review_summary[
            "authenticity_volatility_review_rows"
        ],
        "source_channel_review_informal_authenticity_volatility_rows": source_review_summary[
            "informal_authenticity_volatility_review_rows"
        ],
        "benchmark_task_blueprints": benchmark_summary["task_blueprint_count"],
        "benchmark_blueprints_blocked": benchmark_summary["blocked_task_blueprints"],
        "benchmark_scoring_dimensions": benchmark_summary["scoring_dimension_count"],
        "benchmark_abstention_rules": benchmark_summary["abstention_rule_count"],
        "benchmark_task_source_grounding_contracts": benchmark_summary[
            "task_source_grounding_contract_count"
        ],
        "benchmark_tasks_requiring_legal_claim_anchor": benchmark_summary[
            "tasks_requiring_legal_claim_anchor"
        ],
        "benchmark_legal_claim_anchor_source_channel_count": benchmark_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "benchmark_legal_claim_anchor_source_channel_ids": list(
            benchmark_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "benchmark_tasks_requiring_source_gap_marker": benchmark_summary[
            "tasks_requiring_source_gap_marker"
        ],
        "benchmark_tasks_barring_informal_standalone_claims": benchmark_summary[
            "tasks_barring_informal_standalone_claims"
        ],
        "benchmark_tasks_requiring_temporal_validity": benchmark_summary[
            "tasks_requiring_temporal_validity"
        ],
        "benchmark_tasks_requiring_language_access_review": benchmark_summary[
            "tasks_requiring_language_access_review"
        ],
        "benchmark_tasks_requiring_entity_resolution_review": benchmark_summary[
            "tasks_requiring_entity_resolution_review"
        ],
        "benchmark_tasks_requiring_remedy_forum_review": benchmark_summary[
            "tasks_requiring_remedy_forum_review"
        ],
        "benchmark_tasks_requiring_authority_hierarchy_review": benchmark_summary[
            "tasks_requiring_authority_hierarchy_review"
        ],
        "benchmark_tasks_requiring_coverage_scope_review": benchmark_summary[
            "tasks_requiring_coverage_scope_review"
        ],
        "benchmark_tasks_requiring_jurisdiction_chain_review": benchmark_summary[
            "tasks_requiring_jurisdiction_chain_review"
        ],
        "benchmark_tasks_requiring_implementation_status_review": benchmark_summary[
            "tasks_requiring_implementation_status_review"
        ],
        "benchmark_tasks_requiring_procedural_burden_review": benchmark_summary[
            "tasks_requiring_procedural_burden_review"
        ],
        "eval_judge_dimension_contracts": eval_contract_summary["judge_dimension_contract_count"],
        "eval_failure_modes": eval_contract_summary["failure_mode_count"],
        "eval_run_gates": eval_contract_summary["run_gate_count"],
        "eval_task_source_grounding_contracts": eval_contract_summary[
            "task_source_grounding_contract_count"
        ],
        "eval_tasks_requiring_legal_claim_anchor": eval_contract_summary[
            "tasks_requiring_legal_claim_anchor"
        ],
        "eval_legal_claim_anchor_source_channel_count": eval_contract_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "eval_legal_claim_anchor_source_channel_ids": list(
            eval_contract_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "eval_tasks_requiring_source_gap_marker": eval_contract_summary[
            "tasks_requiring_source_gap_marker"
        ],
        "eval_tasks_barring_informal_standalone_claims": eval_contract_summary[
            "tasks_barring_informal_standalone_claims"
        ],
        "eval_tasks_requiring_temporal_validity": eval_contract_summary[
            "tasks_requiring_temporal_validity"
        ],
        "eval_tasks_requiring_language_access_review": eval_contract_summary[
            "tasks_requiring_language_access_review"
        ],
        "eval_tasks_requiring_entity_resolution_review": eval_contract_summary[
            "tasks_requiring_entity_resolution_review"
        ],
        "eval_tasks_requiring_remedy_forum_review": eval_contract_summary[
            "tasks_requiring_remedy_forum_review"
        ],
        "eval_tasks_requiring_authority_hierarchy_review": eval_contract_summary[
            "tasks_requiring_authority_hierarchy_review"
        ],
        "eval_tasks_requiring_coverage_scope_review": eval_contract_summary[
            "tasks_requiring_coverage_scope_review"
        ],
        "eval_tasks_requiring_jurisdiction_chain_review": eval_contract_summary[
            "tasks_requiring_jurisdiction_chain_review"
        ],
        "eval_tasks_requiring_implementation_status_review": eval_contract_summary[
            "tasks_requiring_implementation_status_review"
        ],
        "eval_tasks_requiring_procedural_burden_review": eval_contract_summary[
            "tasks_requiring_procedural_burden_review"
        ],
        "eval_model_response_record_fields": eval_contract_summary[
            "model_response_record_field_count"
        ],
        "eval_judge_output_fields": eval_contract_summary["judge_output_field_count"],
        "diagnostic_cells": diagnostic_summary["diagnostic_cell_count"],
        "diagnostic_cells_blocked": diagnostic_summary["blocked_diagnostic_cells"],
        "diagnostic_failure_modes": diagnostic_summary["failure_mode_count"],
        "diagnostic_legal_claim_anchor_source_channel_count": diagnostic_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "diagnostic_legal_claim_anchor_source_channel_ids": list(
            diagnostic_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "judge_calibration_cases": judge_calibration_summary["calibration_case_count"],
        "judge_calibration_cases_blocked": judge_calibration_summary["blocked_calibration_cases"],
        "judge_calibration_critical_cases": judge_calibration_summary["critical_calibration_cases"],
        "judge_calibration_source_grounding_failure_modes": judge_calibration_summary[
            "source_grounding_failure_mode_count"
        ],
        "judge_calibration_source_grounding_cases": judge_calibration_summary[
            "source_grounding_calibration_cases"
        ],
        "judge_calibration_legal_claim_anchor_source_channel_count": judge_calibration_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "judge_calibration_legal_claim_anchor_source_channel_ids": list(
            judge_calibration_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "judge_calibration_cases_requiring_source_grounding_findings": judge_calibration_summary[
            "cases_requiring_source_grounding_findings"
        ],
        "judge_calibration_cases_requiring_legal_anchor_or_gap": judge_calibration_summary[
            "cases_requiring_legal_anchor_or_gap"
        ],
        "judge_calibration_cases_requiring_legal_anchor_source_channels": judge_calibration_summary[
            "cases_requiring_legal_anchor_source_channels"
        ],
        "judge_calibration_cases_requiring_temporal_validity_fields": judge_calibration_summary[
            "cases_requiring_temporal_validity_fields"
        ],
        "judge_calibration_cases_requiring_temporal_validity_findings": judge_calibration_summary[
            "cases_requiring_temporal_validity_findings"
        ],
        "judge_calibration_cases_requiring_language_access_fields": judge_calibration_summary[
            "cases_requiring_language_access_fields"
        ],
        "judge_calibration_cases_requiring_language_access_findings": judge_calibration_summary[
            "cases_requiring_language_access_findings"
        ],
        "judge_calibration_cases_requiring_entity_resolution_fields": judge_calibration_summary[
            "cases_requiring_entity_resolution_fields"
        ],
        "judge_calibration_cases_requiring_entity_resolution_findings": judge_calibration_summary[
            "cases_requiring_entity_resolution_findings"
        ],
        "judge_calibration_cases_requiring_remedy_forum_fields": judge_calibration_summary[
            "cases_requiring_remedy_forum_fields"
        ],
        "judge_calibration_cases_requiring_remedy_forum_findings": judge_calibration_summary[
            "cases_requiring_remedy_forum_findings"
        ],
        "judge_calibration_cases_requiring_authority_hierarchy_fields": judge_calibration_summary[
            "cases_requiring_authority_hierarchy_fields"
        ],
        "judge_calibration_cases_requiring_authority_hierarchy_findings": judge_calibration_summary[
            "cases_requiring_authority_hierarchy_findings"
        ],
        "judge_calibration_cases_requiring_coverage_scope_fields": judge_calibration_summary[
            "cases_requiring_coverage_scope_fields"
        ],
        "judge_calibration_cases_requiring_coverage_scope_findings": judge_calibration_summary[
            "cases_requiring_coverage_scope_findings"
        ],
        "judge_calibration_cases_requiring_jurisdiction_chain_fields": judge_calibration_summary[
            "cases_requiring_jurisdiction_chain_fields"
        ],
        "judge_calibration_cases_requiring_jurisdiction_chain_findings": judge_calibration_summary[
            "cases_requiring_jurisdiction_chain_findings"
        ],
        "judge_calibration_cases_requiring_implementation_access_fields": judge_calibration_summary[
            "cases_requiring_implementation_access_fields"
        ],
        "judge_calibration_cases_requiring_implementation_access_findings": judge_calibration_summary[
            "cases_requiring_implementation_access_findings"
        ],
        "judge_calibration_cases_requiring_procedural_burden_fields": judge_calibration_summary[
            "cases_requiring_procedural_burden_fields"
        ],
        "judge_calibration_cases_requiring_procedural_burden_findings": judge_calibration_summary[
            "cases_requiring_procedural_burden_findings"
        ],
        "transition_gate_rows": transition_summary["transition_count"],
        "transition_gate_blocked_rows": transition_summary["blocked_transition_count"],
        "transition_gate_source_grounding_rows": transition_summary[
            "source_grounding_transition_count"
        ],
        "transition_gate_temporal_validity_rows": transition_summary[
            "temporal_validity_transition_count"
        ],
        "transition_gate_language_access_rows": transition_summary[
            "language_access_transition_count"
        ],
        "transition_gate_entity_resolution_rows": transition_summary[
            "entity_resolution_transition_count"
        ],
        "transition_gate_remedy_forum_rows": transition_summary[
            "remedy_forum_transition_count"
        ],
        "transition_gate_authority_hierarchy_rows": transition_summary[
            "authority_hierarchy_transition_count"
        ],
        "transition_gate_coverage_scope_rows": transition_summary[
            "coverage_scope_transition_count"
        ],
        "transition_gate_jurisdiction_chain_rows": transition_summary[
            "jurisdiction_chain_transition_count"
        ],
        "transition_gate_implementation_access_rows": transition_summary[
            "implementation_access_transition_count"
        ],
        "transition_gate_procedural_burden_rows": transition_summary[
            "procedural_burden_transition_count"
        ],
        "transition_gate_legal_claim_anchor_source_channel_count": transition_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "transition_gate_legal_claim_anchor_source_channel_ids": list(
            transition_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "transition_gate_rows_preserving_legal_anchor_source_channels": transition_summary[
            "transitions_preserving_legal_anchor_source_channels"
        ],
        "next_action_count": next_summary["action_count"],
        "next_execution_phase_count": next_summary["execution_phase_count"],
        "next_execution_phase_covered_actions": next_phase_covered_actions,
        "next_actions_legal_claim_anchor_source_channel_count": next_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "next_actions_legal_claim_anchor_source_channel_ids": list(
            next_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "next_actions_preserving_legal_anchor_source_channels": next_summary[
            "actions_preserving_legal_anchor_source_channels"
        ],
        "next_execution_phases_preserving_legal_anchor_source_channels": next_summary[
            "execution_phases_preserving_legal_anchor_source_channels"
        ],
        "next_immediate_action_count": next_summary["immediate_action_count"],
        "next_blocked_action_count": next_summary["blocked_action_count"],
        "next_regulatory_priority_queue_items": next_summary[
            "regulatory_priority_queue_items"
        ],
        "next_regulatory_top_candidate_id": next_summary["regulatory_top_candidate_id"],
        "curator_sprint_item_count": sprint_summary["sprint_item_count"],
        "curator_execution_phase_count": sprint_summary["execution_phase_count"],
        "curator_execution_phase_covered_actions": sprint_phase_covered_actions,
        "curator_sprint_legal_claim_anchor_source_channel_count": sprint_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "curator_sprint_legal_claim_anchor_source_channel_ids": list(
            sprint_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "curator_sprint_items_preserving_legal_anchor_source_channels": sprint_summary[
            "sprint_items_preserving_legal_anchor_source_channels"
        ],
        "curator_blocked_later_items_preserving_legal_anchor_source_channels": sprint_summary[
            "blocked_later_items_preserving_legal_anchor_source_channels"
        ],
        "curator_execution_phases_preserving_legal_anchor_source_channels": sprint_summary[
            "execution_phases_preserving_legal_anchor_source_channels"
        ],
        "curator_regulatory_priority_queue_items": sprint_summary[
            "regulatory_priority_queue_items"
        ],
        "curator_regulatory_top_candidate_id": sprint_summary[
            "regulatory_top_candidate_id"
        ],
        "curator_blocked_later_items": sprint_summary["blocked_later_items"],
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This curation bundle is a project-planning and curator-handoff artifact only. "
            "It does not verify law, fill source rows, promote manifests, create domain seeds, "
            "generate prompts, train models, enable worker-facing use, publish claims, or "
            "authorize comparable scores."
        ),
    }
    checks = [
        _check(
            "project_plan_safe",
            project_summary["safe_for_project_planning"] is True,
            expected=True,
            actual=project_summary["safe_for_project_planning"],
        ),
        _check(
            "readiness_consistency_ok",
            readiness_summary["consistency_ok"] is True,
            expected=True,
            actual=readiness_summary["consistency_ok"],
        ),
        _check(
            "jurisdiction_pack_matrix_consistency_ok",
            jurisdiction_pack_summary["consistency_ok"] is True,
            expected=True,
            actual=jurisdiction_pack_summary["consistency_ok"],
        ),
        _check(
            "jurisdiction_pack_cells_match_scopes_and_lenses",
            jurisdiction_pack_summary["pack_cell_count"]
            == jurisdiction_pack_summary["jurisdiction_scope_count"]
            * jurisdiction_pack_summary["domain_lens_count"],
            expected=(
                jurisdiction_pack_summary["jurisdiction_scope_count"]
                * jurisdiction_pack_summary["domain_lens_count"]
            ),
            actual=jurisdiction_pack_summary["pack_cell_count"],
        ),
        _check(
            "jurisdiction_pack_source_slots_all_not_started",
            jurisdiction_pack_summary["not_started_source_object_slots"]
            == jurisdiction_pack_summary["source_object_slot_count"],
            expected=jurisdiction_pack_summary["source_object_slot_count"],
            actual=jurisdiction_pack_summary["not_started_source_object_slots"],
        ),
        _check(
            "jurisdiction_pack_readiness_flags_blocked",
            jurisdiction_pack_summary["ready_for_comparable_scoring"] is False,
            expected=False,
            actual=jurisdiction_pack_summary["ready_for_comparable_scoring"],
        ),
        _check(
            "source_channel_matrix_consistency_ok",
            source_summary["consistency_ok"] is True,
            expected=True,
            actual=source_summary["consistency_ok"],
        ),
        _check(
            "informal_publication_rows_stay_lead_only",
            source_summary["informal_publication_rows"] == source_summary["lead_only_rows"],
            expected=source_summary["informal_publication_rows"],
            actual=source_summary["lead_only_rows"],
        ),
        _check(
            "source_channel_authenticity_volatility_controls_cover_all_rows",
            source_summary["authenticity_volatility_control_rows"]
            == source_summary["matrix_row_count"],
            expected=source_summary["matrix_row_count"],
            actual=source_summary["authenticity_volatility_control_rows"],
        ),
        _check(
            "informal_publication_authenticity_volatility_controls_match_leads",
            source_summary["informal_authenticity_volatility_control_rows"]
            == source_summary["informal_publication_rows"],
            expected=source_summary["informal_publication_rows"],
            actual=source_summary["informal_authenticity_volatility_control_rows"],
        ),
        _check(
            "source_channel_review_packet_consistency_ok",
            source_review_summary["consistency_ok"] is True,
            expected=True,
            actual=source_review_summary["consistency_ok"],
        ),
        _check(
            "source_channel_review_rows_match_matrix",
            source_review_summary["review_row_count"] == source_summary["matrix_row_count"],
            expected=source_summary["matrix_row_count"],
            actual=source_review_summary["review_row_count"],
        ),
        _check(
            "source_channel_review_rows_not_started",
            source_review_summary["not_started_rows"] == source_review_summary["review_row_count"],
            expected=source_review_summary["review_row_count"],
            actual=source_review_summary["not_started_rows"],
        ),
        _check(
            "source_channel_review_authenticity_volatility_rows_match_review_rows",
            source_review_summary["authenticity_volatility_review_rows"]
            == source_review_summary["review_row_count"],
            expected=source_review_summary["review_row_count"],
            actual=source_review_summary["authenticity_volatility_review_rows"],
        ),
        _check(
            "source_channel_review_informal_authenticity_volatility_rows_match_leads",
            source_review_summary["informal_authenticity_volatility_review_rows"]
            == source_review_summary["informal_publication_rows"],
            expected=source_review_summary["informal_publication_rows"],
            actual=source_review_summary["informal_authenticity_volatility_review_rows"],
        ),
        _check(
            "benchmark_blueprint_procedural_burden_contracts_cover_tasks",
            benchmark_summary["tasks_requiring_procedural_burden_review"]
            == benchmark_summary["task_blueprint_count"],
            expected=benchmark_summary["task_blueprint_count"],
            actual=benchmark_summary["tasks_requiring_procedural_burden_review"],
        ),
        _check(
            "benchmark_blueprint_consistency_ok",
            benchmark_summary["consistency_ok"] is True,
            expected=True,
            actual=benchmark_summary["consistency_ok"],
        ),
        _check(
            "benchmark_blueprints_all_blocked",
            benchmark_summary["blocked_task_blueprints"] == benchmark_summary["task_blueprint_count"],
            expected=benchmark_summary["task_blueprint_count"],
            actual=benchmark_summary["blocked_task_blueprints"],
        ),
        _check(
            "eval_contract_consistency_ok",
            eval_contract_summary["consistency_ok"] is True,
            expected=True,
            actual=eval_contract_summary["consistency_ok"],
        ),
        _check(
            "eval_contract_matches_blueprint_dimensions",
            eval_contract_summary["judge_dimension_contract_count"]
            == benchmark_summary["scoring_dimension_count"],
            expected=benchmark_summary["scoring_dimension_count"],
            actual=eval_contract_summary["judge_dimension_contract_count"],
        ),
        _check(
            "eval_contract_flags_blocked",
            eval_contract_summary["ready_for_model_response_capture"] is False
            and eval_contract_summary["ready_for_comparable_scoring"] is False,
            expected=False,
            actual={
                "model_response_capture": eval_contract_summary[
                    "ready_for_model_response_capture"
                ],
                "comparable_scoring": eval_contract_summary["ready_for_comparable_scoring"],
            },
        ),
        _check(
            "diagnostic_run_plan_consistency_ok",
            diagnostic_summary["consistency_ok"] is True,
            expected=True,
            actual=diagnostic_summary["consistency_ok"],
        ),
        _check(
            "diagnostic_cells_match_blueprints",
            diagnostic_summary["diagnostic_cell_count"] == benchmark_summary["task_blueprint_count"],
            expected=benchmark_summary["task_blueprint_count"],
            actual=diagnostic_summary["diagnostic_cell_count"],
        ),
        _check(
            "diagnostic_cells_all_blocked",
            diagnostic_summary["blocked_diagnostic_cells"] == diagnostic_summary["diagnostic_cell_count"],
            expected=diagnostic_summary["diagnostic_cell_count"],
            actual=diagnostic_summary["blocked_diagnostic_cells"],
        ),
        _check(
            "judge_calibration_plan_consistency_ok",
            judge_calibration_summary["consistency_ok"] is True,
            expected=True,
            actual=judge_calibration_summary["consistency_ok"],
        ),
        _check(
            "judge_calibration_cases_match_failure_modes",
            judge_calibration_summary["calibration_case_count"] == eval_contract_summary["failure_mode_count"],
            expected=eval_contract_summary["failure_mode_count"],
            actual=judge_calibration_summary["calibration_case_count"],
        ),
        _check(
            "judge_calibration_cases_all_blocked",
            judge_calibration_summary["blocked_calibration_cases"]
            == judge_calibration_summary["calibration_case_count"],
            expected=judge_calibration_summary["calibration_case_count"],
            actual=judge_calibration_summary["blocked_calibration_cases"],
        ),
        _check(
            "judge_calibration_legal_anchor_channels_match_eval_contract",
            judge_calibration_summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_summary["legal_claim_anchor_source_channel_count"]
            and judge_calibration_summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_summary["legal_claim_anchor_source_channel_ids"],
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
            actual={
                "legal_claim_anchor_source_channel_count": judge_calibration_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": judge_calibration_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "transition_gate_consistency_ok",
            transition_summary["consistency_ok"] is True,
            expected=True,
            actual=transition_summary["consistency_ok"],
        ),
        _check(
            "transition_gate_rows_all_blocked",
            transition_summary["blocked_transition_count"] == transition_summary["transition_count"],
            expected=transition_summary["transition_count"],
            actual=transition_summary["blocked_transition_count"],
        ),
        _check(
            "transition_gate_legal_anchor_channels_match_eval_contract",
            transition_summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_summary["legal_claim_anchor_source_channel_count"]
            and transition_summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_summary["legal_claim_anchor_source_channel_ids"]
            and transition_summary["transitions_preserving_legal_anchor_source_channels"]
            == transition_summary["transition_count"],
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "transition_count": transition_summary["transition_count"],
            },
            actual={
                "legal_claim_anchor_source_channel_count": transition_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": transition_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "transition_count": transition_summary[
                    "transitions_preserving_legal_anchor_source_channels"
                ],
            },
        ),
        _check(
            "next_actions_consistency_ok",
            next_summary["consistency_ok"] is True,
            expected=True,
            actual=next_summary["consistency_ok"],
        ),
        _check(
            "next_actions_legal_anchor_channels_match_eval_contract",
            next_summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_summary["legal_claim_anchor_source_channel_count"]
            and next_summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_summary["legal_claim_anchor_source_channel_ids"]
            and next_summary["actions_preserving_legal_anchor_source_channels"]
            == next_summary["action_count"]
            and next_summary["execution_phases_preserving_legal_anchor_source_channels"]
            == next_summary["execution_phase_count"],
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "action_count": next_summary["action_count"],
                "execution_phase_count": next_summary["execution_phase_count"],
            },
            actual={
                "legal_claim_anchor_source_channel_count": next_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": next_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "action_count": next_summary[
                    "actions_preserving_legal_anchor_source_channels"
                ],
                "execution_phase_count": next_summary[
                    "execution_phases_preserving_legal_anchor_source_channels"
                ],
            },
        ),
        _check(
            "curator_sprint_consistency_ok",
            sprint_summary["consistency_ok"] is True,
            expected=True,
            actual=sprint_summary["consistency_ok"],
        ),
        _check(
            "curator_sprint_legal_anchor_channels_match_next_actions",
            sprint_summary["legal_claim_anchor_source_channel_count"]
            == next_summary["legal_claim_anchor_source_channel_count"]
            and sprint_summary["legal_claim_anchor_source_channel_ids"]
            == next_summary["legal_claim_anchor_source_channel_ids"]
            and sprint_summary["sprint_items_preserving_legal_anchor_source_channels"]
            == sprint_summary["sprint_item_count"]
            and sprint_summary["blocked_later_items_preserving_legal_anchor_source_channels"]
            == sprint_summary["blocked_later_items"]
            and sprint_summary["execution_phases_preserving_legal_anchor_source_channels"]
            == sprint_summary["execution_phase_count"],
            expected={
                "legal_claim_anchor_source_channel_count": next_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": next_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "sprint_item_count": sprint_summary["sprint_item_count"],
                "blocked_later_items": sprint_summary["blocked_later_items"],
                "execution_phase_count": sprint_summary["execution_phase_count"],
            },
            actual={
                "legal_claim_anchor_source_channel_count": sprint_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": sprint_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "sprint_item_count": sprint_summary[
                    "sprint_items_preserving_legal_anchor_source_channels"
                ],
                "blocked_later_items": sprint_summary[
                    "blocked_later_items_preserving_legal_anchor_source_channels"
                ],
                "execution_phase_count": sprint_summary[
                    "execution_phases_preserving_legal_anchor_source_channels"
                ],
            },
        ),
        _check(
            "next_actions_match_curator_sprint",
            next_summary["immediate_action_count"] == sprint_summary["sprint_item_count"],
            expected=next_summary["immediate_action_count"],
            actual=sprint_summary["sprint_item_count"],
        ),
        _check(
            "next_execution_phases_cover_actions",
            next_phase_covered_actions == next_summary["action_count"],
            expected=next_summary["action_count"],
            actual=next_phase_covered_actions,
        ),
        _check(
            "curator_phase_summary_covers_sprint_and_blocked",
            sprint_phase_covered_actions
            == sprint_summary["sprint_item_count"] + sprint_summary["blocked_later_items"],
            expected=sprint_summary["sprint_item_count"] + sprint_summary["blocked_later_items"],
            actual=sprint_phase_covered_actions,
        ),
        _check(
            "execution_phase_counts_match_curator_sprint",
            next_summary["execution_phase_count"] == sprint_summary["execution_phase_count"],
            expected=next_summary["execution_phase_count"],
            actual=sprint_summary["execution_phase_count"],
        ),
        _check(
            "execution_phase_coverage_matches_curator_sprint",
            next_phase_covered_actions == sprint_phase_covered_actions,
            expected=next_phase_covered_actions,
            actual=sprint_phase_covered_actions,
        ),
        _check(
            "regulatory_priority_queue_matches_curator_sprint",
            next_summary["regulatory_priority_queue_items"]
            == sprint_summary["regulatory_priority_queue_items"],
            expected=next_summary["regulatory_priority_queue_items"],
            actual=sprint_summary["regulatory_priority_queue_items"],
        ),
        _check(
            "regulatory_top_candidate_matches_curator_sprint",
            next_summary["regulatory_top_candidate_id"]
            == sprint_summary["regulatory_top_candidate_id"],
            expected=next_summary["regulatory_top_candidate_id"],
            actual=sprint_summary["regulatory_top_candidate_id"],
        ),
        _check(
            "blocked_later_counts_match",
            next_summary["blocked_action_count"] == sprint_summary["blocked_later_items"],
            expected=next_summary["blocked_action_count"],
            actual=sprint_summary["blocked_later_items"],
        ),
        _check(
            "worker_prompts_still_blocked",
            readiness_summary["worker_prompts_blocked_for_comparable_run"]
            == readiness_summary["worker_prompt_count"],
            expected=readiness_summary["worker_prompt_count"],
            actual=readiness_summary["worker_prompts_blocked_for_comparable_run"],
        ),
        _check(
            "readiness_legal_anchor_channels_match_source_matrix",
            readiness_summary["legal_claim_anchor_source_channel_count"]
            == len(source_channel_builder.legal_claim_anchor_source_channel_ids())
            and readiness_summary["legal_claim_anchor_source_channel_ids"]
            == source_channel_builder.legal_claim_anchor_source_channel_ids(),
            expected={
                "legal_claim_anchor_source_channel_count": len(
                    source_channel_builder.legal_claim_anchor_source_channel_ids()
                ),
                "legal_claim_anchor_source_channel_ids": (
                    source_channel_builder.legal_claim_anchor_source_channel_ids()
                ),
            },
            actual={
                "legal_claim_anchor_source_channel_count": readiness_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": readiness_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "source_channel_matrix_legal_anchor_channels_match_source_policy",
            source_summary["legal_claim_anchor_source_channel_count"]
            == len(source_channel_builder.legal_claim_anchor_source_channel_ids())
            and source_summary["legal_claim_anchor_source_channel_ids"]
            == source_channel_builder.legal_claim_anchor_source_channel_ids(),
            expected={
                "legal_claim_anchor_source_channel_count": len(
                    source_channel_builder.legal_claim_anchor_source_channel_ids()
                ),
                "legal_claim_anchor_source_channel_ids": (
                    source_channel_builder.legal_claim_anchor_source_channel_ids()
                ),
            },
            actual={
                "legal_claim_anchor_source_channel_count": source_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": source_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "source_channel_review_legal_anchor_channels_match_source_matrix",
            source_review_summary["legal_claim_anchor_source_channel_count"]
            == source_summary["legal_claim_anchor_source_channel_count"]
            and source_review_summary["legal_claim_anchor_source_channel_ids"]
            == source_summary["legal_claim_anchor_source_channel_ids"],
            expected={
                "legal_claim_anchor_source_channel_count": source_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": source_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
            actual={
                "legal_claim_anchor_source_channel_count": source_review_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": source_review_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_curation_bundle.v1",
            "project_config": _display_path(project_config_path),
            "domain": domain_id,
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "status": (
                "top-level curation bundle; not legal advice, not source verification, not "
                "prompt generation, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "component_summaries": _component_summaries(chain),
        "checks": checks,
        "artifact_paths": component_paths(output_dir=component_dir, domain_id=domain_id),
    }
    disallowed = _contains_disallowed_text(doc)
    privacy_scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("bundle_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", privacy_scan.get("ok") is True, expected=True, actual=privacy_scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _write_doc_pair(
    doc: dict[str, Any],
    json_path: pathlib.Path,
    markdown_path: pathlib.Path,
    markdown: str,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown + "\n", encoding="utf-8")


def write_component_artifacts(
    chain: dict[str, dict[str, Any]],
    *,
    output_dir: pathlib.Path | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    include_lower_components: bool = False,
) -> dict[str, str]:
    """Write the upstream global protections artifacts used by this bundle."""
    base = output_dir or OUT_DIR
    paths = component_paths(output_dir=base, domain_id=domain_id)
    _write_doc_pair(
        chain["project_plan"],
        base / "global_protections_project_plan.json",
        base / "global_protections_project_plan.md",
        project_plan_builder.build_markdown_report(chain["project_plan"]),
    )
    _write_doc_pair(
        chain["readiness_bundle"],
        base / "global_protections_readiness_bundle.json",
        base / "global_protections_readiness_bundle.md",
        readiness_builder.build_markdown_report(chain["readiness_bundle"]),
    )
    _write_doc_pair(
        chain["jurisdiction_pack_matrix"],
        base / "global_protections_jurisdiction_pack_matrix.json",
        base / "global_protections_jurisdiction_pack_matrix.md",
        jurisdiction_pack_builder.build_markdown_report(chain["jurisdiction_pack_matrix"]),
    )
    _write_doc_pair(
        chain["source_channel_matrix"],
        base / "global_protections_source_channel_matrix.json",
        base / "global_protections_source_channel_matrix.md",
        source_channel_builder.build_markdown_report(chain["source_channel_matrix"]),
    )
    _write_doc_pair(
        chain["source_channel_review_packet"],
        base / "global_protections_source_channel_review_packet.json",
        base / "global_protections_source_channel_review_packet.md",
        source_review_builder.build_markdown_report(chain["source_channel_review_packet"]),
    )
    _write_doc_pair(
        chain["benchmark_blueprint"],
        base / "global_protections_benchmark_blueprint.json",
        base / "global_protections_benchmark_blueprint.md",
        benchmark_blueprint_builder.build_markdown_report(chain["benchmark_blueprint"]),
    )
    _write_doc_pair(
        chain["eval_contract"],
        base / "global_protections_eval_contract.json",
        base / "global_protections_eval_contract.md",
        eval_contract_builder.build_markdown_report(chain["eval_contract"]),
    )
    _write_doc_pair(
        chain["diagnostic_run_plan"],
        base / "global_protections_diagnostic_run_plan.json",
        base / "global_protections_diagnostic_run_plan.md",
        diagnostic_run_builder.build_markdown_report(chain["diagnostic_run_plan"]),
    )
    _write_doc_pair(
        chain["judge_calibration_plan"],
        base / "global_protections_judge_calibration_plan.json",
        base / "global_protections_judge_calibration_plan.md",
        judge_calibration_builder.build_markdown_report(chain["judge_calibration_plan"]),
    )
    _write_doc_pair(
        chain["transition_gate"],
        base / "global_protections_transition_gate.json",
        base / "global_protections_transition_gate.md",
        transition_gate_builder.build_markdown_report(chain["transition_gate"]),
    )
    _write_doc_pair(
        chain["next_actions"],
        base / "global_protections_next_actions.json",
        base / "global_protections_next_actions.md",
        next_actions_builder.build_markdown_report(chain["next_actions"]),
    )
    _write_doc_pair(
        chain["curator_sprint"],
        base / "global_protections_curator_sprint.json",
        base / "global_protections_curator_sprint.md",
        curator_sprint_builder.build_markdown_report(chain["curator_sprint"]),
    )
    if include_lower_components:
        paths.update(
            readiness_builder.write_upstream_artifacts(
                chain["_readiness_chain"],
                output_dir=base,
                domain_id=domain_id,
                include_components=True,
            )
        )
    return paths


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown curation bundle."""
    summary = doc["summary"]
    lines: list[str] = [
        "# Global Protections Curation Bundle",
        "",
        (
            "This bundle composes the project plan, jurisdiction-pack matrix, source-channel "
            "matrix, source-channel review packet, benchmark blueprint, evaluation contract, "
            "diagnostic run plan, judge-calibration plan, transition gate, readiness bundle, "
            "next-actions backlog, and curator sprint packet. "
            "It is not legal advice, not source verification, not prompt generation, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Safe for project planning | {str(bool(summary['safe_for_project_planning'])).lower()} |",
        f"| Registered seed domains | {summary['registered_seed_domain_count']} |",
        f"| Regulatory candidates found | {summary['regulatory_candidates_found_count']} |",
        f"| Jurisdiction-pack scopes | {summary['jurisdiction_pack_scopes']} |",
        f"| Jurisdiction-pack scope IDs | `{_md_cell(', '.join(summary['jurisdiction_pack_scope_ids']))}` |",
        f"| Jurisdiction-pack domain lenses | {summary['jurisdiction_pack_domain_lenses']} |",
        f"| Jurisdiction-pack domain lens IDs | `{_md_cell(', '.join(summary['jurisdiction_pack_domain_lens_ids']))}` |",
        f"| Jurisdiction-pack cells | {summary['jurisdiction_pack_cells']} |",
        (
            "| Jurisdiction-pack source-object slots "
            f"| {summary['jurisdiction_pack_source_object_slots']} |"
        ),
        (
            "| Jurisdiction-pack not-started source-object slots "
            f"| {summary['jurisdiction_pack_not_started_source_object_slots']} |"
        ),
        (
            "| Jurisdiction-pack language-review cells "
            f"| {summary['jurisdiction_pack_language_review_cells']} |"
        ),
        (
            "| Jurisdiction-pack scope-resolution cells "
            f"| {summary['jurisdiction_pack_scope_resolution_cells']} |"
        ),
        f"| Worker prompts | {summary['worker_prompt_count']} |",
        (
            "| Worker prompts blocked for comparable run "
            f"| {summary['worker_prompts_blocked_for_comparable_run']} |"
        ),
        (
            "| Worker verified local-law rows "
            f"| {summary['worker_verified_local_law_rows']} |"
        ),
        (
            "| Worker source-object tasks "
            f"| {summary['worker_source_object_tasks']} |"
        ),
        (
            "| Worker scope-refinement tasks "
            f"| {summary['worker_scope_refinement_tasks']} |"
        ),
        f"| Regulatory patterns | {summary['regulatory_pattern_count']} |",
        (
            "| Regulatory candidate domains "
            f"| {summary['regulatory_candidate_count']} |"
        ),
        (
            "| Regulatory seed scaffold operations "
            f"| {summary['regulatory_seed_scaffold_operations']} |"
        ),
        (
            "| Readiness legal-claim anchor source channels "
            f"| {summary['readiness_legal_claim_anchor_source_channel_count']} |"
        ),
        f"| Source-channel matrix rows | {summary['source_channel_matrix_rows']} |",
        f"| Source channels | {summary['source_channel_count']} |",
        f"| Source-channel authority tiers | {summary['source_channel_authority_tiers']} |",
        f"| Informal publication lead rows | {summary['informal_publication_lead_rows']} |",
        (
            "| Source-channel legal-claim anchor rows "
            f"| {summary['source_channel_legal_claim_anchor_rows']} |"
        ),
        (
            "| Source-channel legal-claim anchor source channels "
            f"| {summary['source_channel_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Source-channel authenticity/volatility control rows "
            f"| {summary['source_channel_authenticity_volatility_control_rows']} |"
        ),
        (
            "| Informal publication authenticity/volatility control rows "
            f"| {summary['informal_publication_authenticity_volatility_control_rows']} |"
        ),
        f"| Source-channel review rows | {summary['source_channel_review_rows']} |",
        f"| Source-channel review not-started rows | {summary['source_channel_review_not_started_rows']} |",
        (
            "| Source-channel review legal-claim anchor rows "
            f"| {summary['source_channel_review_legal_claim_anchor_rows']} |"
        ),
        (
            "| Source-channel review legal-claim anchor source channels "
            f"| {summary['source_channel_review_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Source-channel review lead-only claim rows "
            f"| {summary['source_channel_review_lead_only_claim_rows']} |"
        ),
        (
            "| Source-channel review authenticity/volatility rows "
            f"| {summary['source_channel_review_authenticity_volatility_rows']} |"
        ),
        (
            "| Source-channel review informal authenticity/volatility rows "
            f"| {summary['source_channel_review_informal_authenticity_volatility_rows']} |"
        ),
        f"| Benchmark task blueprints | {summary['benchmark_task_blueprints']} |",
        f"| Benchmark blueprints blocked | {summary['benchmark_blueprints_blocked']} |",
        f"| Benchmark scoring dimensions | {summary['benchmark_scoring_dimensions']} |",
        f"| Benchmark abstention rules | {summary['benchmark_abstention_rules']} |",
        (
            "| Benchmark task source-grounding contracts "
            f"| {summary['benchmark_task_source_grounding_contracts']} |"
        ),
        (
            "| Benchmark tasks requiring legal-claim anchor "
            f"| {summary['benchmark_tasks_requiring_legal_claim_anchor']} |"
        ),
        (
            "| Benchmark legal-claim anchor source channels "
            f"| {summary['benchmark_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Benchmark tasks requiring source-gap marker "
            f"| {summary['benchmark_tasks_requiring_source_gap_marker']} |"
        ),
        (
            "| Benchmark tasks barring informal standalone claims "
            f"| {summary['benchmark_tasks_barring_informal_standalone_claims']} |"
        ),
        (
            "| Benchmark tasks requiring temporal validity "
            f"| {summary['benchmark_tasks_requiring_temporal_validity']} |"
        ),
        (
            "| Benchmark tasks requiring language-access review "
            f"| {summary['benchmark_tasks_requiring_language_access_review']} |"
        ),
        (
            "| Benchmark tasks requiring entity-resolution review "
            f"| {summary['benchmark_tasks_requiring_entity_resolution_review']} |"
        ),
        (
            "| Benchmark tasks requiring remedy/forum review "
            f"| {summary['benchmark_tasks_requiring_remedy_forum_review']} |"
        ),
        (
            "| Benchmark tasks requiring authority-hierarchy review "
            f"| {summary['benchmark_tasks_requiring_authority_hierarchy_review']} |"
        ),
        (
            "| Benchmark tasks requiring coverage-scope review "
            f"| {summary['benchmark_tasks_requiring_coverage_scope_review']} |"
        ),
        (
            "| Benchmark tasks requiring jurisdiction-chain review "
            f"| {summary['benchmark_tasks_requiring_jurisdiction_chain_review']} |"
        ),
        (
            "| Benchmark tasks requiring implementation-status review "
            f"| {summary['benchmark_tasks_requiring_implementation_status_review']} |"
        ),
        (
            "| Benchmark tasks requiring procedural-burden review "
            f"| {summary['benchmark_tasks_requiring_procedural_burden_review']} |"
        ),
        f"| Eval judge dimension contracts | {summary['eval_judge_dimension_contracts']} |",
        f"| Eval failure modes | {summary['eval_failure_modes']} |",
        f"| Eval run gates | {summary['eval_run_gates']} |",
        (
            "| Eval task source-grounding contracts "
            f"| {summary['eval_task_source_grounding_contracts']} |"
        ),
        (
            "| Eval tasks requiring legal-claim anchor "
            f"| {summary['eval_tasks_requiring_legal_claim_anchor']} |"
        ),
        (
            "| Eval legal-claim anchor source channels "
            f"| {summary['eval_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Eval tasks requiring source-gap marker "
            f"| {summary['eval_tasks_requiring_source_gap_marker']} |"
        ),
        (
            "| Eval tasks barring informal standalone claims "
            f"| {summary['eval_tasks_barring_informal_standalone_claims']} |"
        ),
        (
            "| Eval tasks requiring temporal validity "
            f"| {summary['eval_tasks_requiring_temporal_validity']} |"
        ),
        (
            "| Eval tasks requiring language-access review "
            f"| {summary['eval_tasks_requiring_language_access_review']} |"
        ),
        (
            "| Eval tasks requiring entity-resolution review "
            f"| {summary['eval_tasks_requiring_entity_resolution_review']} |"
        ),
        (
            "| Eval tasks requiring remedy/forum review "
            f"| {summary['eval_tasks_requiring_remedy_forum_review']} |"
        ),
        (
            "| Eval tasks requiring authority-hierarchy review "
            f"| {summary['eval_tasks_requiring_authority_hierarchy_review']} |"
        ),
        (
            "| Eval tasks requiring coverage-scope review "
            f"| {summary['eval_tasks_requiring_coverage_scope_review']} |"
        ),
        (
            "| Eval tasks requiring jurisdiction-chain review "
            f"| {summary['eval_tasks_requiring_jurisdiction_chain_review']} |"
        ),
        (
            "| Eval tasks requiring implementation-status review "
            f"| {summary['eval_tasks_requiring_implementation_status_review']} |"
        ),
        (
            "| Eval tasks requiring procedural-burden review "
            f"| {summary['eval_tasks_requiring_procedural_burden_review']} |"
        ),
        f"| Eval model response record fields | {summary['eval_model_response_record_fields']} |",
        f"| Eval judge output fields | {summary['eval_judge_output_fields']} |",
        f"| Diagnostic cells | {summary['diagnostic_cells']} |",
        f"| Diagnostic cells blocked | {summary['diagnostic_cells_blocked']} |",
        f"| Diagnostic failure modes | {summary['diagnostic_failure_modes']} |",
        (
            "| Diagnostic legal-claim anchor source channels "
            f"| {summary['diagnostic_legal_claim_anchor_source_channel_count']} |"
        ),
        f"| Judge calibration cases | {summary['judge_calibration_cases']} |",
        f"| Judge calibration cases blocked | {summary['judge_calibration_cases_blocked']} |",
        f"| Judge calibration critical cases | {summary['judge_calibration_critical_cases']} |",
        (
            "| Judge calibration source-grounding failure modes "
            f"| {summary['judge_calibration_source_grounding_failure_modes']} |"
        ),
        (
            "| Judge calibration source-grounding cases "
            f"| {summary['judge_calibration_source_grounding_cases']} |"
        ),
        (
            "| Judge calibration legal-claim anchor source channels "
            f"| {summary['judge_calibration_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Judge calibration cases requiring source-grounding findings "
            f"| {summary['judge_calibration_cases_requiring_source_grounding_findings']} |"
        ),
        (
            "| Judge calibration cases requiring legal anchor or gap "
            f"| {summary['judge_calibration_cases_requiring_legal_anchor_or_gap']} |"
        ),
        (
            "| Judge calibration cases requiring legal-anchor source channels "
            f"| {summary['judge_calibration_cases_requiring_legal_anchor_source_channels']} |"
        ),
        (
            "| Judge calibration cases requiring temporal-validity fields "
            f"| {summary['judge_calibration_cases_requiring_temporal_validity_fields']} |"
        ),
        (
            "| Judge calibration cases requiring temporal-validity findings "
            f"| {summary['judge_calibration_cases_requiring_temporal_validity_findings']} |"
        ),
        (
            "| Judge calibration cases requiring language-access fields "
            f"| {summary['judge_calibration_cases_requiring_language_access_fields']} |"
        ),
        (
            "| Judge calibration cases requiring language-access findings "
            f"| {summary['judge_calibration_cases_requiring_language_access_findings']} |"
        ),
        (
            "| Judge calibration cases requiring entity-resolution fields "
            f"| {summary['judge_calibration_cases_requiring_entity_resolution_fields']} |"
        ),
        (
            "| Judge calibration cases requiring entity-resolution findings "
            f"| {summary['judge_calibration_cases_requiring_entity_resolution_findings']} |"
        ),
        (
            "| Judge calibration cases requiring remedy/forum fields "
            f"| {summary['judge_calibration_cases_requiring_remedy_forum_fields']} |"
        ),
        (
            "| Judge calibration cases requiring remedy/forum findings "
            f"| {summary['judge_calibration_cases_requiring_remedy_forum_findings']} |"
        ),
        (
            "| Judge calibration cases requiring authority-hierarchy fields "
            f"| {summary['judge_calibration_cases_requiring_authority_hierarchy_fields']} |"
        ),
        (
            "| Judge calibration cases requiring authority-hierarchy findings "
            f"| {summary['judge_calibration_cases_requiring_authority_hierarchy_findings']} |"
        ),
        (
            "| Judge calibration cases requiring coverage-scope fields "
            f"| {summary['judge_calibration_cases_requiring_coverage_scope_fields']} |"
        ),
        (
            "| Judge calibration cases requiring coverage-scope findings "
            f"| {summary['judge_calibration_cases_requiring_coverage_scope_findings']} |"
        ),
        (
            "| Judge calibration cases requiring jurisdiction-chain fields "
            f"| {summary['judge_calibration_cases_requiring_jurisdiction_chain_fields']} |"
        ),
        (
            "| Judge calibration cases requiring jurisdiction-chain findings "
            f"| {summary['judge_calibration_cases_requiring_jurisdiction_chain_findings']} |"
        ),
        (
            "| Judge calibration cases requiring implementation-access fields "
            f"| {summary['judge_calibration_cases_requiring_implementation_access_fields']} |"
        ),
        (
            "| Judge calibration cases requiring implementation-access findings "
            f"| {summary['judge_calibration_cases_requiring_implementation_access_findings']} |"
        ),
        (
            "| Judge calibration cases requiring procedural-burden fields "
            f"| {summary['judge_calibration_cases_requiring_procedural_burden_fields']} |"
        ),
        (
            "| Judge calibration cases requiring procedural-burden findings "
            f"| {summary['judge_calibration_cases_requiring_procedural_burden_findings']} |"
        ),
        f"| Transition gate rows | {summary['transition_gate_rows']} |",
        f"| Transition gate blocked rows | {summary['transition_gate_blocked_rows']} |",
        f"| Transition gate source-grounding rows | {summary['transition_gate_source_grounding_rows']} |",
        f"| Transition gate temporal-validity rows | {summary['transition_gate_temporal_validity_rows']} |",
        f"| Transition gate language-access rows | {summary['transition_gate_language_access_rows']} |",
        f"| Transition gate entity-resolution rows | {summary['transition_gate_entity_resolution_rows']} |",
        f"| Transition gate remedy/forum rows | {summary['transition_gate_remedy_forum_rows']} |",
        f"| Transition gate authority-hierarchy rows | {summary['transition_gate_authority_hierarchy_rows']} |",
        f"| Transition gate coverage-scope rows | {summary['transition_gate_coverage_scope_rows']} |",
        f"| Transition gate jurisdiction-chain rows | {summary['transition_gate_jurisdiction_chain_rows']} |",
        f"| Transition gate implementation-access rows | {summary['transition_gate_implementation_access_rows']} |",
        f"| Transition gate procedural-burden rows | {summary['transition_gate_procedural_burden_rows']} |",
        (
            "| Transition gate legal-claim anchor source channels "
            f"| {summary['transition_gate_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Transition gate rows preserving legal-anchor source channels "
            f"| {summary['transition_gate_rows_preserving_legal_anchor_source_channels']} |"
        ),
        f"| Next actions | {summary['next_action_count']} |",
        f"| Next execution phases | {summary['next_execution_phase_count']} |",
        f"| Next phase-covered actions | {summary['next_execution_phase_covered_actions']} |",
        (
            "| Next-actions legal-claim anchor source channels "
            f"| {summary['next_actions_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Next-actions preserving legal-anchor source channels "
            f"| {summary['next_actions_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Next execution phases preserving legal-anchor source channels "
            f"| {summary['next_execution_phases_preserving_legal_anchor_source_channels']} |"
        ),
        f"| Immediate next actions | {summary['next_immediate_action_count']} |",
        f"| Blocked next actions | {summary['next_blocked_action_count']} |",
        f"| Next regulatory priority queue items | {summary['next_regulatory_priority_queue_items']} |",
        f"| Next regulatory top candidate | {_md_cell(summary['next_regulatory_top_candidate_id'])} |",
        f"| Curator sprint items | {summary['curator_sprint_item_count']} |",
        f"| Curator execution phases | {summary['curator_execution_phase_count']} |",
        f"| Curator phase-covered actions | {summary['curator_execution_phase_covered_actions']} |",
        (
            "| Curator sprint legal-claim anchor source channels "
            f"| {summary['curator_sprint_legal_claim_anchor_source_channel_count']} |"
        ),
        (
            "| Curator sprint items preserving legal-anchor source channels "
            f"| {summary['curator_sprint_items_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Curator blocked-later items preserving legal-anchor source channels "
            f"| {summary['curator_blocked_later_items_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Curator execution phases preserving legal-anchor source channels "
            f"| {summary['curator_execution_phases_preserving_legal_anchor_source_channels']} |"
        ),
        (
            "| Curator regulatory priority queue items "
            f"| {summary['curator_regulatory_priority_queue_items']} |"
        ),
        (
            "| Curator regulatory top candidate "
            f"| {_md_cell(summary['curator_regulatory_top_candidate_id'])} |"
        ),
        f"| Curator blocked-later items | {summary['curator_blocked_later_items']} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for training use | {str(bool(summary['ready_for_training_use'])).lower()} |",
        f"| Ready for public claims | {str(bool(summary['ready_for_public_claims'])).lower()} |",
        f"| Ready for worker-facing use | {str(bool(summary['ready_for_worker_facing_use'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Component Summaries",
        "",
        "| Component | Key Status | Count |",
        "|---|---|---:|",
    ]
    for component, component_summary in doc["component_summaries"].items():
        count = (
            component_summary.get("sprint_item_count")
            or component_summary.get("action_count")
            or component_summary.get("calibration_case_count")
            or component_summary.get("transition_count")
            or component_summary.get("diagnostic_cell_count")
            or component_summary.get("judge_dimension_contract_count")
            or component_summary.get("task_blueprint_count")
            or component_summary.get("review_row_count")
            or component_summary.get("matrix_row_count")
            or component_summary.get("pack_cell_count")
            or component_summary.get("worker_prompt_count")
            or component_summary.get("registered_seed_domain_count")
        )
        status = (
            component_summary.get("consistency_ok")
            if "consistency_ok" in component_summary
            else component_summary.get("safe_for_project_planning")
        )
        lines.append(
            f"| `{_md_cell(component)}` | {_md_cell(str(bool(status)).lower())} | {_md_cell(count)} |"
        )
    lines.extend([
        "",
        "## Checks",
        "",
        "| Check | OK | Expected | Actual |",
        "|---|---:|---|---|",
    ])
    for check in doc["checks"]:
        lines.append(
            f"| {_md_cell(check['id'])} "
            f"| {str(bool(check['ok'])).lower()} "
            f"| {_md_cell(check['expected'])} "
            f"| {_md_cell(check['actual'])} |"
        )
    lines.extend([
        "",
        "## Artifact Paths",
        "",
    ])
    for key, path in doc["artifact_paths"].items():
        lines.append(f"- `{_md_cell(key)}`: `{_md_cell(path)}`")
    lines.extend([
        "",
        "## Non-Scoring Rule",
        "",
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--project-config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown bundle report")
    ap.add_argument(
        "--write-components",
        action="store_true",
        help="also write the upstream global protections project/readiness/backlog/sprint artifacts",
    )
    ap.add_argument(
        "--write-all-components",
        action="store_true",
        help="also write lower-level domain and regulatory curation-chain artifacts",
    )
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    chain = build_global_protections_chain(
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    doc = build_curation_bundle(
        chain=chain,
        domain_id=args.domain,
        project_config_path=args.project_config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    if args.write_components or args.write_all_components:
        doc["artifact_paths"].update(
            write_component_artifacts(
                chain,
                output_dir=args.component_dir,
                domain_id=args.domain,
                include_lower_components=args.write_all_components,
            )
        )
    doc["artifact_paths"]["global_protections_curation_bundle_json"] = _artifact_path(args.out)
    if not args.no_md:
        doc["artifact_paths"]["global_protections_curation_bundle_markdown"] = _artifact_path(args.md_out)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    summary = doc["summary"]
    print(
        "[global-protections-curation-bundle] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"safe_for_project_planning={str(bool(summary['safe_for_project_planning'])).lower()}; "
        f"{summary['curator_sprint_item_count']} sprint items; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0 if summary["consistency_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
