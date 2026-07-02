"""Tests for the global protections diagnostic run plan."""
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
    "build_global_protections_diagnostic_run_plan",
    _ROOT / "scripts" / "build_global_protections_diagnostic_run_plan.py",
)


def test_diagnostic_run_plan_builds_blocked_cells_from_task_blueprints():
    doc = builder.build_diagnostic_run_plan()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["task_blueprint_count"] == 7
    assert summary["diagnostic_cell_count"] == 7
    assert summary["blocked_diagnostic_cells"] == 7
    assert summary["run_gate_count"] == 18
    assert summary["failure_mode_count"] == 16
    assert summary["core_failure_modes_per_cell"] == 15
    assert summary["model_response_record_field_count"] == 32
    assert summary["judge_output_field_count"] == 22
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["ready_for_task_instantiation"] is False
    assert summary["ready_for_model_response_capture"] is False
    assert summary["ready_for_judge_calibration"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_diagnostic_cells_include_required_gates_and_failure_checks():
    doc = builder.build_diagnostic_run_plan()
    cells = doc["diagnostic_cells"]

    assert len(cells) == 7
    assert all(row["status"] == "blocked_pending_source_review" for row in cells)
    assert all(row["execution_mode"] == "dry_run_plan_only" for row in cells)
    assert all("reviewed_source_objects_present" in row["required_run_gate_ids"] for row in cells)
    assert all("source_grounding_contract_review" in row["required_run_gate_ids"] for row in cells)
    assert all("temporal_validity_review" in row["required_run_gate_ids"] for row in cells)
    assert all("language_access_review" in row["required_run_gate_ids"] for row in cells)
    assert all("entity_resolution_review" in row["required_run_gate_ids"] for row in cells)
    assert all("remedy_forum_competence_review" in row["required_run_gate_ids"] for row in cells)
    assert all("authority_hierarchy_review" in row["required_run_gate_ids"] for row in cells)
    assert all("coverage_scope_review" in row["required_run_gate_ids"] for row in cells)
    assert all("jurisdiction_chain_review" in row["required_run_gate_ids"] for row in cells)
    assert all("implementation_access_review" in row["required_run_gate_ids"] for row in cells)
    assert all("procedural_burden_review" in row["required_run_gate_ids"] for row in cells)
    assert all("reviewed_source_object_ids" in row["required_model_response_fields"] for row in cells)
    assert all("legal_claim_anchor_source_object_ids" in row["required_model_response_fields"] for row in cells)
    assert all("legal_claim_anchor_source_channel_ids" in row["required_model_response_fields"] for row in cells)
    assert all(
        row["required_legal_claim_anchor_source_channel_ids"]
        == ["official_gazette_or_law_portal", "labour_or_migration_ministry_notice"]
        for row in cells
    )
    assert all("source_grounding_contract_status" in row["required_model_response_fields"] for row in cells)
    assert all("source_temporal_validity_status" in row["required_model_response_fields"] for row in cells)
    assert all("current_law_claim_basis" in row["required_model_response_fields"] for row in cells)
    assert all("source_language_codes" in row["required_model_response_fields"] for row in cells)
    assert all("translation_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("source_entity_resolution_status" in row["required_model_response_fields"] for row in cells)
    assert all("registry_or_license_status_basis" in row["required_model_response_fields"] for row in cells)
    assert all("remedy_forum_scope_status" in row["required_model_response_fields"] for row in cells)
    assert all("remedy_or_complaint_path_basis" in row["required_model_response_fields"] for row in cells)
    assert all("authority_hierarchy_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("controlling_source_basis" in row["required_model_response_fields"] for row in cells)
    assert all("coverage_scope_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("worker_category_or_sector_basis" in row["required_model_response_fields"] for row in cells)
    assert all("jurisdiction_chain_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("cross_border_responsibility_basis" in row["required_model_response_fields"] for row in cells)
    assert all("implementation_status_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("operational_access_or_enforcement_basis" in row["required_model_response_fields"] for row in cells)
    assert all("procedural_burden_review_status" in row["required_model_response_fields"] for row in cells)
    assert all("deadline_document_or_evidence_basis" in row["required_model_response_fields"] for row in cells)
    assert all("abstention_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("source_grounding_contract_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("temporal_validity_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("language_access_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("entity_resolution_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("authority_hierarchy_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("coverage_scope_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("jurisdiction_chain_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("jurisdiction_scope_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("implementation_access_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("procedural_burden_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("forum_competence_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("remedy_routing_findings" in row["required_judge_output_fields"] for row in cells)
    assert all("legal_authority_hallucination" in row["failure_modes_to_check"] for row in cells)
    assert all("language_access_overclaim" in row["failure_modes_to_check"] for row in cells)
    assert all("entity_identity_conflation" in row["failure_modes_to_check"] for row in cells)
    assert all("remedy_forum_hallucination" in row["failure_modes_to_check"] for row in cells)
    assert all("authority_precedence_misread" in row["failure_modes_to_check"] for row in cells)
    assert all("coverage_scope_overgeneralization" in row["failure_modes_to_check"] for row in cells)
    assert all("cross_border_responsibility_miss" in row["failure_modes_to_check"] for row in cells)
    assert all("implementation_access_overclaim" in row["failure_modes_to_check"] for row in cells)
    assert all("procedural_burden_overclaim" in row["failure_modes_to_check"] for row in cells)
    assert all("privacy_retaliation_leakage" in row["failure_modes_to_check"] for row in cells)


def test_diagnostic_run_plan_is_privacy_safe_and_not_prompt_or_response_dump():
    doc = builder.build_diagnostic_run_plan()
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


def test_diagnostic_run_plan_markdown_lists_cells_and_non_scoring_rule():
    doc = builder.build_diagnostic_run_plan()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Diagnostic Run Plan" in rendered
    assert "Diagnostic cells" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "blocked_pending_source_review" in rendered
    assert "Ready for model response capture" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_diagnostic_run_plan_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "diagnostic_run_plan.json"
    md_out = tmp_path / "diagnostic_run_plan.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "7 diagnostic cells" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["diagnostic_cell_count"] == 7
    assert md_out.exists()
    assert "# Global Protections Diagnostic Run Plan" in md_out.read_text(encoding="utf-8")
