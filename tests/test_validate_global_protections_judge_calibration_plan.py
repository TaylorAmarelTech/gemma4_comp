"""Tests for the global protections judge-calibration-plan validator."""
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
validator = _load(
    "validate_global_protections_judge_calibration_plan",
    _ROOT / "scripts" / "validate_global_protections_judge_calibration_plan.py",
)


def _plan_doc() -> dict:
    return builder.build_judge_calibration_plan()


def test_validator_accepts_current_judge_calibration_plan():
    report = validator.validate_judge_calibration_plan(_plan_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["calibration_case_count"] == 16
    assert report["summary"]["blocked_calibration_cases"] == 16
    assert report["summary"]["source_grounding_calibration_cases"] == 14
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["ready_for_example_creation"] is False
    assert report["summary"]["ready_for_judge_calibration"] is False
    assert report["summary"]["ready_for_model_response_capture"] is False
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_calibration_readiness_drift_without_current_chain():
    doc = _plan_doc()
    doc["summary"]["ready_for_example_creation"] = True
    doc["summary"]["ready_for_judge_calibration"] = True
    doc["calibration_cases"][0]["status"] = "ready_for_calibration"
    doc["calibration_cases"][0]["ready_for_example_creation"] = True
    doc["calibration_cases"][0]["ready_for_judge_calibration"] = True

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_plan" in report["summary"]["failed_check_ids"]
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "judge_calibration_plan_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_calibration_case_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"].pop()

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_plan" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_model_response_anchor_field_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["required_model_response_fields"].remove(
        "legal_claim_anchor_source_object_ids"
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_judge_source_finding_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["required_judge_output_findings"].remove(
        "source_grounding_contract_findings"
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_precondition_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["required_before_calibration"].remove(
        "reviewed source-object identifiers or source-gap markers"
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_judge_obligation_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["expected_judge_obligations"].remove(
        "check legal-claim anchor source IDs before accepting legal certainty"
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_grounding_focus_drift_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["source_grounding_focus"] = False

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_case_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_plan" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_prompt_or_response_dump_without_current_chain():
    doc = _plan_doc()
    doc["calibration_cases"][0]["expected_judge_obligations"].append(
        "Never paste response_text from source_url at https://example.invalid/source."
    )

    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "calibration_plan_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _plan_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_judge_calibration_plan(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Judge Calibration Plan Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    plan_path = tmp_path / "global_protections_judge_calibration_plan.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    plan_path.write_text(json.dumps(_plan_doc()), encoding="utf-8")

    assert validator.main(["--plan", str(plan_path), "--validate"]) == 0
    assert validator.main([
        "--plan",
        str(plan_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_plan(tmp_path):
    doc = _plan_doc()
    doc["calibration_cases"][0]["ready_for_comparable_scoring"] = True
    plan_path = tmp_path / "global_protections_judge_calibration_plan.json"
    out = tmp_path / "validation.json"
    plan_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--plan",
        str(plan_path),
        "--out",
        str(out),
        "--no-current-chain",
    ]) == 1
    assert out.exists()
