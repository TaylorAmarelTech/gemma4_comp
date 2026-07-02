"""Tests for the global protections next-actions validator."""
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
    "build_global_protections_next_actions",
    _ROOT / "scripts" / "build_global_protections_next_actions.py",
)
validator = _load(
    "validate_global_protections_next_actions",
    _ROOT / "scripts" / "validate_global_protections_next_actions.py",
)


def _backlog_doc() -> dict:
    return builder.build_next_actions()


def test_validator_accepts_current_next_actions_backlog():
    report = validator.validate_next_actions(_backlog_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["action_count"] == 34
    assert report["summary"]["execution_phase_count"] == 5
    assert report["summary"]["execution_phase_covered_action_count"] == 34
    assert report["summary"]["immediate_action_count"] == 24
    assert report["summary"]["blocked_action_count"] == 10
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["actions_preserving_legal_anchor_source_channels"] == 34
    assert report["summary"]["execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert report["summary"]["regulatory_top_candidate_id"]
    assert report["summary"]["ready_for_prompt_generation"] is False
    assert report["summary"]["ready_for_worker_facing_use"] is False
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_readiness_drift_without_current_chain():
    doc = _backlog_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    doc["actions"][0]["ready_for_comparable_scoring"] = True

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "next_actions_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_action_count_drift_without_current_chain():
    doc = _backlog_doc()
    doc["summary"]["action_count"] = 99

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_actions" in report["summary"]["failed_check_ids"]


def test_validator_rejects_execution_phase_drift_without_current_chain():
    doc = _backlog_doc()
    doc["execution_phases"][0]["action_ids"].pop()

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "execution_phases_shape" in report["summary"]["failed_check_ids"]
    assert "phase_action_ids_cover_actions" in json.dumps(report["checks"], ensure_ascii=False)


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _backlog_doc()
    doc["actions"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )
    doc["execution_phases"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "action_shape" in report["summary"]["failed_check_ids"]
    assert "execution_phases_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_actions" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_required_check_without_current_chain():
    doc = _backlog_doc()
    doc["checks"] = [
        check for check in doc["checks"] if check["id"] != "regulatory_top_candidate_first"
    ]

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "embedded_checks_all_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_regulatory_rank_drift_without_current_chain():
    doc = _backlog_doc()
    regulatory = [
        action for action in doc["actions"] if action["item_type"] == "candidate_domain_intake"
    ]
    regulatory[0]["expansion_rank"] = 2

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "regulatory_rank_order_intact" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_payload_or_url_dump_without_current_chain():
    doc = _backlog_doc()
    doc["source_object_queue"] = [{
        "source_url": "https://example.invalid/private-case",
        "notes": "synthetic worker@example.invalid contact must not be copied",
    }]

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "top_level_shape" in report["summary"]["failed_check_ids"]
    assert "raw_payload_sections_absent" in report["summary"]["failed_check_ids"]
    assert "next_actions_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unsafe_artifact_path_without_current_chain():
    doc = _backlog_doc()
    doc["artifact_paths"]["global_protections_next_actions_json"] = "https://example.invalid/actions.json"

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_are_handoff_safe" in report["summary"]["failed_check_ids"]
    assert "next_actions_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_validator_rejects_local_absolute_artifact_paths_without_current_chain():
    doc = _backlog_doc()
    doc["artifact_paths"]["project_plan_json"] = "C:/Users/example/project.json"
    doc["artifact_paths"]["domain_curation_bundle_json"] = "/tmp/domain.json"
    doc["artifact_paths"]["regulatory_curation_bundle_json"] = "../reports/regulatory.json"

    report = validator.validate_next_actions(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_are_handoff_safe" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _backlog_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_next_actions(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Next Actions Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Phase-covered actions" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    backlog_path = tmp_path / "global_protections_next_actions.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    backlog_path.write_text(json.dumps(_backlog_doc()), encoding="utf-8")

    assert validator.main(["--backlog", str(backlog_path), "--validate"]) == 0
    assert validator.main([
        "--backlog",
        str(backlog_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert "phase_coverage=5/34" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_backlog(tmp_path):
    doc = _backlog_doc()
    doc["summary"]["action_count"] = 999
    backlog_path = tmp_path / "global_protections_next_actions.json"
    out = tmp_path / "validation.json"
    backlog_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--backlog",
        str(backlog_path),
        "--out",
        str(out),
        "--no-current-chain",
    ]) == 1
    assert out.exists()
