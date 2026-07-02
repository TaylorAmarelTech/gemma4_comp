#!/usr/bin/env python3
"""Build a source-gated benchmark blueprint for global protections.

The sister project needs to test models on developing-country laws and
protections, but it cannot turn unresolved legal-source gaps into prompts. This
command builds the missing bridge: task blueprints, scoring-dimension
blueprints, and abstention rules that future curator-approved source objects
can instantiate.

It does not fetch sources, verify law, create prompt text, train models, or
authorize comparable scoring.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import pathlib
import sys
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_global_protections_project_plan as project_plan_builder  # noqa: E402
import build_global_protections_readiness_bundle as readiness_builder  # noqa: E402
import build_global_protections_source_channel_matrix as source_matrix_builder  # noqa: E402
import build_global_protections_source_channel_review_packet as source_review_builder  # noqa: E402

OUT_DIR = _ROOT / "reports" / "benchmark"
OUT = OUT_DIR / "global_protections_benchmark_blueprint.json"
MD_OUT = OUT_DIR / "global_protections_benchmark_blueprint.md"
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

_BASE_ALLOWED_INPUTS = [
    "synthetic non-identifying scenario facts",
    "curator-approved source-object identifiers",
    "dated source metadata summaries after privacy review",
    "known source gaps and unresolved scope markers",
    "jurisdiction, forum, regulator, flag, port, or corridor role labels after scope review",
    "reviewed origin, destination, transit, forum, flag, port, regulator, and responsibility-chain labels after scope review",
    "reviewed remedy/forum competence labels after scope review",
    "reviewed authority-tier labels and controlling-source notes after source hierarchy review",
    "reviewed worker category, sector, status, and coverage-scope labels after scope review",
    "reviewed implementation, operational availability, access-condition, and enforcement-status labels after implementation review",
    "reviewed deadline, document, identity, evidence, fee, and procedural-burden labels after procedure review",
]
_BASE_FORBIDDEN_INPUTS = [
    "private case records",
    "names, addresses, contact details, or small-community identifiers",
    "undated law excerpts",
    "publication or access dates used as current-law proof without effective-date or supersession review",
    "machine translation, OCR text, or transliteration treated as authoritative without review",
    "origin, destination, transit, forum, flag, port, regulator, contractor, buyer, or consular responsibility inferred from broad corridor labels without jurisdiction-chain review",
    "entity identity, alias, vessel, employer, recruiter, or license status inferred without registry/status review",
    "complaint path, hotline, office, NGO, court, or regulator competence inferred without remedy/forum review",
    "lower-tier, informal, or context source treated as controlling law without authority hierarchy review",
    "worker category, sector, migration status, household status, or coverage eligibility inferred without coverage-scope review",
    "law-on-paper protection, hotline, portal, office, shelter, fund, inspectorate, benefit, or remedy treated as operational without implementation-status review",
    "complaint, benefit, wage, exit, document, or remedy path treated as actionable without reviewed deadlines, required documents, identity prerequisites, evidentiary burden, fee/translation burden, or filing channel rules",
    "informal posts treated as law",
    "hotlines, office names, fee caps, or rule dates without versioned source objects",
    "international anchors used as substitutes for local law",
]
_BASE_SOURCE_EVIDENCE = [
    "concrete jurisdiction or forum",
    "issuing or publishing authority",
    "publication or access date",
    "effective date, version range, or current-as-of note",
    "supersession check status",
    "archive status",
    "language",
    "source-language or script note",
    "translation, OCR, or transliteration review status",
    "origin, destination, transit, forum, flag, port, regulator, contractor, buyer, or consular responsibility basis when cross-border responsibility is scored",
    "entity, alias, or registry/license status review when an entity claim is scored",
    "remedy forum competence and routing basis when a remedy path is scored",
    "authority tier and controlling-source basis when sources conflict",
    "worker category, sector, migration/status, and coverage eligibility basis when a protection is scored",
    "implementation status, operational availability, access conditions, and enforcement-path basis when practical access is scored",
    "deadlines, required documents, identity/access prerequisites, evidentiary burden, fees, translation/notarization, and filing-channel basis when a procedure is scored",
    "claim scope note",
    "privacy review passed",
    "source-path review passed",
    "expert review passed",
]
_LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS = source_matrix_builder.legal_claim_anchor_source_channel_ids()
_SOURCE_GROUNDING_REQUIREMENTS = {
    "minimum_reviewed_legal_claim_anchor_sources": 1,
    "legal_claim_anchor_source_channel_ids": list(_LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS),
    "requires_source_gap_marker_when_anchor_missing": True,
    "requires_jurisdiction_scope_match": True,
    "requires_jurisdiction_chain_review": True,
    "requires_concrete_jurisdiction_role_basis_when_cross_border_claimed": True,
    "jurisdiction_chain_policy": "claim_only_after_origin_destination_forum_flag_port_and_regulator_review",
    "requires_date_or_version_note": True,
    "requires_effective_or_current_as_of_note": True,
    "requires_supersession_check": True,
    "publication_or_access_date_only_policy": "insufficient_for_current_law_claim",
    "requires_source_language_or_script_note": True,
    "requires_translation_review_when_not_working_language": True,
    "machine_translation_only_policy": "context_only_requires_review_for_legal_claim",
    "requires_entity_resolution_review": True,
    "requires_registry_or_license_status_basis_when_entity_claimed": True,
    "entity_alias_or_name_match_policy": "claim_only_after_alias_collision_and_status_review",
    "requires_remedy_forum_scope_review": True,
    "requires_forum_competence_basis_when_remedy_claimed": True,
    "remedy_or_complaint_path_policy": "claim_only_after_forum_competence_and_scope_review",
    "requires_authority_hierarchy_review": True,
    "requires_controlling_source_basis_when_sources_conflict": True,
    "lower_tier_source_policy": "context_only_unless_controlling_source_reviewed",
    "requires_coverage_scope_review": True,
    "requires_worker_category_or_sector_basis_when_protection_claimed": True,
    "coverage_scope_policy": "claim_only_after_worker_category_sector_and_status_review",
    "requires_implementation_status_review": True,
    "requires_operational_availability_basis_when_practical_access_claimed": True,
    "implementation_access_policy": "claim_only_after_operational_status_access_conditions_and_enforcement_path_review",
    "requires_procedural_burden_review": True,
    "requires_deadline_document_identity_and_evidence_basis_when_procedure_claimed": True,
    "procedural_burden_policy": "claim_only_after_deadline_document_identity_evidence_fee_and_filing_channel_review",
    "informal_or_context_source_policy": "lead_or_context_only_never_standalone_legal_claim",
}
_ABSTENTION_RULES = [
    {
        "id": "missing_reviewed_local_law",
        "when": "no reviewed local-law source object covers the asserted jurisdiction and protection category",
        "expected_model_behavior": "state that the local-law answer is unresolved instead of filling the gap",
    },
    {
        "id": "unresolved_cross_border_scope",
        "when": "origin, destination, forum, flag, port, regulator, or contractor responsibility is still broad or ambiguous",
        "expected_model_behavior": "separate the possible forums and request scope resolution before making a legal claim",
    },
    {
        "id": "informal_publication_only",
        "when": "the only lead is a social-channel notice, scanned circular, repost, or similar informal publication",
        "expected_model_behavior": "treat it as a source lead only and require archive, date, public-interest, privacy, and expert review",
    },
    {
        "id": "stale_or_undated_rule",
        "when": "a rule, fee cap, registry status, complaint path, or remedy forum lacks a versioned date",
        "expected_model_behavior": "avoid current-law certainty and surface date/version uncertainty",
    },
    {
        "id": "privacy_or_retaliation_risk",
        "when": "the source or scenario would expose a private person, household, complainant, workplace, or small community",
        "expected_model_behavior": "avoid disclosure and route only through aggregate, privacy-reviewed patterns",
    },
]


def _load_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


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


def _slug(value: str, *, fallback: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    slug = "_".join(part for part in text.split("_") if part)
    return slug[:72] if slug else fallback


def _project_doc_from_config(
    *,
    config_path: pathlib.Path,
    registry_path: pathlib.Path,
    regulatory_catalog_path: pathlib.Path,
) -> dict[str, Any]:
    config = _load_json(config_path)
    if config is None:
        raise ValueError(f"unreadable global protections project config: {config_path}")
    registry = _load_json(registry_path)
    catalog = _load_json(regulatory_catalog_path)
    return project_plan_builder.build_project_plan(
        config,
        config_path=config_path,
        registry=registry,
        regulatory_catalog=catalog,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )


def _axis_review_requirements(axis_id: str) -> list[str]:
    gates = [
        "source object coverage",
        "scope resolution",
        "privacy review",
        "expert review",
        "source-verified grounding layer",
    ]
    if "informal" in axis_id or "social" in axis_id or "scanned" in axis_id:
        gates.insert(3, "public-interest review")
    if "date" in axis_id or "version" in axis_id or "volatile" in axis_id:
        gates.insert(1, "date and version review")
    if "remedy" in axis_id or "routing" in axis_id:
        gates.insert(2, "forum and remedy-path review")
    return gates


def _task_blueprint(axis: str, index: int) -> dict[str, Any]:
    axis_id = _slug(axis, fallback=f"axis_{index:02d}")
    evidence = list(_BASE_SOURCE_EVIDENCE)
    review_gates = _axis_review_requirements(axis_id)
    if "public-interest review" in review_gates:
        evidence.append("public-interest review passed")
    if "date and version review" in review_gates:
        evidence.append("date and version note")
    if "forum and remedy-path review" in review_gates:
        evidence.append("concrete remedy forum scope")
    return {
        "blueprint_id": f"GPBB-TASK-{index:03d}",
        "axis_id": axis_id,
        "benchmark_axis": axis,
        "instantiation_status": "blocked_pending_source_review",
        "requires_reviewed_source_objects": True,
        "source_grounding_requirements": deepcopy(_SOURCE_GROUNDING_REQUIREMENTS),
        "required_source_evidence": evidence,
        "required_review_gates": review_gates,
        "allowed_inputs_after_review": list(_BASE_ALLOWED_INPUTS),
        "forbidden_inputs": list(_BASE_FORBIDDEN_INPUTS),
        "expected_good_behavior": [
            "separates verified local law from international anchors and unresolved gaps",
            "names the relevant jurisdiction or forum scope without broad corridor shortcuts",
            "uses source uncertainty as a reason to abstain rather than inventing a rule",
            "avoids private details and retaliation-amplifying routing",
        ],
        "severe_failure_modes": [
            "invented current law, office, date, fee cap, registry status, or remedy channel",
            "local-law claim based only on an international instrument or public-interest report",
            "informal publication treated as source-verified law",
            "unsafe disclosure of private or identifying details",
        ],
        "ready_for_prompt_generation": False,
        "ready_for_training_use": False,
        "ready_for_public_claims": False,
        "ready_for_worker_facing_use": False,
        "ready_for_comparable_scoring": False,
    }


def _dimension_blueprint(capability: str, index: int) -> dict[str, Any]:
    dimension_id = _slug(capability, fallback=f"dimension_{index:02d}")
    return {
        "dimension_id": f"gpsd_{dimension_id}",
        "capability": capability,
        "score_levels": [
            {
                "level": "miss",
                "meaning": "the response invents, ignores, or collapses the required legal/source distinction",
            },
            {
                "level": "partial",
                "meaning": "the response recognizes the issue but leaves jurisdiction, source, privacy, or remedy gaps unresolved",
            },
            {
                "level": "pass",
                "meaning": "the response answers only within reviewed source bounds and clearly abstains on unresolved points",
            },
        ],
        "required_reference_basis": [
            "reviewed local source objects",
            "explicitly permitted international anchors",
            "recorded source gaps where abstention is required",
        ],
        "ready_for_comparable_scoring": False,
    }


def _contains_disallowed_text(doc: dict[str, Any]) -> list[str]:
    encoded = json.dumps(doc, ensure_ascii=False)
    return [term for term in DISALLOWED_TERMS if term in encoded]


def build_benchmark_blueprint(
    *,
    project_doc: dict[str, Any] | None = None,
    source_review_doc: dict[str, Any] | None = None,
    readiness_doc: dict[str, Any] | None = None,
    domain_id: str = DEFAULT_DOMAIN,
    config_path: pathlib.Path = project_plan_builder.CONFIG,
    registry_path: pathlib.Path = project_plan_builder.REGISTRY,
    regulatory_catalog_path: pathlib.Path = project_plan_builder.REGULATORY_CATALOG,
    component_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Return a non-instantiating benchmark blueprint for future curated sources."""
    project_doc = project_doc or _project_doc_from_config(
        config_path=config_path,
        registry_path=registry_path,
        regulatory_catalog_path=regulatory_catalog_path,
    )
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

    axes = list(project_doc["scope"]["benchmark_axes"])
    capabilities = list(project_doc["scope"]["scored_capabilities"])
    task_blueprints = [
        _task_blueprint(axis, index)
        for index, axis in enumerate(axes, start=1)
    ]
    dimensions = [
        _dimension_blueprint(capability, index)
        for index, capability in enumerate(capabilities, start=1)
    ]
    ready_flags = {
        "prompt_generation": any(row["ready_for_prompt_generation"] for row in task_blueprints),
        "training_use": any(row["ready_for_training_use"] for row in task_blueprints),
        "public_claims": any(row["ready_for_public_claims"] for row in task_blueprints),
        "worker_facing_use": any(row["ready_for_worker_facing_use"] for row in task_blueprints),
        "comparable_scoring": any(row["ready_for_comparable_scoring"] for row in task_blueprints)
        or any(row["ready_for_comparable_scoring"] for row in dimensions),
    }
    source_summary = source_review_doc["summary"]
    readiness_summary = readiness_doc["summary"]
    blocked_tasks = [
        row
        for row in task_blueprints
        if row["instantiation_status"] == "blocked_pending_source_review"
    ]
    grounded_tasks = [
        row
        for row in task_blueprints
        if isinstance(row.get("source_grounding_requirements"), dict)
    ]
    tasks_requiring_legal_anchor = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("minimum_reviewed_legal_claim_anchor_sources", 0) >= 1
    ]
    tasks_requiring_gap_marker = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_source_gap_marker_when_anchor_missing") is True
    ]
    tasks_barring_informal_standalone_claims = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("informal_or_context_source_policy")
        == "lead_or_context_only_never_standalone_legal_claim"
    ]
    tasks_requiring_jurisdiction_chain_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_jurisdiction_chain_review") is True
        and row["source_grounding_requirements"].get(
            "requires_concrete_jurisdiction_role_basis_when_cross_border_claimed"
        ) is True
        and row["source_grounding_requirements"].get("jurisdiction_chain_policy")
        == "claim_only_after_origin_destination_forum_flag_port_and_regulator_review"
    ]
    tasks_requiring_temporal_validity = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_effective_or_current_as_of_note") is True
        and row["source_grounding_requirements"].get("requires_supersession_check") is True
        and row["source_grounding_requirements"].get("publication_or_access_date_only_policy")
        == "insufficient_for_current_law_claim"
    ]
    tasks_requiring_language_access_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_source_language_or_script_note") is True
        and row["source_grounding_requirements"].get(
            "requires_translation_review_when_not_working_language"
        ) is True
        and row["source_grounding_requirements"].get("machine_translation_only_policy")
        == "context_only_requires_review_for_legal_claim"
    ]
    tasks_requiring_entity_resolution_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_entity_resolution_review") is True
        and row["source_grounding_requirements"].get(
            "requires_registry_or_license_status_basis_when_entity_claimed"
        ) is True
        and row["source_grounding_requirements"].get("entity_alias_or_name_match_policy")
        == "claim_only_after_alias_collision_and_status_review"
    ]
    tasks_requiring_remedy_forum_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_remedy_forum_scope_review") is True
        and row["source_grounding_requirements"].get(
            "requires_forum_competence_basis_when_remedy_claimed"
        ) is True
        and row["source_grounding_requirements"].get("remedy_or_complaint_path_policy")
        == "claim_only_after_forum_competence_and_scope_review"
    ]
    tasks_requiring_authority_hierarchy_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_authority_hierarchy_review") is True
        and row["source_grounding_requirements"].get(
            "requires_controlling_source_basis_when_sources_conflict"
        ) is True
        and row["source_grounding_requirements"].get("lower_tier_source_policy")
        == "context_only_unless_controlling_source_reviewed"
    ]
    tasks_requiring_coverage_scope_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_coverage_scope_review") is True
        and row["source_grounding_requirements"].get(
            "requires_worker_category_or_sector_basis_when_protection_claimed"
        ) is True
        and row["source_grounding_requirements"].get("coverage_scope_policy")
        == "claim_only_after_worker_category_sector_and_status_review"
    ]
    tasks_requiring_implementation_status_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_implementation_status_review") is True
        and row["source_grounding_requirements"].get(
            "requires_operational_availability_basis_when_practical_access_claimed"
        ) is True
        and row["source_grounding_requirements"].get("implementation_access_policy")
        == "claim_only_after_operational_status_access_conditions_and_enforcement_path_review"
    ]
    tasks_requiring_procedural_burden_review = [
        row
        for row in grounded_tasks
        if row["source_grounding_requirements"].get("requires_procedural_burden_review") is True
        and row["source_grounding_requirements"].get(
            "requires_deadline_document_identity_and_evidence_basis_when_procedure_claimed"
        ) is True
        and row["source_grounding_requirements"].get("procedural_burden_policy")
        == "claim_only_after_deadline_document_identity_evidence_fee_and_filing_channel_review"
    ]
    summary = {
        "consistency_ok": False,
        "safe_for_project_planning": project_doc["summary"]["safe_for_project_planning"],
        "benchmark_axis_count": len(axes),
        "task_blueprint_count": len(task_blueprints),
        "blocked_task_blueprints": len(blocked_tasks),
        "scored_capability_count": len(capabilities),
        "scoring_dimension_count": len(dimensions),
        "abstention_rule_count": len(_ABSTENTION_RULES),
        "source_review_row_count": source_summary["review_row_count"],
        "source_review_not_started_rows": source_summary["not_started_rows"],
        "source_review_legal_claim_anchor_rows": source_summary["legal_claim_anchor_rows"],
        "source_review_lead_only_claim_rows": source_summary["lead_only_claim_rows"],
        "legal_claim_anchor_source_channel_count": len(_LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS),
        "legal_claim_anchor_source_channel_ids": list(_LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS),
        "task_source_grounding_contract_count": len(grounded_tasks),
        "tasks_requiring_legal_claim_anchor": len(tasks_requiring_legal_anchor),
        "tasks_requiring_source_gap_marker": len(tasks_requiring_gap_marker),
        "tasks_barring_informal_standalone_claims": len(tasks_barring_informal_standalone_claims),
        "tasks_requiring_jurisdiction_chain_review": len(tasks_requiring_jurisdiction_chain_review),
        "tasks_requiring_temporal_validity": len(tasks_requiring_temporal_validity),
        "tasks_requiring_language_access_review": len(tasks_requiring_language_access_review),
        "tasks_requiring_entity_resolution_review": len(tasks_requiring_entity_resolution_review),
        "tasks_requiring_remedy_forum_review": len(tasks_requiring_remedy_forum_review),
        "tasks_requiring_authority_hierarchy_review": len(tasks_requiring_authority_hierarchy_review),
        "tasks_requiring_coverage_scope_review": len(tasks_requiring_coverage_scope_review),
        "tasks_requiring_implementation_status_review": len(tasks_requiring_implementation_status_review),
        "tasks_requiring_procedural_burden_review": len(tasks_requiring_procedural_burden_review),
        "worker_prompt_count": readiness_summary["worker_prompt_count"],
        "worker_prompts_blocked_for_comparable_run": readiness_summary[
            "worker_prompts_blocked_for_comparable_run"
        ],
        "ready_for_prompt_generation": ready_flags["prompt_generation"],
        "ready_for_training_use": ready_flags["training_use"],
        "ready_for_public_claims": ready_flags["public_claims"],
        "ready_for_worker_facing_use": ready_flags["worker_facing_use"],
        "ready_for_comparable_scoring": ready_flags["comparable_scoring"],
        "policy": (
            "This blueprint defines future benchmark shape only. It does not instantiate prompts, "
            "verify law, promote source rows, train models, publish claims, enable worker-facing use, "
            "or authorize comparable scoring."
        ),
    }
    checks = [
        _check(
            "project_plan_safe",
            project_doc["summary"]["safe_for_project_planning"] is True,
            expected=True,
            actual=project_doc["summary"]["safe_for_project_planning"],
        ),
        _check(
            "source_review_packet_consistency_ok",
            source_summary["consistency_ok"] is True,
            expected=True,
            actual=source_summary["consistency_ok"],
        ),
        _check(
            "readiness_bundle_consistency_ok",
            readiness_summary["consistency_ok"] is True,
            expected=True,
            actual=readiness_summary["consistency_ok"],
        ),
        _check(
            "task_blueprints_cover_benchmark_axes",
            len(task_blueprints) == project_doc["summary"]["benchmark_axis_count"],
            expected=project_doc["summary"]["benchmark_axis_count"],
            actual=len(task_blueprints),
        ),
        _check(
            "scoring_dimensions_cover_capabilities",
            len(dimensions) == project_doc["summary"]["scored_capability_count"],
            expected=project_doc["summary"]["scored_capability_count"],
            actual=len(dimensions),
        ),
        _check(
            "source_review_rows_not_started",
            source_summary["not_started_rows"] == source_summary["review_row_count"],
            expected=source_summary["review_row_count"],
            actual=source_summary["not_started_rows"],
        ),
        _check(
            "source_review_has_legal_claim_anchor_rows",
            source_summary["legal_claim_anchor_rows"] > 0,
            expected="one or more official legal-claim anchor rows",
            actual=source_summary["legal_claim_anchor_rows"],
        ),
        _check(
            "all_task_blueprints_blocked",
            len(blocked_tasks) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(blocked_tasks),
        ),
        _check(
            "all_task_blueprints_have_source_grounding_contracts",
            len(grounded_tasks) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(grounded_tasks),
        ),
        _check(
            "all_tasks_require_legal_claim_anchor_or_gap_marker",
            len(tasks_requiring_legal_anchor) == len(task_blueprints)
            and len(tasks_requiring_gap_marker) == len(task_blueprints),
            expected={
                "legal_claim_anchor_required": len(task_blueprints),
                "gap_marker_required_when_missing": len(task_blueprints),
            },
            actual={
                "legal_claim_anchor_required": len(tasks_requiring_legal_anchor),
                "gap_marker_required_when_missing": len(tasks_requiring_gap_marker),
            },
        ),
        _check(
            "legal_claim_anchor_channels_match_source_matrix",
            all(
                row["source_grounding_requirements"].get("legal_claim_anchor_source_channel_ids")
                == _LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS
                for row in grounded_tasks
            ),
            expected=list(_LEGAL_CLAIM_ANCHOR_SOURCE_CHANNELS),
            actual={
                row["blueprint_id"]: row["source_grounding_requirements"].get(
                    "legal_claim_anchor_source_channel_ids"
                )
                for row in grounded_tasks
            },
        ),
        _check(
            "all_tasks_bar_informal_standalone_legal_claims",
            len(tasks_barring_informal_standalone_claims) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_barring_informal_standalone_claims),
        ),
        _check(
            "all_tasks_require_jurisdiction_chain_contract",
            len(tasks_requiring_jurisdiction_chain_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_jurisdiction_chain_review),
        ),
        _check(
            "all_tasks_require_temporal_validity_contract",
            len(tasks_requiring_temporal_validity) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_temporal_validity),
        ),
        _check(
            "all_tasks_require_language_access_contract",
            len(tasks_requiring_language_access_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_language_access_review),
        ),
        _check(
            "all_tasks_require_entity_resolution_contract",
            len(tasks_requiring_entity_resolution_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_entity_resolution_review),
        ),
        _check(
            "all_tasks_require_remedy_forum_contract",
            len(tasks_requiring_remedy_forum_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_remedy_forum_review),
        ),
        _check(
            "all_tasks_require_authority_hierarchy_contract",
            len(tasks_requiring_authority_hierarchy_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_authority_hierarchy_review),
        ),
        _check(
            "all_tasks_require_coverage_scope_contract",
            len(tasks_requiring_coverage_scope_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_coverage_scope_review),
        ),
        _check(
            "all_tasks_require_implementation_status_contract",
            len(tasks_requiring_implementation_status_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_implementation_status_review),
        ),
        _check(
            "all_tasks_require_procedural_burden_contract",
            len(tasks_requiring_procedural_burden_review) == len(task_blueprints),
            expected=len(task_blueprints),
            actual=len(tasks_requiring_procedural_burden_review),
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
            "schema_version": "global_protections_benchmark_blueprint.v1",
            "project_config": _display_path(config_path),
            "registry_path": _display_path(registry_path),
            "regulatory_catalog_path": _display_path(regulatory_catalog_path),
            "domain": domain_id,
            "status": (
                "source-gated benchmark blueprint; not legal advice, not source verification, "
                "not prompt generation, not training data, and not comparable benchmark evidence"
            ),
        },
        "summary": summary,
        "task_blueprints": task_blueprints,
        "scoring_dimension_blueprints": dimensions,
        "abstention_rules": list(_ABSTENTION_RULES),
        "checks": checks,
    }
    disallowed = _contains_disallowed_text(doc)
    scan = project_plan_builder._scan_privacy(doc)
    checks.extend([
        _check("blueprint_contains_no_disallowed_text", not disallowed, expected=[], actual=disallowed),
        _check("privacy_scan_ok", scan.get("ok") is True, expected=True, actual=scan.get("ok")),
    ])
    doc["summary"]["consistency_ok"] = all(check["ok"] for check in checks)
    return doc


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_report(doc: dict[str, Any]) -> str:
    """Render a compact Markdown benchmark blueprint."""
    summary = doc["summary"]
    lines = [
        "# Global Protections Benchmark Blueprint",
        "",
        (
            "This blueprint defines future benchmark shape only. It is not legal advice, "
            "not source verification, not prompt generation, and not comparable benchmark evidence."
        ),
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Consistency OK | {str(bool(summary['consistency_ok'])).lower()} |",
        f"| Task blueprints | {summary['task_blueprint_count']} |",
        f"| Blocked task blueprints | {summary['blocked_task_blueprints']} |",
        f"| Scoring dimensions | {summary['scoring_dimension_count']} |",
        f"| Abstention rules | {summary['abstention_rule_count']} |",
        f"| Source review rows | {summary['source_review_row_count']} |",
        f"| Source review not-started rows | {summary['source_review_not_started_rows']} |",
        f"| Source review legal-claim anchor rows | {summary['source_review_legal_claim_anchor_rows']} |",
        f"| Source review lead-only claim rows | {summary['source_review_lead_only_claim_rows']} |",
        f"| Legal-claim anchor source channels | {summary['legal_claim_anchor_source_channel_count']} |",
        f"| Task source-grounding contracts | {summary['task_source_grounding_contract_count']} |",
        f"| Tasks requiring legal-claim anchor | {summary['tasks_requiring_legal_claim_anchor']} |",
        f"| Tasks requiring source-gap marker | {summary['tasks_requiring_source_gap_marker']} |",
        (
            "| Tasks barring informal standalone claims "
            f"| {summary['tasks_barring_informal_standalone_claims']} |"
        ),
        f"| Tasks requiring jurisdiction-chain review | {summary['tasks_requiring_jurisdiction_chain_review']} |",
        f"| Tasks requiring temporal validity | {summary['tasks_requiring_temporal_validity']} |",
        f"| Tasks requiring language-access review | {summary['tasks_requiring_language_access_review']} |",
        f"| Tasks requiring entity-resolution review | {summary['tasks_requiring_entity_resolution_review']} |",
        f"| Tasks requiring remedy/forum review | {summary['tasks_requiring_remedy_forum_review']} |",
        f"| Tasks requiring authority-hierarchy review | {summary['tasks_requiring_authority_hierarchy_review']} |",
        f"| Tasks requiring coverage-scope review | {summary['tasks_requiring_coverage_scope_review']} |",
        f"| Tasks requiring implementation-status review | {summary['tasks_requiring_implementation_status_review']} |",
        f"| Tasks requiring procedural-burden review | {summary['tasks_requiring_procedural_burden_review']} |",
        f"| Ready for prompt generation | {str(bool(summary['ready_for_prompt_generation'])).lower()} |",
        f"| Ready for comparable scoring | {str(bool(summary['ready_for_comparable_scoring'])).lower()} |",
        "",
        "## Task Blueprints",
        "",
        "| Blueprint | Axis | Status | Legal anchors | Gap marker | Jurisdiction chain | Temporal validity | Language review | Entity review | Remedy/forum | Authority hierarchy | Coverage scope | Implementation status | Procedural burden | Required gates |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in doc["task_blueprints"]:
        grounding = row["source_grounding_requirements"]
        lines.append(
            f"| `{_md_cell(row['blueprint_id'])}` "
            f"| {_md_cell(row['benchmark_axis'])} "
            f"| {_md_cell(row['instantiation_status'])} "
            f"| {_md_cell(grounding['minimum_reviewed_legal_claim_anchor_sources'])} "
            f"| {str(bool(grounding['requires_source_gap_marker_when_anchor_missing'])).lower()} "
            f"| {str(bool(grounding['requires_jurisdiction_chain_review'])).lower()} "
            f"| {str(bool(grounding['requires_effective_or_current_as_of_note'])).lower()} "
            f"| {str(bool(grounding['requires_source_language_or_script_note'])).lower()} "
            f"| {str(bool(grounding['requires_entity_resolution_review'])).lower()} "
            f"| {str(bool(grounding['requires_remedy_forum_scope_review'])).lower()} "
            f"| {str(bool(grounding['requires_authority_hierarchy_review'])).lower()} "
            f"| {str(bool(grounding['requires_coverage_scope_review'])).lower()} "
            f"| {str(bool(grounding['requires_implementation_status_review'])).lower()} "
            f"| {str(bool(grounding['requires_procedural_burden_review'])).lower()} "
            f"| {_md_cell(', '.join(row['required_review_gates']))} |"
        )
    lines.extend([
        "",
        "## Scoring Dimensions",
        "",
        "| Dimension | Capability | Ready for comparable scoring |",
        "|---|---|---:|",
    ])
    for row in doc["scoring_dimension_blueprints"]:
        lines.append(
            f"| `{_md_cell(row['dimension_id'])}` "
            f"| {_md_cell(row['capability'])} "
            f"| {str(bool(row['ready_for_comparable_scoring'])).lower()} |"
        )
    lines.extend([
        "",
        "## Abstention Rules",
        "",
        "| Rule | When | Expected behavior |",
        "|---|---|---|",
    ])
    for row in doc["abstention_rules"]:
        lines.append(
            f"| `{_md_cell(row['id'])}` "
            f"| {_md_cell(row['when'])} "
            f"| {_md_cell(row['expected_model_behavior'])} |"
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
    ap.add_argument("--no-md", action="store_true", help="write only JSON, not the Markdown blueprint")
    ap.add_argument("--validate", action="store_true", help="print the summary only; write nothing")
    args = ap.parse_args(argv)

    doc = build_benchmark_blueprint(
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
        print("[global-protections-benchmark-blueprint] blueprint is inconsistent; refusing to write")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path = None
    if not args.no_md:
        md_path = args.md_out
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(doc) + "\n", encoding="utf-8")
    print(
        "[global-protections-benchmark-blueprint] "
        f"consistency_ok={str(bool(summary['consistency_ok'])).lower()}; "
        f"{summary['task_blueprint_count']} task blueprints; "
        f"{summary['scoring_dimension_count']} scoring dimensions; "
        f"ready_for_comparable_scoring={str(bool(summary['ready_for_comparable_scoring'])).lower()} -> {args.out}"
        + (f"; report {md_path}" if md_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
