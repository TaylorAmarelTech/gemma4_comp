"""Tests for the global protections evaluation-contract validator."""
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
validator = _load(
    "validate_global_protections_eval_contract",
    _ROOT / "scripts" / "validate_global_protections_eval_contract.py",
)


def _contract_doc() -> dict:
    return builder.build_eval_contract()


def test_validator_accepts_current_eval_contract():
    report = validator.validate_eval_contract(_contract_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["judge_dimension_contract_count"] == 6
    assert report["summary"]["failure_mode_count"] == 16
    assert report["summary"]["run_gate_count"] == 18
    assert report["summary"]["model_response_record_field_count"] == 32
    assert report["summary"]["judge_output_field_count"] == 22
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["ready_for_model_response_capture"] is False
    assert report["summary"]["ready_for_judge_calibration"] is False
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_capture_and_scoring_drift_without_current_chain():
    doc = _contract_doc()
    doc["summary"]["ready_for_model_response_capture"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "eval_contract_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_model_response_grounding_field_without_current_chain():
    doc = _contract_doc()
    doc["model_response_record_schema"]["fields"].remove("source_grounding_contract_status")

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "model_response_record_schema_fields" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _contract_doc()
    doc["summary"]["legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_legal_anchor_source_channel_field_without_current_chain():
    doc = _contract_doc()
    doc["model_response_record_schema"]["fields"].remove("legal_claim_anchor_source_channel_ids")

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "model_response_record_schema_fields" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_judge_output_grounding_field_without_current_chain():
    doc = _contract_doc()
    doc["judge_output_schema"]["fields"].remove("source_grounding_contract_findings")

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "judge_output_schema_fields" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]


def test_validator_rejects_failure_mode_removal_without_current_chain():
    doc = _contract_doc()
    doc["failure_modes"].pop()

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "failure_modes_match_contract" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_contract" in report["summary"]["failed_check_ids"]


def test_validator_rejects_dimension_promotion_without_current_chain():
    doc = _contract_doc()
    doc["judge_dimension_contracts"][0]["ready_for_judge_calibration"] = True
    doc["judge_dimension_contracts"][0]["ready_for_comparable_scoring"] = True

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "judge_dimension_contract_shape" in report["summary"]["failed_check_ids"]
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_prompt_or_source_dump_without_current_chain():
    doc = _contract_doc()
    doc["model_response_record_schema"]["policy"] += (
        " Do not copy prompt_text from source_url at https://example.invalid/source."
    )

    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "eval_contract_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _contract_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_eval_contract(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Evaluation Contract Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    contract_path = tmp_path / "global_protections_eval_contract.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    contract_path.write_text(json.dumps(_contract_doc()), encoding="utf-8")

    assert validator.main(["--contract", str(contract_path), "--validate"]) == 0
    assert validator.main([
        "--contract",
        str(contract_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_contract(tmp_path):
    doc = _contract_doc()
    doc["judge_output_schema"]["fields"].remove("privacy_and_retaliation_findings")
    contract_path = tmp_path / "global_protections_eval_contract.json"
    out = tmp_path / "validation.json"
    contract_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--contract",
        str(contract_path),
        "--out",
        str(out),
        "--no-current-chain",
    ]) == 1
    assert out.exists()
