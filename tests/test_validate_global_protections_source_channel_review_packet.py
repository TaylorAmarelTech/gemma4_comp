"""Tests for the global protections source-channel review-packet validator."""
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
    "build_global_protections_source_channel_review_packet",
    _ROOT / "scripts" / "build_global_protections_source_channel_review_packet.py",
)
validator = _load(
    "validate_global_protections_source_channel_review_packet",
    _ROOT / "scripts" / "validate_global_protections_source_channel_review_packet.py",
)


def _packet_doc() -> dict:
    return builder.build_source_channel_review_packet()


def test_validator_accepts_current_source_channel_review_packet():
    report = validator.validate_source_channel_review_packet(_packet_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["review_row_count"] == 70
    assert report["summary"]["informal_publication_rows"] == 7
    assert report["summary"]["legal_claim_anchor_rows"] == 14
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["rows_ready_for_manifest_promotion"] == 0
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_manifest_promotion_and_scoring_drift_without_current_chain():
    doc = _packet_doc()
    doc["review_rows"][0]["ready_for_manifest_promotion"] = True
    doc["review_rows"][0]["ready_for_comparable_scoring"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_source_channel_review_packet(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_rows" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_informal_publication_policy_drift_without_current_chain():
    doc = _packet_doc()
    social = next(
        row for row in doc["review_rows"]
        if row["source_channel_id"] == "social_channel_notice_or_scanned_circular"
    )
    social["claim_use"] = "may_support_legal_claim_after_source_path_privacy_and_expert_review"
    social["public_interest_review_status"] = "not_required"

    report = validator.validate_source_channel_review_packet(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "informal_publications_stay_lead_only" in report["summary"]["failed_check_ids"]
    assert "legal_claim_anchors_are_official_only" in report["summary"]["failed_check_ids"]


def test_validator_rejects_non_official_legal_claim_anchor_without_current_chain():
    doc = _packet_doc()
    ngo = next(
        row for row in doc["review_rows"]
        if row["source_channel_id"] == "ngo_ilo_iom_un_public_interest_report"
    )
    ngo["claim_use"] = "may_support_legal_claim_after_source_path_privacy_and_expert_review"

    report = validator.validate_source_channel_review_packet(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "legal_claim_anchors_are_official_only" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_summary_drift_without_current_chain():
    doc = _packet_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)

    report = validator.validate_source_channel_review_packet(
        doc,
        compare_current_chain=False,
    )

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_rows" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_locator_and_bad_date_without_current_chain():
    doc = _packet_doc()
    row = doc["review_rows"][0]
    row["candidate_source_title"] = "Official notice at https://example.invalid/source"
    row["publication_or_access_date"] = "06/29/2026"

    report = validator.validate_source_channel_review_packet(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "packet_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]
    assert "publication_or_access_dates_are_iso_when_present" in report["summary"]["failed_check_ids"]


def test_validator_rejects_status_count_drift_without_current_chain():
    doc = _packet_doc()
    doc["counts_by_status"]["not_started"] = 1

    report = validator.validate_source_channel_review_packet(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "counts_by_status_match_rows" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _packet_doc()
    doc["review_rows"][0]["ready_for_prompt_generation"] = True
    report = validator.validate_source_channel_review_packet(doc)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Source-Channel Review Packet Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channel IDs" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    packet_path = tmp_path / "global_protections_source_channel_review_packet.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    packet_path.write_text(json.dumps(_packet_doc()), encoding="utf-8")

    assert validator.main(["--packet", str(packet_path), "--validate"]) == 0
    assert validator.main([
        "--packet",
        str(packet_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_packet(tmp_path):
    doc = _packet_doc()
    doc["review_rows"][0]["ready_for_comparable_scoring"] = True
    packet_path = tmp_path / "global_protections_source_channel_review_packet.json"
    out = tmp_path / "validation.json"
    packet_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main(["--packet", str(packet_path), "--out", str(out)]) == 1
    assert out.exists()
