"""Tests for the global protections judge-calibration plan."""
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
    "build_global_protections_judge_calibration_plan",
    _ROOT / "scripts" / "build_global_protections_judge_calibration_plan.py",
)
source_matrix_builder = _load(
    "build_global_protections_source_channel_matrix_for_judge_calibration_tests",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_judge_calibration_plan_builds_blocked_cases_for_failure_modes():
    doc = builder.build_judge_calibration_plan()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["failure_mode_count"] == 16
    assert summary["calibration_case_count"] == 16
    assert summary["blocked_calibration_cases"] == 16
    assert summary["judge_dimension_contract_count"] == 6
    assert summary["diagnostic_cell_count"] == 7
    assert summary["critical_calibration_cases"] == 2
    assert summary["source_grounding_failure_mode_count"] == 14
    assert summary["source_grounding_calibration_cases"] == 14
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    assert summary["cases_requiring_source_grounding_findings"] == 16
    assert summary["cases_requiring_legal_anchor_or_gap"] == 16
    assert summary["cases_requiring_legal_anchor_source_channels"] == 16
    assert summary["cases_requiring_temporal_validity_fields"] == 16
    assert summary["cases_requiring_temporal_validity_findings"] == 16
    assert summary["cases_requiring_language_access_fields"] == 16
    assert summary["cases_requiring_language_access_findings"] == 16
    assert summary["cases_requiring_entity_resolution_fields"] == 16
    assert summary["cases_requiring_entity_resolution_findings"] == 16
    assert summary["cases_requiring_remedy_forum_fields"] == 16
    assert summary["cases_requiring_remedy_forum_findings"] == 16
    assert summary["cases_requiring_authority_hierarchy_fields"] == 16
    assert summary["cases_requiring_authority_hierarchy_findings"] == 16
    assert summary["cases_requiring_coverage_scope_fields"] == 16
    assert summary["cases_requiring_coverage_scope_findings"] == 16
    assert summary["cases_requiring_jurisdiction_chain_fields"] == 16
    assert summary["cases_requiring_jurisdiction_chain_findings"] == 16
    assert summary["cases_requiring_implementation_access_fields"] == 16
    assert summary["cases_requiring_implementation_access_findings"] == 16
    assert summary["cases_requiring_procedural_burden_fields"] == 16
    assert summary["cases_requiring_procedural_burden_findings"] == 16
    assert summary["ready_for_example_creation"] is False
    assert summary["ready_for_judge_calibration"] is False
    assert summary["ready_for_model_response_capture"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_judge_calibration_cases_require_reviewed_examples_and_source_controls():
    doc = builder.build_judge_calibration_plan()
    cases = doc["calibration_cases"]

    assert len(cases) == 16
    assert all(row["status"] == "blocked_pending_reviewed_examples" for row in cases)
    assert all(row["calibration_mode"] == "failure_mode_probe" for row in cases)
    assert all(len(row["judge_dimension_contract_ids"]) == 6 for row in cases)
    assert all(len(row["diagnostic_cell_ids"]) == 7 for row in cases)
    assert all(
        "reviewed source-object identifiers or source-gap markers" in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "legal-claim anchor source identifiers or explicit source-gap markers"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "legal-claim anchor source-channel allowlist matched to source matrix"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all("legal_claim_anchor_source_object_ids" in row["required_model_response_fields"] for row in cases)
    assert all("legal_claim_anchor_source_channel_ids" in row["required_model_response_fields"] for row in cases)
    assert all(
        row["required_legal_claim_anchor_source_channel_ids"]
        == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        for row in cases
    )
    assert all("source_grounding_contract_status" in row["required_model_response_fields"] for row in cases)
    assert all("source_temporal_validity_status" in row["required_model_response_fields"] for row in cases)
    assert all("current_law_claim_basis" in row["required_model_response_fields"] for row in cases)
    assert all("source_language_codes" in row["required_model_response_fields"] for row in cases)
    assert all("translation_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("source_entity_resolution_status" in row["required_model_response_fields"] for row in cases)
    assert all("registry_or_license_status_basis" in row["required_model_response_fields"] for row in cases)
    assert all("remedy_forum_scope_status" in row["required_model_response_fields"] for row in cases)
    assert all("remedy_or_complaint_path_basis" in row["required_model_response_fields"] for row in cases)
    assert all("authority_hierarchy_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("controlling_source_basis" in row["required_model_response_fields"] for row in cases)
    assert all("coverage_scope_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("worker_category_or_sector_basis" in row["required_model_response_fields"] for row in cases)
    assert all("jurisdiction_chain_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("cross_border_responsibility_basis" in row["required_model_response_fields"] for row in cases)
    assert all("implementation_status_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("operational_access_or_enforcement_basis" in row["required_model_response_fields"] for row in cases)
    assert all("procedural_burden_review_status" in row["required_model_response_fields"] for row in cases)
    assert all("deadline_document_or_evidence_basis" in row["required_model_response_fields"] for row in cases)
    assert all("source_grounding_contract_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("temporal_validity_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("language_access_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("entity_resolution_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("authority_hierarchy_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("coverage_scope_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("jurisdiction_chain_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("jurisdiction_scope_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("implementation_access_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("procedural_burden_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("forum_competence_findings" in row["required_judge_output_findings"] for row in cases)
    assert all("remedy_routing_findings" in row["required_judge_output_findings"] for row in cases)
    assert all(
        "confirm legal-claim anchor source channels are allowed before accepting legal certainty"
        in row["expected_judge_obligations"]
        for row in cases
    )
    assert all(
        "effective/current-as-of and supersession expectations" in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "source-language and translation/OCR/transliteration expectations" in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "entity identity, alias, and registry/license-status expectations" in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "remedy forum competence and complaint-path expectations" in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "authority hierarchy, controlling-source, and source-conflict expectations"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "worker-category, sector, status, and coverage-scope expectations"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "origin, destination, forum, flag, port, regulator, and responsibility-chain expectations"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "implementation status, operational availability, access-condition, and enforcement-path expectations"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all(
        "deadline, required-document, identity/access prerequisite, evidence, fee, translation/notarization, and filing-channel expectations"
        in row["required_before_calibration"]
        for row in cases
    )
    assert all("privacy and retaliation screen" in row["required_before_calibration"] for row in cases)
    source_grounding_ids = {
        row["failure_mode_id"] for row in cases if row["source_grounding_focus"]
    }
    assert source_grounding_ids == {
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
    }


def test_judge_calibration_plan_is_privacy_safe_and_not_example_or_response_dump():
    doc = builder.build_judge_calibration_plan()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "prompt_text" not in encoded
    assert "model_response_text" not in encoded
    assert "response_text" not in encoded
    assert "unredacted_response" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert doc["summary"]["consistency_ok"] is True


def test_judge_calibration_plan_markdown_lists_cases_and_non_scoring_rule():
    doc = builder.build_judge_calibration_plan()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Judge Calibration Plan" in rendered
    assert "Calibration cases" in rendered
    assert "Source-grounding calibration cases" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Cases requiring legal-anchor source channels" in rendered
    assert "Cases requiring temporal-validity fields" in rendered
    assert "Cases requiring language-access fields" in rendered
    assert "Cases requiring entity-resolution fields" in rendered
    assert "Cases requiring remedy/forum fields" in rendered
    assert "Cases requiring authority-hierarchy fields" in rendered
    assert "Cases requiring coverage-scope fields" in rendered
    assert "Cases requiring jurisdiction-chain fields" in rendered
    assert "Cases requiring implementation-access fields" in rendered
    assert "Cases requiring procedural-burden fields" in rendered
    assert "legal_authority_hallucination" in rendered
    assert "blocked_pending_reviewed_examples" in rendered
    assert "Ready for judge calibration" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_judge_calibration_plan_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "judge_calibration_plan.json"
    md_out = tmp_path / "judge_calibration_plan.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "16 calibration cases" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["calibration_case_count"] == 16
    assert md_out.exists()
    assert "# Global Protections Judge Calibration Plan" in md_out.read_text(encoding="utf-8")
