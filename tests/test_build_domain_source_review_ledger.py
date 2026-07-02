"""Tests for source-review progress ledger generation."""
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


ledger = _load(
    "build_domain_source_review_ledger",
    _ROOT / "scripts" / "build_domain_source_review_ledger.py",
)


def test_source_review_ledger_summarizes_blank_packet_state():
    doc = ledger.build_source_review_ledger("developing_country_worker_protections")
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["source_rows"] == 15
    assert summary["source_rows_not_started"] == 15
    assert summary["source_rows_in_progress_not_ready"] == 0
    assert summary["source_rows_ready_claimed"] == 0
    assert summary["source_rows_accepted_for_manifest_proposal"] == 0
    assert summary["scope_rows"] == 8
    assert summary["scope_rows_not_started"] == 8
    assert summary["scope_rows_in_progress_not_ready"] == 0
    assert summary["scope_rows_ready_claimed"] == 0
    assert summary["scope_rows_accepted_for_source_queue_update"] == 0
    assert summary["validation_ok"] is True
    assert summary["ready_for_comparable_run"] is False
    assert all(check["ok"] for check in doc["consistency_checks"])


def test_source_review_ledger_reports_required_field_completion():
    doc = ledger.build_source_review_ledger("developing_country_worker_protections")
    source_by_id = {
        row["source_id"]: row
        for row in doc["source_review_ledger_rows"]
    }
    scope_by_task = {
        row["task_id"]: row
        for row in doc["scope_review_ledger_rows"]
    }

    gh = source_by_id["LOCAL-GH-TRAINING-FEES"]
    assert gh["status"] == "not_started"
    assert gh["filled_review_field_count"] == 0
    assert gh["missing_promotion_field_count"] == 12
    assert gh["privacy_review_required"] is True
    assert gh["expert_review_required"] is True

    gulf = scope_by_task["REFINE-SCOPE-GULF-FEE-LABEL-AND-WAGE-RECOVERY"]
    assert gulf["status"] == "not_started"
    assert gulf["filled_review_field_count"] == 0
    assert gulf["missing_required_field_count"] == 4
    assert gulf["expert_review_required"] is True


def test_source_review_ledger_detects_in_progress_rows_without_ready_claims():
    packet = ledger.build_source_review_packet("developing_country_worker_protections")
    source = next(
        row for row in packet["source_candidate_intake_rows"]
        if row["source_id"] == "LOCAL-GH-TRAINING-FEES"
    )
    source["candidate_title"] = "Ghana training fee official source candidate"
    source["candidate_authority"] = "Public authority candidate"
    scope = next(
        row for row in packet["scope_resolution_intake_rows"]
        if row["scope"] == "Gulf" and row["category"] == "fee_label_and_wage_recovery"
    )
    scope["resolved_jurisdictions"] = ["QA"]

    doc = ledger.build_source_review_ledger(
        "developing_country_worker_protections",
        review_packet_doc=packet,
    )
    summary = doc["summary"]

    assert summary["source_rows_not_started"] == 14
    assert summary["source_rows_in_progress_not_ready"] == 1
    assert summary["source_rows_ready_claimed"] == 0
    assert summary["scope_rows_not_started"] == 7
    assert summary["scope_rows_in_progress_not_ready"] == 1
    assert summary["scope_rows_ready_claimed"] == 0


def test_source_review_ledger_reports_blocked_ready_claims():
    packet = ledger.build_source_review_packet("developing_country_worker_protections")
    row = packet["source_candidate_intake_rows"][0]
    row["ready_for_manifest_promotion"] = True
    row["proposed_manifest_verification_status"] = "verified_local_law"

    doc = ledger.build_source_review_ledger(
        "developing_country_worker_protections",
        review_packet_doc=packet,
    )
    summary = doc["summary"]

    assert summary["validation_ok"] is False
    assert summary["source_rows_ready_claimed"] == 1
    assert summary["source_rows_blocked_by_validation"] == 1
    blocked = next(row for row in doc["source_review_ledger_rows"] if row["ready_claimed"])
    assert blocked["status"] == "ready_claim_blocked_by_validation"
    assert blocked["validation_issue_count"] > 0


def test_source_review_ledger_keeps_payload_compact():
    doc = ledger.build_source_review_ledger("developing_country_worker_protections")
    rendered = json.dumps(doc, ensure_ascii=False)

    assert "search_queries" not in rendered
    assert "official labour law" not in rendered
    assert "Synthetic composite:" not in rendered
    assert "source_review_ledger_rows" in doc
    assert "source_candidate_intake_rows" not in doc


def test_source_review_ledger_markdown_lists_status_and_checks():
    doc = ledger.build_source_review_ledger("developing_country_worker_protections")
    report = ledger.build_markdown_report(doc)

    assert "# Domain Source Review Ledger" in report
    assert "Source rows not started" in report
    assert "LOCAL-GH-TRAINING-FEES" in report
    assert "validation_source_count_matches_packet" in report
    assert "not comparable benchmark evidence" in report


def test_source_review_ledger_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "ledger.json"
    md_out = tmp_path / "ledger.md"

    assert ledger.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source rows not started" in printed
    assert "ready_for_comparable_run=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_rows"] == 15
    assert md_out.exists()
    assert "# Domain Source Review Ledger" in md_out.read_text(encoding="utf-8")


def test_source_review_ledger_can_use_prebuilt_packet(tmp_path):
    packet = ledger.build_source_review_packet("developing_country_worker_protections")
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "ledger.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert ledger.main([
        "--domain",
        "developing_country_worker_protections",
        "--review-packet",
        str(packet_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["scope_rows_not_started"] == 8
    assert not out.with_suffix(".md").exists()
