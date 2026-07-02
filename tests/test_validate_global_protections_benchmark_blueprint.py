"""Tests for the global protections benchmark-blueprint validator."""
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
validator = _load(
    "validate_global_protections_benchmark_blueprint",
    _ROOT / "scripts" / "validate_global_protections_benchmark_blueprint.py",
)


def _blueprint_doc() -> dict:
    return builder.build_benchmark_blueprint()


def test_validator_accepts_current_benchmark_blueprint():
    report = validator.validate_benchmark_blueprint(_blueprint_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["task_blueprint_count"] == 7
    assert report["summary"]["blocked_task_blueprints"] == 7
    assert report["summary"]["scoring_dimension_count"] == 6
    assert report["summary"]["abstention_rule_count"] == 5
    assert report["summary"]["task_source_grounding_contract_count"] == 7
    assert report["summary"]["tasks_requiring_legal_claim_anchor"] == 7
    assert report["summary"]["tasks_requiring_source_gap_marker"] == 7
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_prompt_and_scoring_drift_without_current_chain():
    doc = _blueprint_doc()
    doc["task_blueprints"][0]["ready_for_prompt_generation"] = True
    doc["scoring_dimension_blueprints"][0]["ready_for_comparable_scoring"] = True
    doc["summary"]["ready_for_prompt_generation"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "dimension_shape" in report["summary"]["failed_check_ids"]
    assert "benchmark_blueprint_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_weakened_grounding_contract_without_current_chain():
    doc = _blueprint_doc()
    grounding = doc["task_blueprints"][0]["source_grounding_requirements"]
    grounding["requires_source_gap_marker_when_anchor_missing"] = False
    doc["task_blueprints"][0]["required_source_evidence"].remove("supersession check status")

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_grounding_contracts_intact" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_blueprint" in report["summary"]["failed_check_ids"]


def test_validator_rejects_broadened_legal_anchor_channels_without_current_chain():
    doc = _blueprint_doc()
    grounding = doc["task_blueprints"][0]["source_grounding_requirements"]
    grounding["legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_grounding_contracts_intact" in report["summary"]["failed_check_ids"]
    assert (
        "legal_claim_anchor_channels_match_source_matrix"
        in report["summary"]["failed_check_ids"]
    )


def test_validator_rejects_missing_task_blueprint_without_current_chain():
    doc = _blueprint_doc()
    doc["task_blueprints"].pop()

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_blueprint" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_abstention_rule_without_current_chain():
    doc = _blueprint_doc()
    doc["abstention_rules"].pop()

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "abstention_rules_match_contract" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_blueprint" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_prompt_or_source_dump_without_current_chain():
    doc = _blueprint_doc()
    doc["task_blueprints"][0]["expected_good_behavior"].append(
        "Use prompt_text copied from source_url at https://example.invalid/source"
    )

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "blueprint_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_malformed_task_shape_without_current_chain():
    doc = _blueprint_doc()
    row = doc["task_blueprints"][0]
    row["candidate_url"] = "redacted"
    row.pop("required_review_gates")

    report = validator.validate_benchmark_blueprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "task_blueprint_shape" in report["summary"]["failed_check_ids"]
    assert "blueprint_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _blueprint_doc()
    doc["task_blueprints"][0]["ready_for_training_use"] = True
    report = validator.validate_benchmark_blueprint(doc)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Benchmark Blueprint Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    blueprint_path = tmp_path / "global_protections_benchmark_blueprint.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    blueprint_path.write_text(json.dumps(_blueprint_doc()), encoding="utf-8")

    assert validator.main(["--blueprint", str(blueprint_path), "--validate"]) == 0
    assert validator.main([
        "--blueprint",
        str(blueprint_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_blueprint(tmp_path):
    doc = _blueprint_doc()
    doc["task_blueprints"][0]["ready_for_comparable_scoring"] = True
    blueprint_path = tmp_path / "global_protections_benchmark_blueprint.json"
    out = tmp_path / "validation.json"
    blueprint_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--blueprint",
        str(blueprint_path),
        "--out",
        str(out),
        "--no-current-chain",
    ]) == 1
    assert out.exists()
