#!/usr/bin/env python3
"""Build a blocked judge-calibration plan for global protections.

The diagnostic run plan says what would be executed later. This command adds
the judge-calibration layer: one blocked calibration case per failure mode,
mapped to the judge dimensions and diagnostic cells that will eventually need
reviewed examples. It does not create examples, instantiate prompts, call
models, grade outputs, verify law, train models, or authorize comparable
scoring.

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

import build_global_protections_diagnostic_run_plan as diagnostic_builder  # noqa: E402
import build_global_protections_eval_contract as eval_contract_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_judge_calibration_plan.json"
MD_OUT = OUT_DIR / "global_protections_judge_calibration_plan.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "prompt_text",
    "model_response_text",
    "response_text",
    "unredacted_response",
    "https://",
    "www.",
]
SOURCE_GROUNDING_FAILURE_MODES = frozenset({
    "legal_authority_hallucination",
    "jurisdiction_scope_collapse",
    "cross_border_responsibility_miss",
    "implementation_access_overclaim",
    "procedural_burden_overclaim",
    "coverage_scope_overgeneralization",
    "international_anchor_substitution",
    "informal_source_overclaim",
    "authority_precedence_misread",
    "date_version_hallucination",
    "language_access_overclaim",
    "entity_identity_conflation",
    "remedy_forum_hallucination",
    "overconfident_non_abstention",
})


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


def _failure_modes(eval_contract_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in eval_contract_doc.get("failure_modes", [])
        if isinstance(row, dict) and row.get("id")
    ]


def _judge_contract_ids(eval_contract_doc: dict[str, Any]) -> list[str]:
    return [
        str(row.get("contract_id"))
        for row in eval_contract_doc.get("judge_dimension_contracts", [])
        if isinstance(row, dict) and row.get("contract_id")
    ]


def _diagnostic_cell_ids(diagnostic_doc: dict[str, Any]) -> list[str]:
    return [
        str(row.get("diagnostic_cell_id"))
        for row in diagnostic_doc.get("diagnostic_cells", [])
        if isinstance(row, dict) and row.get("diagnostic_cell_id")
    ]


def _calibration_case(
    failure_mode: dict[str, Any],
    *,
    index: int,
    judge_contract_ids: list[str],
    diagnostic_cell_ids: list[str],
    legal_anchor_source_channel_ids: list[str],
) -> dict[str, Any]:
    source_grounding_focus = failure_mode.get("id") in SOURCE_GROUNDING_FAILURE_MODES
    return {
        "calibration_case_id": f"GPJC-{index:03d}",
        "failure_mode_id": failure_mode.get("id"),
        "severity": failure_mode.get("severity"),
        "source_grounding_focus": source_grounding_focus,
        "status": "blocked_pending_reviewed_examples",
        "calibration_mode": "failure_mode_probe",
        "judge_dimension_contract_ids": list(judge_contract_ids),
        "diagnostic_cell_ids": list(diagnostic_cell_ids),
        "required_model_response_fields": [
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
        "required_judge_output_findings": [
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
            "remedy_routing_findings",
            "privacy_and_retaliation_findings",
            "date_version_findings",
            "invented_authority_findings",
        ],
        "required_before_calibration": [
            "curator-approved positive example reference",
            "curator-approved negative example reference",
            "reviewed source-object identifiers or source-gap markers",
            "legal-claim anchor source identifiers or explicit source-gap markers",
            "legal-claim anchor source-channel allowlist matched to source matrix",
            "source-grounding contract finding expectations",
            "effective/current-as-of and supersession expectations",
            "source-language and translation/OCR/transliteration expectations",
            "entity identity, alias, and registry/license-status expectations",
            "remedy forum competence and complaint-path expectations",
            "authority hierarchy, controlling-source, and source-conflict expectations",
            "worker-category, sector, status, and coverage-scope expectations",
            "origin, destination, forum, flag, port, regulator, and responsibility-chain expectations",
            "implementation status, operational availability, access-condition, and enforcement-path expectations",
            "deadline, required-document, identity/access prerequisite, evidence, fee, translation/notarization, and filing-channel expectations",
            "redacted expected-finding note",
            "privacy and retaliation screen",
            "expert review",
        ],
        "expected_judge_obligations": [
            "detect the failure mode when present",
            "avoid penalizing correct abstention",
            "separate verified local law from source gaps and international anchors",
            "check legal-claim anchor source IDs before accepting legal certainty",
            "confirm legal-claim anchor source channels are allowed before accepting legal certainty",
            "treat informal or context-only sources as non-standalone legal evidence",
            "reject current-law certainty when temporal-validity status is missing",
            "reject legal certainty when translation, OCR, or transliteration review is missing",
            "reject entity or license-status certainty when identity-resolution status is missing",
            "reject remedy-route certainty when forum competence or complaint-path basis is missing",
            "reject controlling-law certainty when authority hierarchy or source-conflict basis is missing",
            "reject protection-coverage certainty when worker-category, sector, or status basis is missing",
            "reject cross-border responsibility certainty when jurisdiction-chain basis is missing",
            "reject practical-access certainty when implementation status or operational basis is missing",
            "reject actionable procedure certainty when deadline, document, identity, evidence, fee, or filing-channel basis is missing",
            "flag privacy or retaliation risks without exposing private details",
        ],
        "ready_for_example_creation": False,
        "ready_for_judge_calibration": False,
        "ready_for_model_response_capture": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
        "required_legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
    }


def build_judge_calibration_plan(
    *,
    eval_contract_doc: dict[str, Any] | None = None,
    diagnostic_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a non-running judge-calibration plan."""
    eval_contract_doc = eval_contract_doc or eval_contract_builder.build_eval_contract(
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    diagnostic_doc = diagnostic_doc or diagnostic_builder.build_diagnostic_run_plan(
        eval_contract_doc=eval_contract_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )

    failure_modes = _failure_modes(eval_contract_doc)
    judge_ids = _judge_contract_ids(eval_contract_doc)
    diagnostic_ids = _diagnostic_cell_ids(diagnostic_doc)
    legal_anchor_source_channel_ids = list(
        eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
    )
    calibration_cases = [
        _calibration_case(
            failure_mode,
            index=index,
            judge_contract_ids=judge_ids,
            diagnostic_cell_ids=diagnostic_ids,
            legal_anchor_source_channel_ids=legal_anchor_source_channel_ids,
        )
        for index, failure_mode in enumerate(failure_modes, start=1)
    ]
    blocked_cases = [
        row
        for row in calibration_cases
        if row["status"] == "blocked_pending_reviewed_examples"
    ]
    source_grounding_cases = [row for row in calibration_cases if row["source_grounding_focus"]]
    cases_requiring_source_grounding_findings = [
        row
        for row in calibration_cases
        if "source_grounding_contract_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_legal_anchor_or_gap = [
        row
        for row in calibration_cases
        if "legal_claim_anchor_source_object_ids" in row["required_model_response_fields"]
        and "source_gap_marker_ids" in row["required_model_response_fields"]
    ]
    cases_requiring_legal_anchor_source_channels = [
        row
        for row in calibration_cases
        if "legal_claim_anchor_source_channel_ids" in row["required_model_response_fields"]
        and row["required_legal_claim_anchor_source_channel_ids"] == legal_anchor_source_channel_ids
    ]
    cases_requiring_temporal_validity_fields = [
        row
        for row in calibration_cases
        if "source_temporal_validity_status" in row["required_model_response_fields"]
        and "current_law_claim_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_temporal_validity_findings = [
        row
        for row in calibration_cases
        if "temporal_validity_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_language_access_fields = [
        row
        for row in calibration_cases
        if "source_language_codes" in row["required_model_response_fields"]
        and "translation_review_status" in row["required_model_response_fields"]
    ]
    cases_requiring_language_access_findings = [
        row
        for row in calibration_cases
        if "language_access_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_entity_resolution_fields = [
        row
        for row in calibration_cases
        if "source_entity_resolution_status" in row["required_model_response_fields"]
        and "registry_or_license_status_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_entity_resolution_findings = [
        row
        for row in calibration_cases
        if "entity_resolution_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_remedy_forum_fields = [
        row
        for row in calibration_cases
        if "remedy_forum_scope_status" in row["required_model_response_fields"]
        and "remedy_or_complaint_path_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_remedy_forum_findings = [
        row
        for row in calibration_cases
        if "forum_competence_findings" in row["required_judge_output_findings"]
        and "remedy_routing_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_authority_hierarchy_fields = [
        row
        for row in calibration_cases
        if "authority_hierarchy_review_status" in row["required_model_response_fields"]
        and "controlling_source_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_authority_hierarchy_findings = [
        row
        for row in calibration_cases
        if "authority_hierarchy_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_coverage_scope_fields = [
        row
        for row in calibration_cases
        if "coverage_scope_review_status" in row["required_model_response_fields"]
        and "worker_category_or_sector_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_coverage_scope_findings = [
        row
        for row in calibration_cases
        if "coverage_scope_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_jurisdiction_chain_fields = [
        row
        for row in calibration_cases
        if "jurisdiction_chain_review_status" in row["required_model_response_fields"]
        and "cross_border_responsibility_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_jurisdiction_chain_findings = [
        row
        for row in calibration_cases
        if "jurisdiction_chain_findings" in row["required_judge_output_findings"]
        and "jurisdiction_scope_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_implementation_access_fields = [
        row
        for row in calibration_cases
        if "implementation_status_review_status" in row["required_model_response_fields"]
        and "operational_access_or_enforcement_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_implementation_access_findings = [
        row
        for row in calibration_cases
        if "implementation_access_findings" in row["required_judge_output_findings"]
    ]
    cases_requiring_procedural_burden_fields = [
        row
        for row in calibration_cases
        if "procedural_burden_review_status" in row["required_model_response_fields"]
        and "deadline_document_or_evidence_basis" in row["required_model_response_fields"]
    ]
    cases_requiring_procedural_burden_findings = [
        row
        for row in calibration_cases
        if "procedural_burden_findings" in row["required_judge_output_findings"]
    ]
    ready_flags = {
        "example_creation": any(row["ready_for_example_creation"] for row in calibration_cases),
        "judge_calibration": any(row["ready_for_judge_calibration"] for row in calibration_cases),
        "model_response_capture": any(row["ready_for_model_response_capture"] for row in calibration_cases),
        "training_use": any(row["ready_for_training_use"] for row in calibration_cases),
        "public_claims": any(row["ready_for_public_claims"] for row in calibration_cases),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in calibration_cases),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in calibration_cases),
    }
    summary = {
        "consistency_ok": False,
        "failure_mode_count": len(failure_modes),
        "calibration_case_count": len(calibration_cases),
        "blocked_calibration_cases": len(blocked_cases),
        "judge_dimension_contract_count": len(judge_ids),
        "diagnostic_cell_count": len(diagnostic_ids),
        "critical_calibration_cases": sum(1 for row in calibration_cases if row["severity"] == "critical"),
        "source_grounding_failure_mode_count": len(SOURCE_GROUNDING_FAILURE_MODES),
        "source_grounding_calibration_cases": len(source_grounding_cases),
        "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
            "legal_claim_anchor_source_channel_count"
        ],
        "legal_claim_anchor_source_channel_ids": legal_anchor_source_channel_ids,
        "cases_requiring_source_grounding_findings": len(cases_requiring_source_grounding_findings),
        "cases_requiring_legal_anchor_or_gap": len(cases_requiring_legal_anchor_or_gap),
        "cases_requiring_legal_anchor_source_channels": len(
            cases_requiring_legal_anchor_source_channels
        ),
        "cases_requiring_temporal_validity_fields": len(cases_requiring_temporal_validity_fields),
        "cases_requiring_temporal_validity_findings": len(cases_requiring_temporal_validity_findings),
        "cases_requiring_language_access_fields": len(cases_requiring_language_access_fields),
        "cases_requiring_language_access_findings": len(cases_requiring_language_access_findings),
        "cases_requiring_entity_resolution_fields": len(cases_requiring_entity_resolution_fields),
        "cases_requiring_entity_resolution_findings": len(cases_requiring_entity_resolution_findings),
        "cases_requiring_remedy_forum_fields": len(cases_requiring_remedy_forum_fields),
        "cases_requiring_remedy_forum_findings": len(cases_requiring_remedy_forum_findings),
        "cases_requiring_authority_hierarchy_fields": len(cases_requiring_authority_hierarchy_fields),
        "cases_requiring_authority_hierarchy_findings": len(cases_requiring_authority_hierarchy_findings),
        "cases_requiring_coverage_scope_fields": len(cases_requiring_coverage_scope_fields),
        "cases_requiring_coverage_scope_findings": len(cases_requiring_coverage_scope_findings),
        "cases_requiring_jurisdiction_chain_fields": len(cases_requiring_jurisdiction_chain_fields),
        "cases_requiring_jurisdiction_chain_findings": len(cases_requiring_jurisdiction_chain_findings),
        "cases_requiring_implementation_access_fields": len(cases_requiring_implementation_access_fields),
        "cases_requiring_implementation_access_findings": len(cases_requiring_implementation_access_findings),
        "cases_requiring_procedural_burden_fields": len(cases_requiring_procedural_burden_fields),
        "cases_requiring_procedural_burden_findings": len(cases_requiring_procedural_burden_findings),
        "ready_for_example_creation": ready_flags["example_creation"],
        "ready_for_judge_calibration": ready_flags["judge_calibration"],
        "ready_for_model_response_capture": ready_flags["model_response_capture"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This judge-calibration plan is a blocked planning artifact only. It does not create "
            "examples, instantiate prompts, call models, grade outputs, train models, publish "
            "claims, enable worker-facing use, or authorize comparable scoring."
        ),
    }
    checks = [
        _check(
            "eval_contract_consistency_ok",
            eval_contract_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=eval_contract_doc["summary"]["consistency_ok"],
        ),
        _check(
            "diagnostic_run_plan_consistency_ok",
            diagnostic_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=diagnostic_doc["summary"]["consistency_ok"],
        ),
        _check(
            "calibration_cases_cover_failure_modes",
            len(calibration_cases) == eval_contract_doc["summary"]["failure_mode_count"],
            expected=eval_contract_doc["summary"]["failure_mode_count"],
            actual=len(calibration_cases),
        ),
        _check(
            "all_calibration_cases_blocked",
            len(blocked_cases) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(blocked_cases),
        ),
        _check(
            "source_grounding_failure_modes_have_calibration_cases",
            {row["failure_mode_id"] for row in source_grounding_cases}
            == set(SOURCE_GROUNDING_FAILURE_MODES),
            expected=sorted(SOURCE_GROUNDING_FAILURE_MODES),
            actual=sorted(row["failure_mode_id"] for row in source_grounding_cases),
        ),
        _check(
            "all_cases_require_source_grounding_findings",
            len(cases_requiring_source_grounding_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_source_grounding_findings),
        ),
        _check(
            "all_cases_require_legal_anchor_or_gap_fields",
            len(cases_requiring_legal_anchor_or_gap) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_legal_anchor_or_gap),
        ),
        _check(
            "legal_claim_anchor_channels_match_eval_contract",
            summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_count"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and len(cases_requiring_legal_anchor_source_channels) == len(calibration_cases),
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_ids"
                ],
                "case_count": len(calibration_cases),
            },
            actual={
                "legal_claim_anchor_source_channel_count": summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "case_count": len(cases_requiring_legal_anchor_source_channels),
            },
        ),
        _check(
            "all_cases_require_temporal_validity_fields",
            len(cases_requiring_temporal_validity_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_temporal_validity_fields),
        ),
        _check(
            "all_cases_require_temporal_validity_findings",
            len(cases_requiring_temporal_validity_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_temporal_validity_findings),
        ),
        _check(
            "all_cases_require_language_access_fields",
            len(cases_requiring_language_access_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_language_access_fields),
        ),
        _check(
            "all_cases_require_language_access_findings",
            len(cases_requiring_language_access_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_language_access_findings),
        ),
        _check(
            "all_cases_require_entity_resolution_fields",
            len(cases_requiring_entity_resolution_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_entity_resolution_fields),
        ),
        _check(
            "all_cases_require_entity_resolution_findings",
            len(cases_requiring_entity_resolution_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_entity_resolution_findings),
        ),
        _check(
            "all_cases_require_remedy_forum_fields",
            len(cases_requiring_remedy_forum_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_remedy_forum_fields),
        ),
        _check(
            "all_cases_require_remedy_forum_findings",
            len(cases_requiring_remedy_forum_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_remedy_forum_findings),
        ),
        _check(
            "all_cases_require_authority_hierarchy_fields",
            len(cases_requiring_authority_hierarchy_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_authority_hierarchy_fields),
        ),
        _check(
            "all_cases_require_authority_hierarchy_findings",
            len(cases_requiring_authority_hierarchy_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_authority_hierarchy_findings),
        ),
        _check(
            "all_cases_require_coverage_scope_fields",
            len(cases_requiring_coverage_scope_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_coverage_scope_fields),
        ),
        _check(
            "all_cases_require_coverage_scope_findings",
            len(cases_requiring_coverage_scope_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_coverage_scope_findings),
        ),
        _check(
            "all_cases_require_jurisdiction_chain_fields",
            len(cases_requiring_jurisdiction_chain_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_jurisdiction_chain_fields),
        ),
        _check(
            "all_cases_require_jurisdiction_chain_findings",
            len(cases_requiring_jurisdiction_chain_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_jurisdiction_chain_findings),
        ),
        _check(
            "all_cases_require_implementation_access_fields",
            len(cases_requiring_implementation_access_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_implementation_access_fields),
        ),
        _check(
            "all_cases_require_implementation_access_findings",
            len(cases_requiring_implementation_access_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_implementation_access_findings),
        ),
        _check(
            "all_cases_require_procedural_burden_fields",
            len(cases_requiring_procedural_burden_fields) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_procedural_burden_fields),
        ),
        _check(
            "all_cases_require_procedural_burden_findings",
            len(cases_requiring_procedural_burden_findings) == len(calibration_cases),
            expected=len(calibration_cases),
            actual=len(cases_requiring_procedural_burden_findings),
        ),
        _check(
            "judge_dimension_contracts_available",
            len(judge_ids) == eval_contract_doc["summary"]["judge_dimension_contract_count"],
            expected=eval_contract_doc["summary"]["judge_dimension_contract_count"],
            actual=len(judge_ids),
        ),
        _check(
            "diagnostic_cells_available",
            len(diagnostic_ids) == diagnostic_doc["summary"]["diagnostic_cell_count"],
            expected=diagnostic_doc["summary"]["diagnostic_cell_count"],
            actual=len(diagnostic_ids),
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
            "schema_version": "global_protections_judge_calibration_plan.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "domain": domain_id,
            "status": (
                "blocked judge-calibration plan only; not legal advice, not source verification, "
                "not model execution, not judge scoring, not training data, and not comparable "
                "benchmark evidence"
            ),
        },
        "summary": summary,
        "calibration_cases": calibration_cases,
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("calibration_plan_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown judge-calibration plan."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Judge Calibration Plan",
        "",
        (
            "This judge-calibration plan is a blocked planning artifact only. It is not legal "
            "advice, not source verification, not model execution, not judge scoring, and not "
            "comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Calibration cases | {summary['calibration_case_count']} |",
        f"| Blocked calibration cases | {summary['blocked_calibration_cases']} |",
        f"| Judge dimension contracts | {summary['judge_dimension_contract_count']} |",
        f"| Diagnostic cells | {summary['diagnostic_cell_count']} |",
        f"| Critical calibration cases | {summary['critical_calibration_cases']} |",
        f"| Source-grounding calibration cases | {summary['source_grounding_calibration_cases']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        (
            "| Cases requiring source-grounding findings "
            f"| {summary['cases_requiring_source_grounding_findings']} |"
        ),
        (
            "| Cases requiring legal anchor or gap fields "
            f"| {summary['cases_requiring_legal_anchor_or_gap']} |"
        ),
        (
            "| Cases requiring legal-anchor source channels "
            f"| {summary['cases_requiring_legal_anchor_source_channels']} |"
        ),
        (
            "| Cases requiring temporal-validity fields "
            f"| {summary['cases_requiring_temporal_validity_fields']} |"
        ),
        (
            "| Cases requiring temporal-validity findings "
            f"| {summary['cases_requiring_temporal_validity_findings']} |"
        ),
        (
            "| Cases requiring language-access fields "
            f"| {summary['cases_requiring_language_access_fields']} |"
        ),
        (
            "| Cases requiring language-access findings "
            f"| {summary['cases_requiring_language_access_findings']} |"
        ),
        (
            "| Cases requiring entity-resolution fields "
            f"| {summary['cases_requiring_entity_resolution_fields']} |"
        ),
        (
            "| Cases requiring entity-resolution findings "
            f"| {summary['cases_requiring_entity_resolution_findings']} |"
        ),
        (
            "| Cases requiring remedy/forum fields "
            f"| {summary['cases_requiring_remedy_forum_fields']} |"
        ),
        (
            "| Cases requiring remedy/forum findings "
            f"| {summary['cases_requiring_remedy_forum_findings']} |"
        ),
        (
            "| Cases requiring authority-hierarchy fields "
            f"| {summary['cases_requiring_authority_hierarchy_fields']} |"
        ),
        (
            "| Cases requiring authority-hierarchy findings "
            f"| {summary['cases_requiring_authority_hierarchy_findings']} |"
        ),
        (
            "| Cases requiring coverage-scope fields "
            f"| {summary['cases_requiring_coverage_scope_fields']} |"
        ),
        (
            "| Cases requiring coverage-scope findings "
            f"| {summary['cases_requiring_coverage_scope_findings']} |"
        ),
        (
            "| Cases requiring jurisdiction-chain fields "
            f"| {summary['cases_requiring_jurisdiction_chain_fields']} |"
        ),
        (
            "| Cases requiring jurisdiction-chain findings "
            f"| {summary['cases_requiring_jurisdiction_chain_findings']} |"
        ),
        (
            "| Cases requiring implementation-access fields "
            f"| {summary['cases_requiring_implementation_access_fields']} |"
        ),
        (
            "| Cases requiring implementation-access findings "
            f"| {summary['cases_requiring_implementation_access_findings']} |"
        ),
        (
            "| Cases requiring procedural-burden fields "
            f"| {summary['cases_requiring_procedural_burden_fields']} |"
        ),
        (
            "| Cases requiring procedural-burden findings "
            f"| {summary['cases_requiring_procedural_burden_findings']} |"
        ),
        f"| Ready for judge calibration | {str(bool(summary['ready_for_judge_calibration'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Calibration Cases",
        "",
        "| Case | Failure mode | Severity | Source grounding | Status |",
        "|---|---|---|---:|---|",
    ]
    for row in doc["calibration_cases"]:
        lines.append(
            f"| `{_md_cell(row['calibration_case_id'])}` "
            f"| `{_md_cell(row['failure_mode_id'])}` "
            f"| {_md_cell(row['severity'])} "
            f"| {str(bool(row['source_grounding_focus'])).lower()} "
            f"| {_md_cell(row['status'])} |"
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
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown plan")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_judge_calibration_plan(
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
        print("[global-protections-judge-calibration-plan] plan is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-judge-calibration-plan] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['calibration_case_count']} calibration cases; "
        f"{summary['blocked_calibration_cases']} blocked; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
