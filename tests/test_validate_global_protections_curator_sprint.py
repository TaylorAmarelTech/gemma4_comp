"""Tests for the global protections curator-sprint validator."""
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
    "build_global_protections_curator_sprint",
    _ROOT / "scripts" / "build_global_protections_curator_sprint.py",
)
validator = _load(
    "validate_global_protections_curator_sprint",
    _ROOT / "scripts" / "validate_global_protections_curator_sprint.py",
)


def _sprint_doc() -> dict:
    return builder.build_curator_sprint()


def test_validator_accepts_current_curator_sprint():
    report = validator.validate_curator_sprint(_sprint_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["sprint_item_count"] == 24
    assert report["summary"]["execution_phase_count"] == 5
    assert report["summary"]["execution_phase_covered_action_count"] == 34
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["sprint_items_preserving_legal_anchor_source_channels"] == 24
    assert report["summary"]["blocked_later_items_preserving_legal_anchor_source_channels"] == 10
    assert report["summary"]["execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert report["summary"]["regulatory_priority_queue_items"] == 10
    assert report["summary"]["regulatory_top_candidate_id"]
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_prompt_generation_and_scoring_drift():
    doc = _sprint_doc()
    doc["summary"]["ready_for_prompt_generation"] = True
    doc["regulatory_candidate_intake_items"][0]["readiness"]["ready_for_comparable_scoring"] = True

    report = validator.validate_curator_sprint(doc)

    assert report["summary"]["valid"] is False
    assert "all_prompt_and_scoring_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" in report["summary"]["failed_check_ids"]


def test_validator_rejects_regulatory_rank_drift_without_current_chain():
    doc = _sprint_doc()
    doc["regulatory_candidate_intake_items"][0]["expansion_rank"] = 2
    doc["regulatory_candidate_intake_items"][0]["is_top_candidate"] = False

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "regulatory_priority_queue_valid" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_source_promotion_drift_without_current_chain():
    doc = _sprint_doc()
    doc["source_review_items"][0]["ready_for_manifest_promotion"] = True

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_review_rows_still_unpromoted" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_url_dump_without_current_chain():
    doc = _sprint_doc()
    doc["scope_resolution_items"][0]["source_url"] = "https://example.invalid/private-case"

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "sprint_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_count_drift_without_current_chain():
    doc = _sprint_doc()
    doc["summary"]["sprint_item_count"] = 1

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_sections" in report["summary"]["failed_check_ids"]


def test_validator_rejects_execution_phase_summary_drift_without_current_chain():
    doc = _sprint_doc()
    doc["execution_phase_summary"][0]["sprint_action_ids"].pop()

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "execution_phase_summary_valid" in report["summary"]["failed_check_ids"]
    assert "phase_action_ids_cover_sprint_packet" in json.dumps(report["checks"], ensure_ascii=False)


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _sprint_doc()
    doc["scope_resolution_items"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )
    doc["execution_phase_summary"][0]["required_legal_claim_anchor_source_channel_ids"].append(
        "social_channel_notice_or_scanned_circular"
    )

    report = validator.validate_curator_sprint(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "legal_claim_anchor_source_channels_preserved" in report["summary"]["failed_check_ids"]
    rendered_checks = json.dumps(report["checks"], ensure_ascii=False)
    assert "sprint_items_preserving_legal_anchor_source_channels_match_items" in rendered_checks
    assert "execution_phases_preserving_legal_anchor_source_channels_match_phases" in rendered_checks


def test_render_markdown_reports_failed_ids():
    doc = _sprint_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_curator_sprint(doc)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Curator Sprint Validation" in rendered
    assert "all_prompt_and_scoring_flags_blocked" in rendered
    assert "Phase-covered actions" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    sprint_path = tmp_path / "global_protections_curator_sprint.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    sprint_path.write_text(json.dumps(_sprint_doc()), encoding="utf-8")

    assert validator.main(["--sprint", str(sprint_path), "--validate"]) == 0
    assert validator.main([
        "--sprint",
        str(sprint_path),
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


def test_main_returns_nonzero_for_invalid_sprint(tmp_path):
    doc = _sprint_doc()
    doc["summary"]["regulatory_priority_queue_items"] = 0
    sprint_path = tmp_path / "global_protections_curator_sprint.json"
    out = tmp_path / "validation.json"
    sprint_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main(["--sprint", str(sprint_path), "--out", str(out)]) == 1
    assert out.exists()
