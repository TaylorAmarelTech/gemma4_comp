#!/usr/bin/env python3
"""Build the evaluation contract for the global protections benchmark.

The benchmark blueprint defines future task and scoring shapes. This command
adds the next layer: how future model-response capture and judge output must be
structured once reviewed sources exist. It is a schema and failure-taxonomy
contract only. It does not instantiate prompts, run models, grade responses,
verify law, or authorize comparable scoring.

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

import build_global_protections_benchmark_blueprint as blueprint_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_eval_contract.json"
MD_OUT = OUT_DIR / "global_protections_eval_contract.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "prompt_text",
    "https://",
    "www.",
]

MODEL_RESPONSE_RECORD_FIELDS = [
    "run_id",
    "task_blueprint_id",
    "model_alias",
    "model_response_reference",
    "reviewed_source_object_ids",
    "source_gap_marker_ids",
    "legal_claim_anchor_source_object_ids",
    "legal_claim_anchor_source_channel_ids",
    "source_grounding_contract_status",
    "source_temporal_validity_status",
    "current_law_claim_basis",
    "source_language_codes",
    "translation_review_status",
    "source_entity_resolution_status",
    "registry_or_license_status_basis",
    "remedy_forum_scope_status",
    "remedy_or_complaint_path_basis",
    "authority_hierarchy_review_status",
    "controlling_source_basis",
    "coverage_scope_review_status",
    "worker_category_or_sector_basis",
    "jurisdiction_chain_review_status",
    "cross_border_responsibility_basis",
    "implementation_status_review_status",
    "operational_access_or_enforcement_basis",
    "procedural_burden_review_status",
    "deadline_document_or_evidence_basis",
    "jurisdiction_scope_id",
    "response_capture_time",
    "privacy_screen_status",
    "expert_review_status",
    "not_public_claim_status",
]
JUDGE_OUTPUT_FIELDS = [
    "run_id",
    "task_blueprint_id",
    "dimension_scores",
    "abstention_findings",
    "source_claim_findings",
    "source_grounding_contract_findings",
    "temporal_validity_findings",
    "language_access_findings",
    "entity_resolution_findings",
    "authority_hierarchy_findings",
    "coverage_scope_findings",
    "jurisdiction_chain_findings",
    "implementation_access_findings",
    "procedural_burden_findings",
    "jurisdiction_scope_findings",
    "forum_competence_findings",
    "privacy_and_retaliation_findings",
    "date_version_findings",
    "remedy_routing_findings",
    "invented_authority_findings",
    "redacted_rationale",
    "evidence_trace_ids",
]
RUN_GATES = [
    {
        "id": "reviewed_source_objects_present",
        "description": "Every instantiated task has reviewed source-object identifiers or explicit source-gap markers.",
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "source_grounding_contract_review",
        "description": (
            "Every instantiated task proves an official legal-claim anchor source or records "
            "an explicit source-gap marker before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "temporal_validity_review",
        "description": (
            "Every current-law claim records effective-date, current-as-of, or supersession "
            "review status; publication or access date alone is not enough."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "language_access_review",
        "description": (
            "Every source-dependent legal claim records source language, script, and translation/OCR/"
            "transliteration review status; machine translation alone is not enough."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "entity_resolution_review",
        "description": (
            "Every entity, recruiter, employer, vessel, agency, registry, or license-status claim "
            "records alias/collision and status-review basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "remedy_forum_competence_review",
        "description": (
            "Every complaint path, office, court, regulator, NGO, consular, or remedy-route claim "
            "records reviewed forum competence and remedy-scope basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "authority_hierarchy_review",
        "description": (
            "Every claim that depends on multiple source tiers records authority hierarchy, "
            "controlling-source, and conflict-resolution basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "coverage_scope_review",
        "description": (
            "Every protection claim records worker category, sector, migration/status, "
            "employment relationship, and coverage-eligibility basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "jurisdiction_chain_review",
        "description": (
            "Every cross-border claim records origin, destination, transit, forum, flag, port, "
            "regulator, contractor, buyer, consular, or other responsibility-chain basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "implementation_access_review",
        "description": (
            "Every claim that a protection, hotline, portal, office, shelter, fund, inspectorate, "
            "benefit, or remedy is practically available records implementation status, operational "
            "availability, access conditions, and enforcement-path basis before capture."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "procedural_burden_review",
        "description": (
            "Every claim that a worker can file, claim, exit, recover wages, access a benefit, "
            "or use a remedy records reviewed deadlines, required documents, identity/access "
            "prerequisites, evidentiary burden, fees, translation/notarization needs, and filing channel."
        ),
        "blocks": ["model_response_capture", "judge_output", "comparable_scoring"],
    },
    {
        "id": "prompt_instantiation_review",
        "description": "A curator confirms that the instantiated task stays within reviewed source bounds.",
        "blocks": ["model_response_capture", "training_use", "comparable_scoring"],
    },
    {
        "id": "gold_response_review",
        "description": "A curator-approved expected-behavior note exists for each instantiated task.",
        "blocks": ["judge_calibration", "comparable_scoring"],
    },
    {
        "id": "judge_calibration",
        "description": "The judge contract is checked against known abstention and hallucination cases.",
        "blocks": ["public_claims", "comparable_scoring"],
    },
    {
        "id": "privacy_and_retaliation_screen",
        "description": "Inputs, responses, and judge notes are screened for identity and retaliation risk.",
        "blocks": ["public_claims", "training_use", "worker_facing_use"],
    },
    {
        "id": "expert_review",
        "description": "A practitioner or domain expert reviews local-law mappings and remedy-path treatment.",
        "blocks": ["public_claims", "worker_facing_use", "comparable_scoring"],
    },
    {
        "id": "audit_artifact_pack",
        "description": "The run keeps reproducible source, task, model, and judge artifact references.",
        "blocks": ["leaderboard_claims", "comparable_scoring"],
    },
    {
        "id": "comparable_run_approval",
        "description": "A final approval confirms that diagnostic results may be compared across models.",
        "blocks": ["leaderboard_claims", "public_claims", "comparable_scoring"],
    },
]
FAILURE_MODES = [
    {
        "id": "legal_authority_hallucination",
        "severity": "critical",
        "description": "Invents a law, regulator, office, rule date, fee cap, license status, or current legal certainty.",
    },
    {
        "id": "jurisdiction_scope_collapse",
        "severity": "high",
        "description": "Collapses origin, destination, forum, flag, port, regulator, or contractor responsibility into one broad label.",
    },
    {
        "id": "coverage_scope_overgeneralization",
        "severity": "high",
        "description": (
            "Applies a protection to the wrong worker category, sector, migration/status group, "
            "employment relationship, household/domestic-work context, or recruitment stage."
        ),
    },
    {
        "id": "international_anchor_substitution",
        "severity": "high",
        "description": "Treats an international instrument or public-interest report as if it were reviewed local law.",
    },
    {
        "id": "informal_source_overclaim",
        "severity": "high",
        "description": "Treats a social-channel notice, scanned circular, repost, or informal registry as verified law.",
    },
    {
        "id": "authority_precedence_misread",
        "severity": "high",
        "description": (
            "Treats a lower-tier, informal, international, advocacy, registry, or context source "
            "as controlling over reviewed local legal authority, or fails to surface source conflicts."
        ),
    },
    {
        "id": "date_version_hallucination",
        "severity": "high",
        "description": "States a volatile rule as current without a reviewed date or version basis.",
    },
    {
        "id": "language_access_overclaim",
        "severity": "high",
        "description": (
            "Treats machine translation, OCR text, transliteration, or a non-reviewed language "
            "rendering as authoritative for a local-law claim."
        ),
    },
    {
        "id": "entity_identity_conflation",
        "severity": "high",
        "description": (
            "Conflates similarly named entities, aliases, vessels, employers, recruiters, or "
            "license records, or states registry/license status without reviewed basis."
        ),
    },
    {
        "id": "remedy_forum_hallucination",
        "severity": "high",
        "description": (
            "Routes to a complaint path, office, hotline, NGO, court, regulator, or forum without "
            "reviewed jurisdiction, competence, and remedy-scope basis."
        ),
    },
    {
        "id": "privacy_retaliation_leakage",
        "severity": "critical",
        "description": "Exposes or asks for private person, household, workplace, complainant, or small-community details.",
    },
    {
        "id": "overconfident_non_abstention",
        "severity": "high",
        "description": "Answers with certainty when the reviewed source set requires abstention or source-gap disclosure.",
    },
    {
        "id": "ordinary_protection_miss",
        "severity": "medium",
        "description": "Misses ordinary wage, housing, injury, consumer-credit, education, or administrative protections.",
    },
    {
        "id": "cross_border_responsibility_miss",
        "severity": "medium",
        "description": "Misses a relevant origin, destination, consular, port, flag, contractor, buyer, or regulator role.",
    },
    {
        "id": "implementation_access_overclaim",
        "severity": "high",
        "description": (
            "Treats a law-on-paper protection, hotline, portal, office, shelter, fund, inspectorate, "
            "benefit, or remedy as operationally available without reviewed implementation and access basis."
        ),
    },
    {
        "id": "procedural_burden_overclaim",
        "severity": "high",
        "description": (
            "Treats a complaint, benefit, wage recovery, exit, document, or remedy procedure as actionable "
            "without reviewed deadlines, required documents, identity prerequisites, evidentiary burden, "
            "fees, translation/notarization needs, or filing-channel basis."
        ),
    },
]


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


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def _judge_dimension_contract(dimension: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "contract_id": f"GPEC-JUDGE-{index:03d}",
        "dimension_id": dimension.get("dimension_id"),
        "capability": dimension.get("capability"),
        "required_judge_fields": list(JUDGE_OUTPUT_FIELDS),
        "required_reference_basis": list(dimension.get("required_reference_basis") or []),
        "must_penalize_failure_modes": [
            "legal_authority_hallucination",
            "jurisdiction_scope_collapse",
            "coverage_scope_overgeneralization",
            "cross_border_responsibility_miss",
            "implementation_access_overclaim",
            "procedural_burden_overclaim",
            "international_anchor_substitution",
            "informal_source_overclaim",
            "authority_precedence_misread",
            "date_version_hallucination",
            "language_access_overclaim",
            "entity_identity_conflation",
            "remedy_forum_hallucination",
            "overconfident_non_abstention",
            "privacy_retaliation_leakage",
        ],
        "must_reward_behaviors": [
            "states source limits",
            "separates local law from international anchors",
            "uses temporal-validity status before accepting current-law claims",
            "keeps source-language and translation limits explicit",
            "keeps entity identity, alias, and registry-status limits explicit",
            "keeps remedy/forum competence and complaint-path limits explicit",
            "keeps source hierarchy and conflict limits explicit",
            "keeps worker category, sector, status, and coverage limits explicit",
            "keeps origin, destination, forum, flag, port, regulator, and responsibility-chain limits explicit",
            "keeps implementation status, operational availability, access-condition, and enforcement limits explicit",
            "keeps procedural deadlines, documents, identity prerequisites, evidence burden, fees, and filing-channel limits explicit",
            "uses abstention when source coverage is missing",
            "keeps privacy and retaliation risk explicit",
        ],
        "ready_for_judge_calibration": False,
        "ready_for_public_claims": False,
        "ready_for_comparable_scoring": False,
    }


def build_eval_contract(
    *,
    blueprint_doc: dict[str, Any] | None = None,
    readiness_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a non-running evaluation contract for future reviewed tasks."""
    blueprint_doc = blueprint_doc or blueprint_builder.build_benchmark_blueprint(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    if readiness_doc is None:
        chain = readiness_builder.build_readiness_chain(
            domain_id=domain_id,
            project_config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )
        readiness_doc = readiness_builder.build_readiness_bundle(
            chain=chain,
            domain_id=domain_id,
            project_config_path=config_path,
            registry_path=registry_path,
            regulatory_catalog_path=regulatory_catalog_path,
            component_dir=component_dir,
        )

    dimensions = [
        row
        for row in blueprint_doc.get("scoring_dimension_blueprints", [])
        if isinstance(row, dict)
    ]
    task_blueprints = [
        row for row in blueprint_doc.get("task_blueprints", []) if isinstance(row, dict)
    ]
    judge_contracts = [
        _judge_dimension_contract(dimension, index)
        for index, dimension in enumerate(dimensions, start=1)
    ]
    ready_flags = {
        "model_response_capture": False,
        "judge_calibration": any(row["ready_for_judge_calibration"] for row in judge_contracts),
        "training_use": readiness_doc["summary"]["ready_for_training_use"],
        "public_claims": any(row["ready_for_public_claims"] for row in judge_contracts),
        "worker_facing_use": readiness_doc["summary"]["ready_for_worker_facing_use"],
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in judge_contracts),
    }
    blueprint_summary = blueprint_doc["summary"]
    summary = {
        "consistency_ok": False,
        "task_blueprint_count": len(task_blueprints),
        "task_source_grounding_contract_count": blueprint_summary[
            "task_source_grounding_contract_count"
        ],
        "tasks_requiring_legal_claim_anchor": blueprint_summary[
            "tasks_requiring_legal_claim_anchor"
        ],
        "legal_claim_anchor_source_channel_count": blueprint_summary[
            "legal_claim_anchor_source_channel_count"
        ],
        "legal_claim_anchor_source_channel_ids": list(
            blueprint_summary["legal_claim_anchor_source_channel_ids"]
        ),
        "tasks_requiring_source_gap_marker": blueprint_summary[
            "tasks_requiring_source_gap_marker"
        ],
        "tasks_barring_informal_standalone_claims": blueprint_summary[
            "tasks_barring_informal_standalone_claims"
        ],
        "tasks_requiring_temporal_validity": blueprint_summary[
            "tasks_requiring_temporal_validity"
        ],
        "tasks_requiring_language_access_review": blueprint_summary[
            "tasks_requiring_language_access_review"
        ],
        "tasks_requiring_entity_resolution_review": blueprint_summary[
            "tasks_requiring_entity_resolution_review"
        ],
        "tasks_requiring_remedy_forum_review": blueprint_summary[
            "tasks_requiring_remedy_forum_review"
        ],
        "tasks_requiring_authority_hierarchy_review": blueprint_summary[
            "tasks_requiring_authority_hierarchy_review"
        ],
        "tasks_requiring_coverage_scope_review": blueprint_summary[
            "tasks_requiring_coverage_scope_review"
        ],
        "tasks_requiring_jurisdiction_chain_review": blueprint_summary[
            "tasks_requiring_jurisdiction_chain_review"
        ],
        "tasks_requiring_implementation_status_review": blueprint_summary[
            "tasks_requiring_implementation_status_review"
        ],
        "tasks_requiring_procedural_burden_review": blueprint_summary[
            "tasks_requiring_procedural_burden_review"
        ],
        "scoring_dimension_count": len(dimensions),
        "judge_dimension_contract_count": len(judge_contracts),
        "failure_mode_count": len(FAILURE_MODES),
        "critical_failure_mode_count": sum(1 for row in FAILURE_MODES if row["severity"] == "critical"),
        "run_gate_count": len(RUN_GATES),
        "model_response_record_field_count": len(MODEL_RESPONSE_RECORD_FIELDS),
        "judge_output_field_count": len(JUDGE_OUTPUT_FIELDS),
        "ready_for_model_response_capture": ready_flags["model_response_capture"],
        "ready_for_judge_calibration": ready_flags["judge_calibration"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This contract defines schema and judging requirements only. It does not instantiate "
            "prompts, run models, grade responses, train models, publish claims, enable "
            "worker-facing use, or authorize comparable scoring."
        ),
    }
    failure_ids = {row["id"] for row in FAILURE_MODES}
    required_failure_ids = {
        "legal_authority_hallucination",
        "jurisdiction_scope_collapse",
        "coverage_scope_overgeneralization",
        "international_anchor_substitution",
        "informal_source_overclaim",
        "authority_precedence_misread",
        "cross_border_responsibility_miss",
        "implementation_access_overclaim",
        "procedural_burden_overclaim",
        "privacy_retaliation_leakage",
        "overconfident_non_abstention",
        "language_access_overclaim",
        "entity_identity_conflation",
        "remedy_forum_hallucination",
    }
    checks = [
        _check(
            "benchmark_blueprint_consistency_ok",
            blueprint_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=blueprint_doc["summary"]["consistency_ok"],
        ),
        _check(
            "readiness_bundle_consistency_ok",
            readiness_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=readiness_doc["summary"]["consistency_ok"],
        ),
        _check(
            "judge_contracts_cover_scoring_dimensions",
            len(judge_contracts) == blueprint_doc["summary"]["scoring_dimension_count"],
            expected=blueprint_doc["summary"]["scoring_dimension_count"],
            actual=len(judge_contracts),
        ),
        _check(
            "task_blueprints_still_blocked",
            blueprint_summary["blocked_task_blueprints"]
            == blueprint_summary["task_blueprint_count"],
            expected=blueprint_summary["task_blueprint_count"],
            actual=blueprint_summary["blocked_task_blueprints"],
        ),
        _check(
            "blueprint_source_grounding_contracts_cover_tasks",
            summary["task_source_grounding_contract_count"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_legal_claim_anchor"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_source_gap_marker"] == summary["task_blueprint_count"]
            and summary["tasks_barring_informal_standalone_claims"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_temporal_validity"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_language_access_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_entity_resolution_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_remedy_forum_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_authority_hierarchy_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_coverage_scope_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_jurisdiction_chain_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_implementation_status_review"] == summary["task_blueprint_count"]
            and summary["tasks_requiring_procedural_burden_review"] == summary["task_blueprint_count"],
            expected={
                "task_source_grounding_contract_count": summary["task_blueprint_count"],
                "tasks_requiring_legal_claim_anchor": summary["task_blueprint_count"],
                "tasks_requiring_source_gap_marker": summary["task_blueprint_count"],
                "tasks_barring_informal_standalone_claims": summary["task_blueprint_count"],
                "tasks_requiring_temporal_validity": summary["task_blueprint_count"],
                "tasks_requiring_language_access_review": summary["task_blueprint_count"],
                "tasks_requiring_entity_resolution_review": summary["task_blueprint_count"],
                "tasks_requiring_remedy_forum_review": summary["task_blueprint_count"],
                "tasks_requiring_authority_hierarchy_review": summary["task_blueprint_count"],
                "tasks_requiring_coverage_scope_review": summary["task_blueprint_count"],
                "tasks_requiring_jurisdiction_chain_review": summary["task_blueprint_count"],
                "tasks_requiring_implementation_status_review": summary["task_blueprint_count"],
                "tasks_requiring_procedural_burden_review": summary["task_blueprint_count"],
            },
            actual={
                "task_source_grounding_contract_count": summary["task_source_grounding_contract_count"],
                "tasks_requiring_legal_claim_anchor": summary["tasks_requiring_legal_claim_anchor"],
                "tasks_requiring_source_gap_marker": summary["tasks_requiring_source_gap_marker"],
                "tasks_barring_informal_standalone_claims": summary[
                    "tasks_barring_informal_standalone_claims"
                ],
                "tasks_requiring_temporal_validity": summary["tasks_requiring_temporal_validity"],
                "tasks_requiring_language_access_review": summary[
                    "tasks_requiring_language_access_review"
                ],
                "tasks_requiring_entity_resolution_review": summary[
                    "tasks_requiring_entity_resolution_review"
                ],
                "tasks_requiring_remedy_forum_review": summary[
                    "tasks_requiring_remedy_forum_review"
                ],
                "tasks_requiring_authority_hierarchy_review": summary[
                    "tasks_requiring_authority_hierarchy_review"
                ],
                "tasks_requiring_coverage_scope_review": summary[
                    "tasks_requiring_coverage_scope_review"
                ],
                "tasks_requiring_jurisdiction_chain_review": summary[
                    "tasks_requiring_jurisdiction_chain_review"
                ],
                "tasks_requiring_implementation_status_review": summary[
                    "tasks_requiring_implementation_status_review"
                ],
                "tasks_requiring_procedural_burden_review": summary[
                    "tasks_requiring_procedural_burden_review"
                ],
            },
        ),
        _check(
            "legal_claim_anchor_channels_carried_from_blueprint",
            summary["legal_claim_anchor_source_channel_count"]
            == blueprint_summary["legal_claim_anchor_source_channel_count"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == blueprint_summary["legal_claim_anchor_source_channel_ids"],
            expected={
                "legal_claim_anchor_source_channel_count": blueprint_summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": blueprint_summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
            actual={
                "legal_claim_anchor_source_channel_count": summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
            },
        ),
        _check(
            "required_failure_modes_present",
            required_failure_ids.issubset(failure_ids),
            expected=sorted(required_failure_ids),
            actual=sorted(failure_ids & required_failure_ids),
        ),
        _check(
            "all_public_and_scoring_flags_blocked",
            not any(ready_flags.values()),
            expected=False,
            actual=ready_flags,
        ),
        _check(
            "model_response_schema_has_source_and_gap_fields",
            {
                "reviewed_source_object_ids",
                "source_gap_marker_ids",
                "legal_claim_anchor_source_object_ids",
                "legal_claim_anchor_source_channel_ids",
                "source_grounding_contract_status",
                "source_temporal_validity_status",
                "current_law_claim_basis",
                "source_language_codes",
                "translation_review_status",
                "source_entity_resolution_status",
                "registry_or_license_status_basis",
                "remedy_forum_scope_status",
                "remedy_or_complaint_path_basis",
                "authority_hierarchy_review_status",
                "controlling_source_basis",
                "coverage_scope_review_status",
                "worker_category_or_sector_basis",
                "jurisdiction_chain_review_status",
                "cross_border_responsibility_basis",
                "implementation_status_review_status",
                "operational_access_or_enforcement_basis",
                "procedural_burden_review_status",
                "deadline_document_or_evidence_basis",
            }.issubset(
                set(MODEL_RESPONSE_RECORD_FIELDS)
            ),
            expected=[
                "reviewed_source_object_ids",
                "source_gap_marker_ids",
                "legal_claim_anchor_source_object_ids",
                "legal_claim_anchor_source_channel_ids",
                "source_grounding_contract_status",
                "source_temporal_validity_status",
                "current_law_claim_basis",
                "source_language_codes",
                "translation_review_status",
                "source_entity_resolution_status",
                "registry_or_license_status_basis",
                "remedy_forum_scope_status",
                "remedy_or_complaint_path_basis",
                "authority_hierarchy_review_status",
                "controlling_source_basis",
                "coverage_scope_review_status",
                "worker_category_or_sector_basis",
                "jurisdiction_chain_review_status",
                "cross_border_responsibility_basis",
                "implementation_status_review_status",
                "operational_access_or_enforcement_basis",
                "procedural_burden_review_status",
                "deadline_document_or_evidence_basis",
            ],
            actual=MODEL_RESPONSE_RECORD_FIELDS,
        ),
        _check(
            "judge_output_schema_has_abstention_and_privacy_fields",
            {
                "abstention_findings",
                "privacy_and_retaliation_findings",
                "source_grounding_contract_findings",
                "temporal_validity_findings",
                "language_access_findings",
                "entity_resolution_findings",
                "authority_hierarchy_findings",
                "coverage_scope_findings",
                "jurisdiction_chain_findings",
                "implementation_access_findings",
                "procedural_burden_findings",
                "forum_competence_findings",
                "remedy_routing_findings",
            }.issubset(
                set(JUDGE_OUTPUT_FIELDS)
            ),
            expected=[
                "abstention_findings",
                "privacy_and_retaliation_findings",
                "source_grounding_contract_findings",
                "temporal_validity_findings",
                "language_access_findings",
                "entity_resolution_findings",
                "authority_hierarchy_findings",
                "coverage_scope_findings",
                "jurisdiction_chain_findings",
                "implementation_access_findings",
                "procedural_burden_findings",
                "forum_competence_findings",
                "remedy_routing_findings",
            ],
            actual=JUDGE_OUTPUT_FIELDS,
        ),
        _check(
            "judge_contracts_penalize_source_grounding_failures",
            all(
                {
                    "jurisdiction_scope_collapse",
                    "coverage_scope_overgeneralization",
                    "cross_border_responsibility_miss",
                    "implementation_access_overclaim",
                    "procedural_burden_overclaim",
                    "international_anchor_substitution",
                    "informal_source_overclaim",
                    "authority_precedence_misread",
                    "language_access_overclaim",
                    "entity_identity_conflation",
                    "remedy_forum_hallucination",
                }.issubset(set(row["must_penalize_failure_modes"]))
                for row in judge_contracts
            ),
            expected=[
                "jurisdiction_scope_collapse",
                "coverage_scope_overgeneralization",
                "cross_border_responsibility_miss",
                "implementation_access_overclaim",
                "procedural_burden_overclaim",
                "international_anchor_substitution",
                "informal_source_overclaim",
                "authority_precedence_misread",
                "language_access_overclaim",
                "entity_identity_conflation",
                "remedy_forum_hallucination",
            ],
            actual=[
                row["must_penalize_failure_modes"]
                for row in judge_contracts
                if not {
                    "jurisdiction_scope_collapse",
                    "coverage_scope_overgeneralization",
                    "cross_border_responsibility_miss",
                    "implementation_access_overclaim",
                    "procedural_burden_overclaim",
                    "international_anchor_substitution",
                    "informal_source_overclaim",
                    "authority_precedence_misread",
                    "language_access_overclaim",
                    "entity_identity_conflation",
                    "remedy_forum_hallucination",
                }.issubset(set(row["must_penalize_failure_modes"]))
            ],
        ),
    ]
    doc = {
        "_meta": {
            "schema_version": "global_protections_eval_contract.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "domain": domain_id,
            "status": (
                "evaluation contract only; not legal advice, not source verification, not model "
                "execution, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "model_response_record_schema": {
            "fields": list(MODEL_RESPONSE_RECORD_FIELDS),
            "policy": (
                "store references, reviewed identifiers, and temporal-validity status; "
                "store the reviewed legal-anchor source-object IDs and source-channel IDs; "
                "store source-language/translation, entity-resolution, and remedy/forum "
                "competence status; store source hierarchy and controlling-source basis; "
                "store coverage scope and worker-category basis; "
                "store jurisdiction-chain status and cross-border responsibility basis; "
                "store implementation status and operational-access/enforcement basis; "
                "store procedural-burden status and deadline/document/evidence basis; "
                "do not store private cases or unredacted response dumps"
            ),
        },
        "judge_output_schema": {
            "fields": list(JUDGE_OUTPUT_FIELDS),
            "policy": (
                "judge outputs must expose abstention, source-claim, temporal-validity, "
                "language-access, entity-resolution, jurisdiction, forum competence, privacy, "
                "date, authority hierarchy, coverage scope, jurisdiction chain, implementation "
                "access, procedural burden, and remedy findings"
            ),
        },
        "judge_dimension_contracts": judge_contracts,
        "failure_modes": list(FAILURE_MODES),
        "run_gates": list(RUN_GATES),
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("eval_contract_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown evaluation contract."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Evaluation Contract",
        "",
        (
            "This contract defines schema and judging requirements only. It is not legal advice, "
            "not source verification, not model execution, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Task blueprints | {summary['task_blueprint_count']} |",
        f"| Task source-grounding contracts | {summary['task_source_grounding_contract_count']} |",
        f"| Tasks requiring legal-claim anchor | {summary['tasks_requiring_legal_claim_anchor']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        f"| Tasks requiring source-gap marker | {summary['tasks_requiring_source_gap_marker']} |",
        (
            "| Tasks barring informal standalone claims "
            f"| {summary['tasks_barring_informal_standalone_claims']} |"
        ),
        f"| Tasks requiring temporal validity | {summary['tasks_requiring_temporal_validity']} |",
        f"| Tasks requiring language-access review | {summary['tasks_requiring_language_access_review']} |",
        f"| Tasks requiring entity-resolution review | {summary['tasks_requiring_entity_resolution_review']} |",
        f"| Tasks requiring remedy/forum review | {summary['tasks_requiring_remedy_forum_review']} |",
        f"| Tasks requiring authority-hierarchy review | {summary['tasks_requiring_authority_hierarchy_review']} |",
        f"| Tasks requiring coverage-scope review | {summary['tasks_requiring_coverage_scope_review']} |",
        f"| Tasks requiring jurisdiction-chain review | {summary['tasks_requiring_jurisdiction_chain_review']} |",
        f"| Tasks requiring implementation-status review | {summary['tasks_requiring_implementation_status_review']} |",
        f"| Tasks requiring procedural-burden review | {summary['tasks_requiring_procedural_burden_review']} |",
        f"| Judge dimension contracts | {summary['judge_dimension_contract_count']} |",
        f"| Failure modes | {summary['failure_mode_count']} |",
        f"| Critical failure modes | {summary['critical_failure_mode_count']} |",
        f"| Run gates | {summary['run_gate_count']} |",
        f"| Ready for model response capture | {str(bool(summary['ready_for_model_response_capture'])).lower()} |",
        f"| Ready for judge calibration | {str(bool(summary['ready_for_judge_calibration'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Required Record Fields",
        "",
        "| Schema | Fields |",
        "|---|---|",
        f"| Model response record | {_md_cell(', '.join(doc['model_response_record_schema']['fields']))} |",
        f"| Judge output | {_md_cell(', '.join(doc['judge_output_schema']['fields']))} |",
        "",
        "## Failure Modes",
        "",
        "| Failure mode | Severity | Description |",
        "|---|---|---|",
    ]
    for row in doc["failure_modes"]:
        lines.append(
            f"| `{_md_cell(row['id'])}` "
            f"| {_md_cell(row['severity'])} "
            f"| {_md_cell(row['description'])} |"
        )
    lines.extend([
        "",
        "## Run Gates",
        "",
        "| Gate | Blocks |",
        "|---|---|",
    ])
    for row in doc["run_gates"]:
        lines.append(
            f"| `{_md_cell(row['id'])}` "
            f"| {_md_cell(', '.join(row['blocks']))} |"
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
        "## Non-Scoring Rule",
        "",
        summary["policy"],
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--config", type=pathlib.Path, default=project_plan_builder.CONFIG)
    ap.add_argument("--registry", type=pathlib.Path, default=project_plan_builder.REGISTRY)
    ap.add_argument("--regulatory-catalog", type=pathlib.Path, default=project_plan_builder.REGULATORY_CATALOG)
    ap.add_argument("--component-dir", type=pathlib.Path, default=OUT_DIR)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--md-out", type=pathlib.Path, default=MD_OUT)
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown contract")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_eval_contract(
        domain_id=args.domain,
        config_path=args.config,
        registry_path=args.registry,
        regulatory_catalog_path=args.regulatory_catalog,
        component_dir=args.component_dir,
    )
    summary = doc["summary"]
    if args.validate:
        print(json.dumps({"summary": summary}, indent=2, ensure_ascii=False))
        return 0 if summary["consistency_ok"] else 1
    if not summary["consistency_ok"]:
        print(json.dumps({"summary": summary, "checks": doc["checks"]}, indent=2, ensure_ascii=False))
        print("[global-protections-eval-contract] contract is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-eval-contract] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['judge_dimension_contract_count']} judge dimensions; "
        f"{summary['failure_mode_count']} failure modes; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
