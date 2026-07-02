#!/usr/bin/env python3
"""Build the transition gate for the global protections benchmark chain.

This command composes the current source, blueprint, evaluation, diagnostic,
and calibration layers into a go/no-go matrix for future transitions. It keeps
each transition blocked until the required reviewed source, privacy, expert,
and calibration evidence exists.

It does not fetch sources, verify law, instantiate prompts, call models, grade
outputs, train models, publish claims, enable worker-facing use, or authorize
comparable scoring.

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
import build_global_protections_diagnostic_run_plan as diagnostic_builder  # noqa: E402
import build_global_protections_eval_contract as eval_contract_builder  # noqa: E402
import build_global_protections_judge_calibration_plan as calibration_builder  # noqa: E402
import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402
import build_global_protections_source_channel_review_packet as source_review_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_transition_gate.json"
MD_OUT = OUT_DIR / "global_protections_transition_gate.md"
DEFAULT_DOMAIN = readiness_builder.DEFAULT_DOMAIN

DISALLOWED_TERMS = [
    "Synthetic composite:",
    "prompt_family_sketches",
    "candidate_url",
    "source_url",
    "raw_text",
    "case_text",
    "prompt_text",
    "response_text",
    "unredacted_response",
    "https://",
    "www.",
]

TRANSITION_DEFINITIONS = [
    {
        "id": "source_review_to_manifest_promotion",
        "from": "blank source-channel review rows",
        "to": "grounding manifest source objects",
        "temporal_validity_gate": True,
        "language_access_gate": True,
        "entity_resolution_gate": True,
        "remedy_forum_gate": True,
        "authority_hierarchy_gate": True,
        "coverage_scope_gate": True,
        "jurisdiction_chain_gate": True,
        "implementation_access_gate": True,
        "procedural_burden_gate": True,
        "blocks": ["manifest_promotion", "prompt_instantiation", "comparable_scoring"],
        "required_evidence": [
            "all promoted rows have public source metadata",
            "effective/current-as-of or supersession fields reviewed where legal-claim support is proposed",
            "source language, script, and translation/OCR/transliteration status reviewed",
            "entity identity, alias, and registry/license status reviewed where entity claims are proposed",
            "forum competence and remedy-path scope reviewed where remedy routing is proposed",
            "authority tier and controlling-source basis reviewed where source conflicts are proposed",
            "worker category, sector, status, and coverage-scope basis reviewed where protections are proposed",
            "origin, destination, forum, flag, port, regulator, and responsibility-chain basis reviewed where cross-border claims are proposed",
            "implementation status, operational availability, access-condition, and enforcement-path basis reviewed where practical access is proposed",
            "deadlines, required documents, identity/access prerequisites, evidence burden, fees, translation/notarization, and filing-channel basis reviewed where procedures are proposed",
            "archive status is complete",
            "privacy review passed",
            "expert review passed",
        ],
    },
    {
        "id": "manifest_to_prompt_instantiation",
        "from": "reviewed source objects",
        "to": "source-bounded task instances",
        "source_grounding_gate": True,
        "temporal_validity_gate": True,
        "language_access_gate": True,
        "entity_resolution_gate": True,
        "remedy_forum_gate": True,
        "authority_hierarchy_gate": True,
        "coverage_scope_gate": True,
        "jurisdiction_chain_gate": True,
        "implementation_access_gate": True,
        "procedural_burden_gate": True,
        "blocks": ["prompt_generation", "model_response_capture", "comparable_scoring"],
        "required_evidence": [
            "jurisdiction and forum scope resolved",
            "local-law source objects cover every claim",
            "legal-claim anchor source identifiers recorded",
            "source-gap markers exist where abstention is expected",
            "source-grounding contract status planned",
            "temporal-validity contract status planned",
            "language-access contract status planned",
            "entity-resolution contract status planned",
            "remedy/forum competence contract status planned",
            "authority-hierarchy contract status planned",
            "coverage-scope contract status planned",
            "jurisdiction-chain contract status planned",
            "implementation-access contract status planned",
            "procedural-burden contract status planned",
            "prompt-instantiation review passed",
        ],
    },
    {
        "id": "prompt_to_diagnostic_capture",
        "from": "source-bounded task instances",
        "to": "diagnostic model-response records",
        "source_grounding_gate": True,
        "temporal_validity_gate": True,
        "language_access_gate": True,
        "entity_resolution_gate": True,
        "remedy_forum_gate": True,
        "authority_hierarchy_gate": True,
        "coverage_scope_gate": True,
        "jurisdiction_chain_gate": True,
        "implementation_access_gate": True,
        "procedural_burden_gate": True,
        "blocks": ["model_response_capture", "judge_output", "public_claims"],
        "required_evidence": [
            "diagnostic run cell approved",
            "privacy and retaliation screen passed",
            "model-response record schema available",
            "legal-claim anchor source object IDs or source-gap markers recorded",
            "source-grounding contract status recorded",
            "temporal-validity status recorded",
            "source-language and translation-review status recorded",
            "entity-resolution and registry/license-status basis recorded",
            "remedy/forum status and complaint-path basis recorded",
            "authority-hierarchy status and controlling-source basis recorded",
            "coverage-scope status and worker-category basis recorded",
            "jurisdiction-chain status and cross-border responsibility basis recorded",
            "implementation-access status and operational/enforcement basis recorded",
            "procedural-burden status and deadline/document/evidence basis recorded",
            "not-public-claim status recorded",
        ],
    },
    {
        "id": "diagnostic_capture_to_judge_output",
        "from": "diagnostic model-response records",
        "to": "judge output records",
        "source_grounding_gate": True,
        "temporal_validity_gate": True,
        "language_access_gate": True,
        "entity_resolution_gate": True,
        "remedy_forum_gate": True,
        "authority_hierarchy_gate": True,
        "coverage_scope_gate": True,
        "jurisdiction_chain_gate": True,
        "implementation_access_gate": True,
        "procedural_burden_gate": True,
        "blocks": ["judge_output", "public_claims", "comparable_scoring"],
        "required_evidence": [
            "judge-output schema available",
            "abstention findings required",
            "source-claim findings required",
            "source-grounding contract findings required",
            "temporal-validity findings required",
            "language-access findings required",
            "entity-resolution findings required",
            "authority-hierarchy findings required",
            "coverage-scope findings required",
            "jurisdiction-chain findings required",
            "implementation-access findings required",
            "procedural-burden findings required",
            "forum competence and remedy-routing findings required",
            "redacted rationale policy accepted",
        ],
    },
    {
        "id": "judge_output_to_calibration",
        "from": "judge output records",
        "to": "judge calibration evidence",
        "source_grounding_gate": True,
        "temporal_validity_gate": True,
        "language_access_gate": True,
        "entity_resolution_gate": True,
        "remedy_forum_gate": True,
        "authority_hierarchy_gate": True,
        "coverage_scope_gate": True,
        "jurisdiction_chain_gate": True,
        "implementation_access_gate": True,
        "procedural_burden_gate": True,
        "blocks": ["judge_calibration", "public_claims", "comparable_scoring"],
        "required_evidence": [
            "positive and negative calibration references reviewed",
            "failure-mode cases covered",
            "source-grounding calibration cases covered",
            "temporal-validity calibration expectations covered",
            "language-access calibration expectations covered",
            "entity-resolution calibration expectations covered",
            "remedy/forum competence calibration expectations covered",
            "authority-hierarchy calibration expectations covered",
            "coverage-scope calibration expectations covered",
            "jurisdiction-chain calibration expectations covered",
            "implementation-access calibration expectations covered",
            "procedural-burden calibration expectations covered",
            "privacy review passed",
            "expert review passed",
        ],
    },
    {
        "id": "calibration_to_training_use",
        "from": "calibrated diagnostic evidence",
        "to": "training or distillation use",
        "blocks": ["training_use", "public_claims", "worker_facing_use"],
        "required_evidence": [
            "training-use approval recorded",
            "source licenses reviewed",
            "private details absent",
            "public-claim language remains blocked unless separately approved",
        ],
    },
    {
        "id": "calibration_to_public_claims",
        "from": "calibrated diagnostic evidence",
        "to": "public benchmark claims",
        "blocks": ["public_claims", "leaderboard_claims", "comparable_scoring"],
        "required_evidence": [
            "public-claim review passed",
            "metric provenance is reproducible",
            "scope limits are stated",
            "diagnostic-only caveats are preserved",
        ],
    },
    {
        "id": "calibration_to_comparable_scoring",
        "from": "calibrated diagnostic evidence",
        "to": "comparable model scoring",
        "blocks": ["comparable_scoring", "leaderboard_claims"],
        "required_evidence": [
            "comparable-run approval recorded",
            "all run gates passed",
            "all calibration cases have reviewed examples",
            "artifact pack is reproducible",
        ],
    },
    {
        "id": "comparable_scoring_to_worker_facing_use",
        "from": "reviewed benchmark evidence",
        "to": "worker-facing use",
        "blocks": ["worker_facing_use"],
        "required_evidence": [
            "worker-facing release review passed",
            "legal advice boundary preserved",
            "retaliation-risk language reviewed",
            "current source-object freshness checked",
        ],
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


def _transition_row(
    definition: dict[str, Any],
    index: int,
    *,
    legal_anchor_source_channel_ids: list[str],
) -> dict[str, Any]:
    return {
        "transition_id": f"GPTG-{index:03d}",
        "transition_key": definition["id"],
        "from_state": definition["from"],
        "to_state": definition["to"],
        "status": "blocked",
        "source_grounding_gate": bool(definition.get("source_grounding_gate")),
        "temporal_validity_gate": bool(definition.get("temporal_validity_gate")),
        "language_access_gate": bool(definition.get("language_access_gate")),
        "entity_resolution_gate": bool(definition.get("entity_resolution_gate")),
        "remedy_forum_gate": bool(definition.get("remedy_forum_gate")),
        "authority_hierarchy_gate": bool(definition.get("authority_hierarchy_gate")),
        "coverage_scope_gate": bool(definition.get("coverage_scope_gate")),
        "jurisdiction_chain_gate": bool(definition.get("jurisdiction_chain_gate")),
        "implementation_access_gate": bool(definition.get("implementation_access_gate")),
        "procedural_burden_gate": bool(definition.get("procedural_burden_gate")),
        "blocked_by": list(definition["blocks"]),
        "required_evidence": list(definition["required_evidence"]),
        "required_legal_claim_anchor_source_channel_ids": list(legal_anchor_source_channel_ids),
        "ready_for_manifest_promotion": False,
        "ready_for_prompt_generation": False,
        "ready_for_task_instantiation": False,
        "ready_for_model_response_capture": False,
        "ready_for_judge_output": False,
        "ready_for_judge_calibration": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
    }


def build_transition_gate(
    *,
    source_review_doc: dict[str, Any] | None = None,
    blueprint_doc: dict[str, Any] | None = None,
    eval_contract_doc: dict[str, Any] | None = None,
    diagnostic_doc: dict[str, Any] | None = None,
    calibration_doc: dict[str, Any] | None = None,
    readiness_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a blocked transition gate for the source-gated evaluation chain."""
    source_review_doc = source_review_doc or source_review_builder.build_source_channel_review_packet(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
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
    blueprint_doc = blueprint_doc or blueprint_builder.build_benchmark_blueprint(
        source_review_doc=source_review_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    eval_contract_doc = eval_contract_doc or eval_contract_builder.build_eval_contract(
        blueprint_doc=blueprint_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    diagnostic_doc = diagnostic_doc or diagnostic_builder.build_diagnostic_run_plan(
        blueprint_doc=blueprint_doc,
        eval_contract_doc=eval_contract_doc,
        readiness_doc=readiness_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )
    calibration_doc = calibration_doc or calibration_builder.build_judge_calibration_plan(
        eval_contract_doc=eval_contract_doc,
        diagnostic_doc=diagnostic_doc,
        domain_id=domain_id,
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
        component_dir=component_dir,
    )

    legal_anchor_source_channel_ids = list(
        eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
    )
    transitions = [
        _transition_row(
            definition,
            index,
            legal_anchor_source_channel_ids=legal_anchor_source_channel_ids,
        )
        for index, definition in enumerate(TRANSITION_DEFINITIONS, start=1)
    ]
    blocked_transitions = [row for row in transitions if row["status"] == "blocked"]
    source_grounding_transitions = [row for row in transitions if row["source_grounding_gate"]]
    temporal_validity_transitions = [row for row in transitions if row["temporal_validity_gate"]]
    language_access_transitions = [row for row in transitions if row["language_access_gate"]]
    entity_resolution_transitions = [row for row in transitions if row["entity_resolution_gate"]]
    remedy_forum_transitions = [row for row in transitions if row["remedy_forum_gate"]]
    authority_hierarchy_transitions = [row for row in transitions if row["authority_hierarchy_gate"]]
    coverage_scope_transitions = [row for row in transitions if row["coverage_scope_gate"]]
    jurisdiction_chain_transitions = [row for row in transitions if row["jurisdiction_chain_gate"]]
    implementation_access_transitions = [row for row in transitions if row["implementation_access_gate"]]
    procedural_burden_transitions = [row for row in transitions if row["procedural_burden_gate"]]
    legal_anchor_source_channel_transitions = [
        row
        for row in transitions
        if row["required_legal_claim_anchor_source_channel_ids"] == legal_anchor_source_channel_ids
    ]
    ready_flags = {
        "manifest_promotion": any(row["ready_for_manifest_promotion"] for row in transitions),
        "prompt_generation": any(row["ready_for_prompt_generation"] for row in transitions),
        "task_instantiation": any(row["ready_for_task_instantiation"] for row in transitions),
        "model_response_capture": any(row["ready_for_model_response_capture"] for row in transitions),
        "judge_output": any(row["ready_for_judge_output"] for row in transitions),
        "judge_calibration": any(row["ready_for_judge_calibration"] for row in transitions),
        "training_use": any(row["ready_for_training_use"] for row in transitions),
        "public_claims": any(row["ready_for_public_claims"] for row in transitions),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in transitions),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in transitions),
    }
    summary = {
        "consistency_ok": False,
        "transition_count": len(transitions),
        "blocked_transition_count": len(blocked_transitions),
        "source_grounding_transition_count": len(source_grounding_transitions),
        "temporal_validity_transition_count": len(temporal_validity_transitions),
        "language_access_transition_count": len(language_access_transitions),
        "entity_resolution_transition_count": len(entity_resolution_transitions),
        "remedy_forum_transition_count": len(remedy_forum_transitions),
        "authority_hierarchy_transition_count": len(authority_hierarchy_transitions),
        "coverage_scope_transition_count": len(coverage_scope_transitions),
        "jurisdiction_chain_transition_count": len(jurisdiction_chain_transitions),
        "implementation_access_transition_count": len(implementation_access_transitions),
        "procedural_burden_transition_count": len(procedural_burden_transitions),
        "source_review_rows": source_review_doc["summary"]["review_row_count"],
        "source_review_not_started_rows": source_review_doc["summary"]["not_started_rows"],
        "task_blueprint_count": blueprint_doc["summary"]["task_blueprint_count"],
        "diagnostic_cell_count": diagnostic_doc["summary"]["diagnostic_cell_count"],
        "calibration_case_count": calibration_doc["summary"]["calibration_case_count"],
        "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
            "legal_claim_anchor_source_channel_count"
        ],
        "legal_claim_anchor_source_channel_ids": legal_anchor_source_channel_ids,
        "transitions_preserving_legal_anchor_source_channels": len(
            legal_anchor_source_channel_transitions
        ),
        "ready_for_manifest_promotion": ready_flags["manifest_promotion"],
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_task_instantiation": ready_flags["task_instantiation"],
        "ready_for_model_response_capture": ready_flags["model_response_capture"],
        "ready_for_judge_output": ready_flags["judge_output"],
        "ready_for_judge_calibration": ready_flags["judge_calibration"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This transition gate is a blocked go/no-go matrix only. It does not promote sources, "
            "instantiate prompts, call models, grade outputs, train models, publish claims, enable "
            "worker-facing use, or authorize comparable scoring."
        ),
    }
    checks = [
        _check(
            "source_review_packet_consistency_ok",
            source_review_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=source_review_doc["summary"]["consistency_ok"],
        ),
        _check(
            "benchmark_blueprint_consistency_ok",
            blueprint_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=blueprint_doc["summary"]["consistency_ok"],
        ),
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
            "judge_calibration_plan_consistency_ok",
            calibration_doc["summary"]["consistency_ok"] is True,
            expected=True,
            actual=calibration_doc["summary"]["consistency_ok"],
        ),
        _check(
            "all_transitions_blocked",
            len(blocked_transitions) == len(transitions),
            expected=len(transitions),
            actual=len(blocked_transitions),
        ),
        _check(
            "source_grounding_transitions_present",
            {
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in source_grounding_transitions}),
            expected=[
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in source_grounding_transitions),
        ),
        _check(
            "temporal_validity_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in temporal_validity_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in temporal_validity_transitions),
        ),
        _check(
            "language_access_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in language_access_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in language_access_transitions),
        ),
        _check(
            "entity_resolution_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in entity_resolution_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in entity_resolution_transitions),
        ),
        _check(
            "remedy_forum_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in remedy_forum_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in remedy_forum_transitions),
        ),
        _check(
            "authority_hierarchy_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in authority_hierarchy_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in authority_hierarchy_transitions),
        ),
        _check(
            "coverage_scope_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in coverage_scope_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in coverage_scope_transitions),
        ),
        _check(
            "jurisdiction_chain_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in jurisdiction_chain_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in jurisdiction_chain_transitions),
        ),
        _check(
            "implementation_access_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in implementation_access_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in implementation_access_transitions),
        ),
        _check(
            "procedural_burden_transitions_present",
            {
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            }.issubset({row["transition_key"] for row in procedural_burden_transitions}),
            expected=[
                "source_review_to_manifest_promotion",
                "manifest_to_prompt_instantiation",
                "prompt_to_diagnostic_capture",
                "diagnostic_capture_to_judge_output",
                "judge_output_to_calibration",
            ],
            actual=sorted(row["transition_key"] for row in procedural_burden_transitions),
        ),
        _check(
            "source_rows_still_not_started",
            source_review_doc["summary"]["not_started_rows"]
            == source_review_doc["summary"]["review_row_count"],
            expected=source_review_doc["summary"]["review_row_count"],
            actual=source_review_doc["summary"]["not_started_rows"],
        ),
        _check(
            "calibration_cases_still_blocked",
            calibration_doc["summary"]["blocked_calibration_cases"]
            == calibration_doc["summary"]["calibration_case_count"],
            expected=calibration_doc["summary"]["calibration_case_count"],
            actual=calibration_doc["summary"]["blocked_calibration_cases"],
        ),
        _check(
            "legal_claim_anchor_channels_match_eval_diagnostic_and_calibration",
            summary["legal_claim_anchor_source_channel_count"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_count"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == eval_contract_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == diagnostic_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and summary["legal_claim_anchor_source_channel_ids"]
            == calibration_doc["summary"]["legal_claim_anchor_source_channel_ids"]
            and len(legal_anchor_source_channel_transitions) == len(transitions),
            expected={
                "legal_claim_anchor_source_channel_count": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": eval_contract_doc["summary"][
                    "legal_claim_anchor_source_channel_ids"
                ],
                "transition_count": len(transitions),
            },
            actual={
                "legal_claim_anchor_source_channel_count": summary[
                    "legal_claim_anchor_source_channel_count"
                ],
                "legal_claim_anchor_source_channel_ids": summary[
                    "legal_claim_anchor_source_channel_ids"
                ],
                "transition_count": len(legal_anchor_source_channel_transitions),
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
            "schema_version": "global_protections_transition_gate.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "domain": domain_id,
            "status": (
                "blocked transition gate only; not legal advice, not source verification, not "
                "model execution, not judge scoring, not training data, and not comparable "
                "benchmark evidence"
            ),
        },
        "summary": summary,
        "transitions": transitions,
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("transition_gate_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown transition gate."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Transition Gate",
        "",
        (
            "This transition gate is a blocked go/no-go matrix only. It is not legal advice, "
            "not source verification, not model execution, not judge scoring, and not comparable "
            "benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Transitions | {summary['transition_count']} |",
        f"| Blocked transitions | {summary['blocked_transition_count']} |",
        f"| Source-grounding transitions | {summary['source_grounding_transition_count']} |",
        f"| Temporal-validity transitions | {summary['temporal_validity_transition_count']} |",
        f"| Language-access transitions | {summary['language_access_transition_count']} |",
        f"| Entity-resolution transitions | {summary['entity_resolution_transition_count']} |",
        f"| Remedy/forum transitions | {summary['remedy_forum_transition_count']} |",
        f"| Authority-hierarchy transitions | {summary['authority_hierarchy_transition_count']} |",
        f"| Coverage-scope transitions | {summary['coverage_scope_transition_count']} |",
        f"| Jurisdiction-chain transitions | {summary['jurisdiction_chain_transition_count']} |",
        f"| Implementation-access transitions | {summary['implementation_access_transition_count']} |",
        f"| Procedural-burden transitions | {summary['procedural_burden_transition_count']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        (
            "| Transitions preserving legal-anchor source channels "
            f"| {summary['transitions_preserving_legal_anchor_source_channels']} |"
        ),
        f"| Source review rows | {summary['source_review_rows']} |",
        f"| Calibration cases | {summary['calibration_case_count']} |",
        f"| Ready for manifest promotion | {str(bool(summary['ready_for_manifest_promotion'])).lower()} |",
        f"| Ready for model response capture | {str(bool(summary['ready_for_model_response_capture'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Transitions",
        "",
        "| Transition | From | To | Source grounding | Temporal validity | Language access | Entity resolution | Remedy/forum | Authority hierarchy | Coverage scope | Jurisdiction chain | Implementation access | Procedural burden | Status | Blocks |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in doc["transitions"]:
        lines.append(
            f"| `{_md_cell(row['transition_key'])}` "
            f"| {_md_cell(row['from_state'])} "
            f"| {_md_cell(row['to_state'])} "
            f"| {str(bool(row['source_grounding_gate'])).lower()} "
            f"| {str(bool(row['temporal_validity_gate'])).lower()} "
            f"| {str(bool(row['language_access_gate'])).lower()} "
            f"| {str(bool(row['entity_resolution_gate'])).lower()} "
            f"| {str(bool(row['remedy_forum_gate'])).lower()} "
            f"| {str(bool(row['authority_hierarchy_gate'])).lower()} "
            f"| {str(bool(row['coverage_scope_gate'])).lower()} "
            f"| {str(bool(row['jurisdiction_chain_gate'])).lower()} "
            f"| {str(bool(row['implementation_access_gate'])).lower()} "
            f"| {str(bool(row['procedural_burden_gate'])).lower()} "
            f"| {_md_cell(row['status'])} "
            f"| {_md_cell(', '.join(row['blocked_by']))} |"
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
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown gate")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_transition_gate(
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
        print("[global-protections-transition-gate] gate is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-transition-gate] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['transition_count']} transitions; "
        f"{summary['blocked_transition_count']} blocked; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
