"""Tests for the global protections transition-gate validator."""
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
    "build_global_protections_transition_gate",
    _ROOT / "scripts" / "build_global_protections_transition_gate.py",
)
validator = _load(
    "validate_global_protections_transition_gate",
    _ROOT / "scripts" / "validate_global_protections_transition_gate.py",
)


def _gate_doc() -> dict:
    return builder.build_transition_gate()


def test_validator_accepts_current_transition_gate():
    report = validator.validate_transition_gate(_gate_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["transition_count"] == 9
    assert report["summary"]["blocked_transition_count"] == 9
    assert report["summary"]["source_grounding_transition_count"] == 4
    assert report["summary"]["temporal_validity_transition_count"] == 5
    assert report["summary"]["language_access_transition_count"] == 5
    assert report["summary"]["entity_resolution_transition_count"] == 5
    assert report["summary"]["remedy_forum_transition_count"] == 5
    assert report["summary"]["authority_hierarchy_transition_count"] == 5
    assert report["summary"]["coverage_scope_transition_count"] == 5
    assert report["summary"]["jurisdiction_chain_transition_count"] == 5
    assert report["summary"]["implementation_access_transition_count"] == 5
    assert report["summary"]["procedural_burden_transition_count"] == 5
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["transitions_preserving_legal_anchor_source_channels"] == 9
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_unblocked_transition_without_current_chain():
    doc = _gate_doc()
    doc["transitions"][0]["status"] = "approved"
    doc["summary"]["blocked_transition_count"] = 8

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "transition_row_shape" in report["summary"]["failed_check_ids"]
    assert "all_transitions_remain_blocked" in report["summary"]["failed_check_ids"]
    assert "transition_gate_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_model_capture_and_scoring_drift_without_current_chain():
    doc = _gate_doc()
    doc["transitions"][2]["ready_for_model_response_capture"] = True
    doc["transitions"][7]["ready_for_comparable_scoring"] = True
    doc["summary"]["ready_for_model_response_capture"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_transitions_remain_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_transition_row_without_current_chain():
    doc = _gate_doc()
    doc["transitions"].pop(1)

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "transition_keys_match_contract" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_transitions" in report["summary"]["failed_check_ids"]


def test_validator_rejects_gate_count_drift_without_current_chain():
    doc = _gate_doc()
    doc["transitions"][0]["temporal_validity_gate"] = False

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_transitions" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _gate_doc()
    doc["transitions"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "transition_row_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_transitions" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_prompt_or_source_dump_without_current_chain():
    doc = _gate_doc()
    doc["transitions"][0]["required_evidence"].append(
        "prompt_text copied from source_url at https://example.invalid/source"
    )

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "gate_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_malformed_transition_shape_without_current_chain():
    doc = _gate_doc()
    row = doc["transitions"][0]
    row["transition_url"] = "redacted"
    row.pop("required_evidence")

    report = validator.validate_transition_gate(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "transition_row_shape" in report["summary"]["failed_check_ids"]


def test_validator_rejects_empty_transition_labels_without_current_chain():
    doc = _gate_doc()
    row = doc["transitions"][0]
    row["from_state"] = " "
    row["to_state"] = None

    report = validator.validate_transition_gate(doc, compare_current_chain=False)
    shape = next(check for check in report["checks"] if check["id"] == "transition_row_shape")
    rules = {finding["rule"] for finding in shape["actual"] if "rule" in finding}

    assert report["summary"]["valid"] is False
    assert "transition_row_shape" in report["summary"]["failed_check_ids"]
    assert "from_state_non_empty_string" in rules
    assert "to_state_non_empty_string" in rules


def test_validator_rejects_non_string_transition_lists_without_current_chain():
    doc = _gate_doc()
    row = doc["transitions"][0]
    row["blocked_by"].append("")
    row["required_evidence"].append({"note": "not a plain evidence string"})
    row["required_legal_claim_anchor_source_channel_ids"] = [
        "official_gazette_or_law_portal",
        12,
    ]

    report = validator.validate_transition_gate(doc, compare_current_chain=False)
    shape = next(check for check in report["checks"] if check["id"] == "transition_row_shape")
    rules = {finding["rule"] for finding in shape["actual"] if "rule" in finding}

    assert report["summary"]["valid"] is False
    assert "transition_row_shape" in report["summary"]["failed_check_ids"]
    assert "blocked_by_items_non_empty_strings" in rules
    assert "required_evidence_items_non_empty_strings" in rules
    assert "required_legal_claim_anchor_source_channel_ids_items_non_empty_strings" in rules


def test_render_markdown_reports_failed_ids():
    doc = _gate_doc()
    doc["transitions"][0]["ready_for_judge_output"] = True
    report = validator.validate_transition_gate(doc)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Transition Gate Validation" in rendered
    assert "all_transitions_remain_blocked" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    gate_path = tmp_path / "global_protections_transition_gate.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    gate_path.write_text(json.dumps(_gate_doc()), encoding="utf-8")

    assert validator.main(["--gate", str(gate_path), "--validate"]) == 0
    assert validator.main([
        "--gate",
        str(gate_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_gate(tmp_path):
    doc = _gate_doc()
    doc["transitions"][0]["ready_for_comparable_scoring"] = True
    gate_path = tmp_path / "global_protections_transition_gate.json"
    out = tmp_path / "validation.json"
    gate_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main(["--gate", str(gate_path), "--out", str(out), "--no-current-chain"]) == 1
    assert out.exists()
