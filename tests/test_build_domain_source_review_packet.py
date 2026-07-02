"""Tests for blank source-review intake packets."""
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


bsrpkt = _load(
    "build_domain_source_review_packet",
    _ROOT / "scripts" / "build_domain_source_review_packet.py",
)


def test_worker_protection_review_packet_starts_all_rows_in_review():
    doc = bsrpkt.build_source_review_packet("developing_country_worker_protections")
    summary = doc["summary"]

    assert doc["_meta"]["status"].startswith("blank source-review intake packet")
    assert summary["source_candidate_rows"] == 15
    assert summary["scope_resolution_rows"] == 8
    assert summary["default_ready_for_manifest_promotion"] == 0
    assert summary["default_ready_for_source_queue_update"] == 0
    assert doc["safety_audit"]["ok"] is True
    assert doc["safety_audit"]["issues"] == []

    assert all(
        row["proposed_manifest_verification_status"] == "needs_review"
        for row in doc["source_candidate_intake_rows"]
    )
    assert all(
        row["ready_for_manifest_promotion"] is False
        for row in doc["source_candidate_intake_rows"]
    )
    assert all(
        row["ready_for_source_queue_update"] is False
        for row in doc["scope_resolution_intake_rows"]
    )


def test_source_candidate_row_preserves_task_context_but_leaves_candidate_fields_blank():
    doc = bsrpkt.build_source_review_packet("developing_country_worker_protections")
    by_source = {
        row["source_id"]: row
        for row in doc["source_candidate_intake_rows"]
    }

    hk = by_source["LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"]
    assert hk["jurisdiction"] == "HK"
    assert hk["jurisdiction_label"] == "Hong Kong"
    assert hk["candidate_title"] == ""
    assert hk["candidate_authority"] == ""
    assert hk["candidate_url"] == ""
    assert hk["candidate_accessed_date"] == ""
    assert hk["pii_risk"] == "unknown"
    assert "DCWP-SCHEME-0007" in hk["blocked_prompt_ids"]
    assert any("site:gov.hk" in query for query in hk["search_queries"])
    assert any("private case file" in rule for rule in hk["reject_if"])
    assert "verification_status" in hk["manifest_fields_to_fill"]


def test_scope_resolution_rows_require_concrete_jurisdictions_before_queue_update():
    doc = bsrpkt.build_source_review_packet("developing_country_worker_protections")
    by_scope = {
        (row["scope"], row["category"]): row
        for row in doc["scope_resolution_intake_rows"]
    }

    gulf = by_scope[("Gulf", "fee_label_and_wage_recovery")]
    assert gulf["resolved_jurisdictions"] == []
    assert gulf["resolved_forums_or_regulators"] == []
    assert gulf["ready_for_source_queue_update"] is False
    assert any("concrete jurisdiction" in check for check in gulf["acceptance_checks"])
    assert any("Gulf states" in query for query in gulf["search_queries"])


def test_review_packet_validator_flags_accidental_promotion():
    doc = bsrpkt.build_source_review_packet("developing_country_worker_protections")
    doc["source_candidate_intake_rows"][0]["proposed_manifest_verification_status"] = "verified_local_law"
    doc["source_candidate_intake_rows"][0]["ready_for_manifest_promotion"] = True
    doc["source_candidate_intake_rows"][0]["candidate_url"] = "https://example.test/source"

    audit = bsrpkt.validate_review_packet(doc)

    assert audit["ok"] is False
    assert any("must start as needs_review" in issue for issue in audit["issues"])
    assert any("cannot start ready for promotion" in issue for issue in audit["issues"])
    assert any("candidate_url must start blank" in issue for issue in audit["issues"])


def test_review_packet_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "review_packet.json"
    md_out = tmp_path / "review_packet.md"

    assert bsrpkt.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source candidate rows" in printed
    assert "scope resolution rows" in printed
    assert "report" in printed

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_candidate_rows"] == 15
    report = md_out.read_text(encoding="utf-8")
    assert "# Domain Source Review Packet" in report
    assert "not legal advice" in report
    assert "`RESEARCH-LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY`" in report
    assert "Synthetic composite:" not in report


def test_review_packet_cli_can_skip_markdown(tmp_path, capsys):
    out = tmp_path / "review_packet.json"

    assert bsrpkt.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    printed = capsys.readouterr().out
    assert "report" not in printed
    assert out.exists()
    assert not out.with_suffix(".md").exists()


def test_review_packet_can_build_from_precomputed_source_plan(tmp_path):
    plan = bsrpkt.build_source_research_plan("developing_country_worker_protections")
    plan_path = tmp_path / "source_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    out = tmp_path / "review_packet.json"

    assert bsrpkt.main([
        "--domain",
        "developing_country_worker_protections",
        "--source-plan",
        str(plan_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["_meta"]["source_plan_status"].startswith("source-research plan")
