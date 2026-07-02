"""Tests for the global protections source-channel matrix validator."""
from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
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
    "build_global_protections_source_channel_matrix",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)
validator = _load(
    "validate_global_protections_source_channel_matrix",
    _ROOT / "scripts" / "validate_global_protections_source_channel_matrix.py",
)


def _matrix_doc():
    return builder.build_source_channel_matrix()


def test_validator_accepts_current_source_channel_matrix():
    report = validator.validate_source_channel_matrix(_matrix_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["matrix_row_count"] == 70
    assert report["summary"]["informal_publication_rows"] == 7
    assert report["summary"]["legal_claim_anchor_rows"] == 14
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_ready_flag_drift():
    doc = deepcopy(_matrix_doc())
    doc["summary"]["ready_for_comparable_scoring"] = True
    doc["matrix_rows"][0]["ready_for_comparable_scoring"] = True

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "matrix_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_matrix_row_and_count_drift():
    doc = deepcopy(_matrix_doc())
    removed = doc["matrix_rows"].pop()
    doc["counts_by_source_channel"][removed["source_channel_id"]] -= 1

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_matrix" in report["summary"]["failed_check_ids"]
    assert "each_family_has_each_source_channel" in report["summary"]["failed_check_ids"]


def test_validator_rejects_counts_by_source_channel_drift():
    doc = deepcopy(_matrix_doc())
    doc["counts_by_source_channel"]["official_gazette_or_law_portal"] += 1

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "counts_by_source_channel_match_rows" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_required_embedded_check():
    doc = deepcopy(_matrix_doc())
    doc["checks"] = [
        check
        for check in doc["checks"]
        if check["id"] != "informal_publications_require_authenticity_volatility_and_official_followup"
    ]

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "embedded_checks_all_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_informal_publication_promoted_to_legal_claim():
    doc = deepcopy(_matrix_doc())
    social = next(
        row
        for row in doc["matrix_rows"]
        if row["source_channel_id"] == "social_channel_notice_or_scanned_circular"
    )
    social["claim_use"] = "may_support_legal_claim_after_source_path_privacy_and_expert_review"
    social["evidence_status"] = "candidate_until_dated_archived_and_reviewed"

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "source_channel_policy_boundaries_intact" in report["summary"]["failed_check_ids"]
    assert "legal_claim_anchors_are_official_only" in report["summary"]["failed_check_ids"]


def test_validator_rejects_non_official_legal_claim_anchor():
    doc = deepcopy(_matrix_doc())
    context = next(
        row
        for row in doc["matrix_rows"]
        if row["source_channel_id"] == "ngo_ilo_iom_un_public_interest_report"
    )
    context["claim_use"] = "may_support_legal_claim_after_source_path_privacy_and_expert_review"

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "legal_claim_anchors_are_official_only" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_summary_drift():
    doc = deepcopy(_matrix_doc())
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_matrix" in report["summary"]["failed_check_ids"]
    assert "matrix_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_url_raw_text_and_privacy_leak():
    doc = deepcopy(_matrix_doc())
    doc["matrix_rows"][0]["next_step"] = (
        "Review https://example.invalid/source raw_text and email reviewer@example.invalid"
    )

    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]
    assert "matrix_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_validator_render_markdown_reports_failed_ids():
    doc = deepcopy(_matrix_doc())
    doc["summary"]["ready_for_prompt_generation"] = True
    report = validator.validate_source_channel_matrix(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Source-Channel Matrix Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channel IDs" in rendered
    assert "Failed Check IDs" in rendered


def test_validator_cli_writes_json_and_markdown(tmp_path, capsys):
    matrix_path = tmp_path / "global_protections_source_channel_matrix.json"
    out = tmp_path / "validation.json"
    md_out = tmp_path / "validation.md"
    matrix_path.write_text(json.dumps(_matrix_doc(), indent=2) + "\n", encoding="utf-8")

    assert validator.main([
        "--matrix",
        str(matrix_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["valid"] is True
    assert "# Global Protections Source-Channel Matrix Validation" in md_out.read_text(encoding="utf-8")


def test_validator_cli_nonzero_for_invalid_matrix(tmp_path, capsys):
    matrix_path = tmp_path / "global_protections_source_channel_matrix.json"
    doc = deepcopy(_matrix_doc())
    doc["summary"]["ready_for_comparable_scoring"] = True
    matrix_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    assert validator.main(["--matrix", str(matrix_path), "--validate", "--no-current-chain"]) == 1
    printed = capsys.readouterr().out
    assert '"valid": false' in printed
