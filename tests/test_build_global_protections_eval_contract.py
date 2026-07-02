"""Tests for the global protections evaluation contract."""
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
    "build_global_protections_eval_contract",
    _ROOT / "scripts" / "build_global_protections_eval_contract.py",
)
source_matrix_builder = _load(
    "build_global_protections_source_channel_matrix_for_eval_contract_tests",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_eval_contract_builds_judge_schema_and_keeps_run_flags_blocked():
    doc = builder.build_eval_contract()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["task_blueprint_count"] == 7
    assert summary["task_source_grounding_contract_count"] == 7
    assert summary["tasks_requiring_legal_claim_anchor"] == 7
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
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
    assert summary["scoring_dimension_count"] == 6
    assert summary["judge_dimension_contract_count"] == 6
    assert summary["failure_mode_count"] == 16
    assert summary["critical_failure_mode_count"] == 2
    assert summary["run_gate_count"] == 18
    assert summary["model_response_record_field_count"] == 32
    assert summary["judge_output_field_count"] == 22
    assert summary["ready_for_model_response_capture"] is False
    assert summary["ready_for_judge_calibration"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_eval_contract_names_core_failure_modes_and_required_judge_fields():
    doc = builder.build_eval_contract()
    failure_ids = {row["id"] for row in doc["failure_modes"]}
    judge_fields = set(doc["judge_output_schema"]["fields"])

    assert "legal_authority_hallucination" in failure_ids
    assert "jurisdiction_scope_collapse" in failure_ids
    assert "cross_border_responsibility_miss" in failure_ids
    assert "implementation_access_overclaim" in failure_ids
    assert "procedural_burden_overclaim" in failure_ids
    assert "coverage_scope_overgeneralization" in failure_ids
    assert "international_anchor_substitution" in failure_ids
    assert "informal_source_overclaim" in failure_ids
    assert "authority_precedence_misread" in failure_ids
    assert "language_access_overclaim" in failure_ids
    assert "entity_identity_conflation" in failure_ids
    assert "remedy_forum_hallucination" in failure_ids
    assert "privacy_retaliation_leakage" in failure_ids
    assert "overconfident_non_abstention" in failure_ids
    assert "abstention_findings" in judge_fields
    assert "source_grounding_contract_findings" in judge_fields
    assert "temporal_validity_findings" in judge_fields
    assert "language_access_findings" in judge_fields
    assert "entity_resolution_findings" in judge_fields
    assert "authority_hierarchy_findings" in judge_fields
    assert "coverage_scope_findings" in judge_fields
    assert "jurisdiction_chain_findings" in judge_fields
    assert "implementation_access_findings" in judge_fields
    assert "procedural_burden_findings" in judge_fields
    assert "jurisdiction_scope_findings" in judge_fields
    assert "forum_competence_findings" in judge_fields
    assert "remedy_routing_findings" in judge_fields
    assert "privacy_and_retaliation_findings" in judge_fields
    assert "invented_authority_findings" in judge_fields

    response_fields = set(doc["model_response_record_schema"]["fields"])
    assert "legal_claim_anchor_source_object_ids" in response_fields
    assert "legal_claim_anchor_source_channel_ids" in response_fields
    assert "source_grounding_contract_status" in response_fields
    assert "source_temporal_validity_status" in response_fields
    assert "current_law_claim_basis" in response_fields
    assert "source_language_codes" in response_fields
    assert "translation_review_status" in response_fields
    assert "source_entity_resolution_status" in response_fields
    assert "registry_or_license_status_basis" in response_fields
    assert "remedy_forum_scope_status" in response_fields
    assert "remedy_or_complaint_path_basis" in response_fields
    assert "authority_hierarchy_review_status" in response_fields
    assert "controlling_source_basis" in response_fields
    assert "coverage_scope_review_status" in response_fields
    assert "worker_category_or_sector_basis" in response_fields
    assert "jurisdiction_chain_review_status" in response_fields
    assert "cross_border_responsibility_basis" in response_fields
    assert "implementation_status_review_status" in response_fields
    assert "operational_access_or_enforcement_basis" in response_fields
    assert "procedural_burden_review_status" in response_fields
    assert "deadline_document_or_evidence_basis" in response_fields


def test_eval_contract_judge_dimensions_cover_blueprint_dimensions():
    doc = builder.build_eval_contract()

    assert len(doc["judge_dimension_contracts"]) == 6
    assert all(
        "legal_authority_hallucination" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "informal_source_overclaim" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "international_anchor_substitution" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "date_version_hallucination" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "language_access_overclaim" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "entity_identity_conflation" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "remedy_forum_hallucination" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "authority_precedence_misread" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "coverage_scope_overgeneralization" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "cross_border_responsibility_miss" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "implementation_access_overclaim" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(
        "procedural_burden_overclaim" in row["must_penalize_failure_modes"]
        for row in doc["judge_dimension_contracts"]
    )
    assert all(row["ready_for_judge_calibration"] is False for row in doc["judge_dimension_contracts"])
    assert all(row["ready_for_comparable_scoring"] is False for row in doc["judge_dimension_contracts"])


def test_eval_contract_is_privacy_safe_and_not_prompt_or_source_dump():
    doc = builder.build_eval_contract()
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


def test_eval_contract_markdown_lists_schema_failure_modes_and_gates():
    doc = builder.build_eval_contract()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Evaluation Contract" in rendered
    assert "Model response record" in rendered
    assert "Judge output" in rendered
    assert "Task source-grounding contracts" in rendered
    assert "Tasks requiring temporal validity" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Tasks requiring language-access review" in rendered
    assert "Tasks requiring entity-resolution review" in rendered
    assert "Tasks requiring remedy/forum review" in rendered
    assert "Tasks requiring authority-hierarchy review" in rendered
    assert "Tasks requiring coverage-scope review" in rendered
    assert "Tasks requiring jurisdiction-chain review" in rendered
    assert "Tasks requiring implementation-status review" in rendered
    assert "Tasks requiring procedural-burden review" in rendered
    assert "source_grounding_contract_findings" in rendered
    assert "temporal_validity_findings" in rendered
    assert "language_access_findings" in rendered
    assert "entity_resolution_findings" in rendered
    assert "authority_hierarchy_findings" in rendered
    assert "coverage_scope_findings" in rendered
    assert "jurisdiction_chain_findings" in rendered
    assert "implementation_access_findings" in rendered
    assert "procedural_burden_findings" in rendered
    assert "forum_competence_findings" in rendered
    assert "remedy_routing_findings" in rendered
    assert "legal_authority_hallucination" in rendered
    assert "language_access_review" in rendered
    assert "entity_resolution_review" in rendered
    assert "remedy_forum_competence_review" in rendered
    assert "authority_hierarchy_review" in rendered
    assert "coverage_scope_review" in rendered
    assert "jurisdiction_chain_review" in rendered
    assert "implementation_access_review" in rendered
    assert "procedural_burden_review" in rendered
    assert "source_grounding_contract_review" in rendered
    assert "temporal_validity_review" in rendered
    assert "comparable_run_approval" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_eval_contract_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "eval_contract.json"
    md_out = tmp_path / "eval_contract.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "6 judge dimensions" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["judge_dimension_contract_count"] == 6
    assert md_out.exists()
    assert "# Global Protections Evaluation Contract" in md_out.read_text(encoding="utf-8")
