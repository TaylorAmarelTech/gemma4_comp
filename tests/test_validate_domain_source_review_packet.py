"""Tests for filled source-review packet validation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


builder = _load(
    "build_domain_source_review_packet_for_validation_tests",
    _ROOT / "scripts" / "build_domain_source_review_packet.py",
)
validator = _load(
    "validate_domain_source_review_packet",
    _ROOT / "scripts" / "validate_domain_source_review_packet.py",
)
grounding = _load(
    "domain_grounding_for_review_validation_tests",
    _ROOT / "scripts" / "domain_grounding.py",
)


def _packet():
    return builder.build_source_review_packet("developing_country_worker_protections")


def _fill_valid_source_row(row):
    row.update({
        "candidate_title": "Hong Kong wage recovery official guidance",
        "candidate_authority": "Official Labour Department",
        "candidate_url": "https://www.example.gov.hk/labour/wage-recovery",
        "candidate_archive_url": "https://archive.example.org/hk-wage-recovery",
        "candidate_source_type": "official_regulator_guidance",
        "candidate_publication_date": "2026-06-01",
        "candidate_accessed_date": "2026-06-29",
        "candidate_language": "en",
        "official_or_public_interest": "official",
        "legal_scope_note": "Synthetic review fixture for Hong Kong wage recovery scope.",
        "privacy_notes": "No worker or complainant data in this synthetic fixture.",
        "pii_risk": "none_detected",
        "license_or_terms_note": "Public official web page fixture.",
        "reviewer_notes": "Reviewed by synthetic domain reviewer.",
        "proposed_manifest_verification_status": "verified_local_law",
        "ready_for_manifest_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })


def test_blank_review_packet_validates_with_no_promotion_candidates():
    report = validator.validate_source_review_packet(_packet(), domain_id="developing_country_worker_protections")
    summary = report["summary"]

    assert summary["ok"] is True
    assert summary["source_rows"] == 15
    assert summary["scope_rows"] == 8
    assert summary["source_rows_ready_claimed"] == 0
    assert summary["source_rows_accepted_for_manifest_proposal"] == 0
    assert report["candidate_manifest_rows"] == []
    assert report["scope_update_candidates"] == []


def test_valid_ready_source_row_produces_manifest_shaped_candidate():
    packet = _packet()
    hk = next(
        row for row in packet["source_candidate_intake_rows"]
        if row["source_id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    )
    _fill_valid_source_row(hk)

    report = validator.validate_source_review_packet(packet, domain_id="developing_country_worker_protections")

    assert report["summary"]["ok"] is True
    assert report["summary"]["source_rows_ready_claimed"] == 1
    assert report["summary"]["source_rows_accepted_for_manifest_proposal"] == 1
    candidate = report["candidate_manifest_rows"][0]
    assert candidate["id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    assert candidate["jurisdiction"] == "HK"
    assert candidate["verification_status"] == "verified_local_law"
    assert candidate["verified_date"] == "2026-06-29"
    assert candidate["coverage_tags"] == ["fee_label_and_wage_recovery"]

    grounding.validate_grounding_manifest({
        "_meta": {
            "domain": "fixture",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [candidate],
    })


def test_ready_source_row_with_missing_fields_is_blocked():
    packet = _packet()
    row = packet["source_candidate_intake_rows"][0]
    row["proposed_manifest_verification_status"] = "verified_local_law"
    row["ready_for_manifest_promotion"] = True

    report = validator.validate_source_review_packet(packet, domain_id="developing_country_worker_protections")
    result = next(r for r in report["source_row_results"] if r["task_id"] == row["task_id"])

    assert report["summary"]["ok"] is False
    assert result["ready_claimed"] is True
    assert result["accepted_for_manifest_proposal"] is False
    assert "candidate_title_required_for_promotion" in result["issues"]
    assert "privacy_review_required_must_be_false_after_review" in result["issues"]


def test_ready_source_row_with_private_contact_text_is_blocked():
    packet = _packet()
    row = packet["source_candidate_intake_rows"][0]
    _fill_valid_source_row(row)
    row["reviewer_notes"] = "Call +1 555 555 5555 before publishing."

    report = validator.validate_source_review_packet(packet, domain_id="developing_country_worker_protections")
    result = next(r for r in report["source_row_results"] if r["task_id"] == row["task_id"])

    assert report["summary"]["ok"] is False
    assert any("phone_like_text" in issue for issue in result["issues"])
    assert report["candidate_manifest_rows"] == []


def test_valid_scope_resolution_row_is_reported_as_queue_update_candidate():
    packet = _packet()
    scope = next(
        row for row in packet["scope_resolution_intake_rows"]
        if row["scope"] == "Gulf" and row["category"] == "fee_label_and_wage_recovery"
    )
    scope.update({
        "resolved_jurisdictions": ["QA", "SA"],
        "resolved_forums_or_regulators": ["labour ministry", "recruitment regulator"],
        "source_ids_to_create": ["LOCAL-QA-FEE-LABEL-AND-WAGE-RECOVERY"],
        "resolution_note": "Synthetic fixture resolving Gulf to concrete destination forums.",
        "ready_for_source_queue_update": True,
        "expert_review_required": False,
    })

    report = validator.validate_source_review_packet(packet, domain_id="developing_country_worker_protections")

    assert report["summary"]["ok"] is True
    assert report["summary"]["scope_rows_ready_claimed"] == 1
    assert report["summary"]["scope_rows_accepted_for_queue_update"] == 1
    candidate = report["scope_update_candidates"][0]
    assert candidate["resolved_jurisdictions"] == ["QA", "SA"]
    assert candidate["source_ids_to_create"] == ["LOCAL-QA-FEE-LABEL-AND-WAGE-RECOVERY"]


def test_validation_cli_writes_report_for_blank_packet(tmp_path, capsys):
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "validation.json"
    md_out = tmp_path / "validation.md"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")

    assert validator.main([
        "--domain",
        "developing_country_worker_protections",
        "--packet",
        str(packet_path),
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source proposals" in printed
    assert "ok=true" in printed
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["ok"] is True
    md = md_out.read_text(encoding="utf-8")
    assert "# Domain Source Review Validation" in md
    assert "never mutates the grounding manifest" in md


def test_validation_cli_returns_nonzero_for_blocked_ready_claim(tmp_path, capsys):
    packet = _packet()
    packet["source_candidate_intake_rows"][0]["ready_for_manifest_promotion"] = True
    packet["source_candidate_intake_rows"][0]["proposed_manifest_verification_status"] = "verified_local_law"
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "validation.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert validator.main([
        "--domain",
        "developing_country_worker_protections",
        "--packet",
        str(packet_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 1
    printed = capsys.readouterr().out
    assert "ok=false" in printed
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["source_rows_blocked_after_ready_claim"] == 1
