"""Tests for the global protections benchmark blueprint."""
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
    "build_global_protections_benchmark_blueprint",
    _ROOT / "scripts" / "build_global_protections_benchmark_blueprint.py",
)
source_matrix_builder = _load(
    "build_global_protections_source_channel_matrix",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_benchmark_blueprint_builds_blocked_tasks_and_dimensions():
    doc = builder.build_benchmark_blueprint()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["safe_for_project_planning"] is True
    assert summary["benchmark_axis_count"] == 7
    assert summary["task_blueprint_count"] == 7
    assert summary["blocked_task_blueprints"] == 7
    assert summary["scored_capability_count"] == 6
    assert summary["scoring_dimension_count"] == 6
    assert summary["abstention_rule_count"] == 5
    assert summary["source_review_row_count"] == 70
    assert summary["source_review_not_started_rows"] == 70
    assert summary["source_review_legal_claim_anchor_rows"] == 14
    assert summary["source_review_lead_only_claim_rows"] == 7
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    assert summary["task_source_grounding_contract_count"] == 7
    assert summary["tasks_requiring_legal_claim_anchor"] == 7
    assert summary["tasks_requiring_source_gap_marker"] == 7
    assert summary["tasks_barring_informal_standalone_claims"] == 7
    assert summary["tasks_requiring_temporal_validity"] == 7
    assert summary["tasks_requiring_language_access_review"] == 7
    assert summary["tasks_requiring_entity_resolution_review"] == 7
    assert summary["tasks_requiring_remedy_forum_review"] == 7
    assert summary["tasks_requiring_authority_hierarchy_review"] == 7
    assert summary["tasks_requiring_coverage_scope_review"] == 7
    assert summary["tasks_requiring_jurisdiction_chain_review"] == 7
    assert summary["tasks_requiring_implementation_status_review"] == 7
    assert summary["tasks_requiring_procedural_burden_review"] == 7
    assert summary["worker_prompt_count"] == 12
    assert summary["worker_prompts_blocked_for_comparable_run"] == 12
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_benchmark_blueprint_requires_source_review_before_prompt_instantiation():
    doc = builder.build_benchmark_blueprint()

    assert all(
        row["instantiation_status"] == "blocked_pending_source_review"
        for row in doc["task_blueprints"]
    )
    assert all(row["requires_reviewed_source_objects"] is True for row in doc["task_blueprints"])
    assert all(
        row["source_grounding_requirements"]["minimum_reviewed_legal_claim_anchor_sources"] == 1
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_source_gap_marker_when_anchor_missing"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_effective_or_current_as_of_note"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_supersession_check"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["publication_or_access_date_only_policy"]
        == "insufficient_for_current_law_claim"
        for row in doc["task_blueprints"]
    )
    assert all(
        "effective date, version range, or current-as-of note" in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all("supersession check status" in row["required_source_evidence"] for row in doc["task_blueprints"])
    assert all(
        row["source_grounding_requirements"]["requires_source_language_or_script_note"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_translation_review_when_not_working_language"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["machine_translation_only_policy"]
        == "context_only_requires_review_for_legal_claim"
        for row in doc["task_blueprints"]
    )
    assert all("source-language or script note" in row["required_source_evidence"] for row in doc["task_blueprints"])
    assert all(
        "translation, OCR, or transliteration review status" in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_entity_resolution_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_registry_or_license_status_basis_when_entity_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["entity_alias_or_name_match_policy"]
        == "claim_only_after_alias_collision_and_status_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "entity, alias, or registry/license status review when an entity claim is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_remedy_forum_scope_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_forum_competence_basis_when_remedy_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["remedy_or_complaint_path_policy"]
        == "claim_only_after_forum_competence_and_scope_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "remedy forum competence and routing basis when a remedy path is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_authority_hierarchy_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_controlling_source_basis_when_sources_conflict"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["lower_tier_source_policy"]
        == "context_only_unless_controlling_source_reviewed"
        for row in doc["task_blueprints"]
    )
    assert all(
        "authority tier and controlling-source basis when sources conflict"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_coverage_scope_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_worker_category_or_sector_basis_when_protection_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["coverage_scope_policy"]
        == "claim_only_after_worker_category_sector_and_status_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "worker category, sector, migration/status, and coverage eligibility basis when a protection is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_jurisdiction_chain_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_concrete_jurisdiction_role_basis_when_cross_border_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["jurisdiction_chain_policy"]
        == "claim_only_after_origin_destination_forum_flag_port_and_regulator_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "origin, destination, transit, forum, flag, port, regulator, contractor, buyer, or consular responsibility basis when cross-border responsibility is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_implementation_status_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_operational_availability_basis_when_practical_access_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["implementation_access_policy"]
        == "claim_only_after_operational_status_access_conditions_and_enforcement_path_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "implementation status, operational availability, access conditions, and enforcement-path basis when practical access is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["requires_procedural_burden_review"] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"][
            "requires_deadline_document_identity_and_evidence_basis_when_procedure_claimed"
        ] is True
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["procedural_burden_policy"]
        == "claim_only_after_deadline_document_identity_evidence_fee_and_filing_channel_review"
        for row in doc["task_blueprints"]
    )
    assert all(
        "deadlines, required documents, identity/access prerequisites, evidentiary burden, fees, translation/notarization, and filing-channel basis when a procedure is scored"
        in row["required_source_evidence"]
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["legal_claim_anchor_source_channel_ids"]
        == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        for row in doc["task_blueprints"]
    )
    assert all(
        row["source_grounding_requirements"]["informal_or_context_source_policy"]
        == "lead_or_context_only_never_standalone_legal_claim"
        for row in doc["task_blueprints"]
    )
    assert all("privacy review" in row["required_review_gates"] for row in doc["task_blueprints"])
    assert all("expert review" in row["required_review_gates"] for row in doc["task_blueprints"])
    informal_rows = [
        row
        for row in doc["task_blueprints"]
        if row["axis_id"].startswith("informal_publication_handling")
    ]
    assert len(informal_rows) == 1
    assert "public-interest review" in informal_rows[0]["required_review_gates"]
    assert "public-interest review passed" in informal_rows[0]["required_source_evidence"]


def test_benchmark_blueprint_is_privacy_safe_and_not_prompt_or_source_dump():
    doc = builder.build_benchmark_blueprint()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "prompt_text" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert doc["summary"]["consistency_ok"] is True


def test_benchmark_blueprint_markdown_lists_tasks_dimensions_and_abstention_rules():
    doc = builder.build_benchmark_blueprint()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Benchmark Blueprint" in rendered
    assert "Task blueprints" in rendered
    assert "Scoring dimensions" in rendered
    assert "Abstention rules" in rendered
    assert "Task source-grounding contracts" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Tasks barring informal standalone claims" in rendered
    assert "Tasks requiring temporal validity" in rendered
    assert "Tasks requiring language-access review" in rendered
    assert "Tasks requiring entity-resolution review" in rendered
    assert "Tasks requiring remedy/forum review" in rendered
    assert "Tasks requiring authority-hierarchy review" in rendered
    assert "Tasks requiring coverage-scope review" in rendered
    assert "Tasks requiring jurisdiction-chain review" in rendered
    assert "Tasks requiring implementation-status review" in rendered
    assert "Tasks requiring procedural-burden review" in rendered
    assert "missing_reviewed_local_law" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_benchmark_blueprint_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "benchmark_blueprint.json"
    md_out = tmp_path / "benchmark_blueprint.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "7 task blueprints" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["task_blueprint_count"] == 7
    assert md_out.exists()
    assert "# Global Protections Benchmark Blueprint" in md_out.read_text(encoding="utf-8")
