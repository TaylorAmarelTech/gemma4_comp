"""Tests for source-review sprint packet generation."""
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


sprint = _load(
    "build_domain_source_review_sprint",
    _ROOT / "scripts" / "build_domain_source_review_sprint.py",
)


def test_source_review_sprint_splits_scope_source_and_deferred_rows():
    doc = sprint.build_source_review_sprint("developing_country_worker_protections")
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["source_review_sprint_rows"] == 6
    assert summary["scope_resolution_sprint_rows"] == 8
    assert summary["deferred_scope_blocked_source_rows"] == 9
    assert summary["selected_source_rows_by_priority"] == {
        "2_promote_existing_pending_row": 4,
        "3_add_missing_source_row": 2,
    }
    assert summary["all_source_rows_ready_for_manifest_promotion"] is False
    assert summary["all_scope_rows_ready_for_source_queue_update"] is False
    assert summary["ready_for_comparable_run"] is False
    assert all(check["ok"] for check in doc["consistency_checks"])


def test_source_review_sprint_selects_only_non_scope_blocked_source_rows():
    doc = sprint.build_source_review_sprint("developing_country_worker_protections")
    source_ids = {row["source_id"]: row for row in doc["source_review_sprint_rows"]}
    deferred_ids = {row["source_id"] for row in doc["deferred_scope_blocked_source_rows"]}

    assert "LOCAL-GH-TRAINING-FEES" in source_ids
    assert "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY" not in source_ids
    assert "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY" in deferred_ids
    gh = source_ids["LOCAL-GH-TRAINING-FEES"]
    assert gh["review_packet_defaults"]["proposed_manifest_verification_status"] == "needs_review"
    assert gh["review_packet_defaults"]["ready_for_manifest_promotion"] is False
    assert "candidate_url" in gh["fields_to_complete"]


def test_source_review_sprint_scope_rows_keep_blank_resolution_defaults():
    doc = sprint.build_source_review_sprint("developing_country_worker_protections")
    by_task = {
        row["scope_task_id"]: row
        for row in doc["scope_resolution_sprint_rows"]
    }

    gulf_fee = by_task["REFINE-SCOPE-GULF-FEE-LABEL-AND-WAGE-RECOVERY"]
    assert "HK:fee_label_and_wage_recovery" in gulf_fee["related_coverage_cell_ids"]
    assert "PH:fee_label_and_wage_recovery" in gulf_fee["related_coverage_cell_ids"]
    assert gulf_fee["review_packet_defaults"]["resolved_jurisdictions"] == []
    assert gulf_fee["review_packet_defaults"]["ready_for_source_queue_update"] is False
    assert "resolved_jurisdictions" in gulf_fee["fields_to_complete"]


def test_source_review_sprint_keeps_payload_compact():
    doc = sprint.build_source_review_sprint("developing_country_worker_protections")
    rendered = json.dumps(doc, ensure_ascii=False)

    assert "search_queries" not in rendered
    assert "official labour law" not in rendered
    assert "Synthetic composite:" not in rendered
    assert "source_review_sprint_rows" in doc
    assert "source_candidate_intake_rows" not in doc


def test_source_review_sprint_markdown_lists_rows_and_gates():
    doc = sprint.build_source_review_sprint("developing_country_worker_protections")
    report = sprint.build_markdown_report(doc)

    assert "# Domain Source Review Sprint" in report
    assert "Scope Resolution Sprint" in report
    assert "Source Review Sprint" in report
    assert "LOCAL-GH-TRAINING-FEES" in report
    assert "not comparable benchmark evidence" in report


def test_source_review_sprint_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "sprint.json"
    md_out = tmp_path / "sprint.md"

    assert sprint.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source-review rows" in printed
    assert "ready_for_comparable_run=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_review_sprint_rows"] == 6
    assert md_out.exists()
    assert "# Domain Source Review Sprint" in md_out.read_text(encoding="utf-8")


def test_source_review_sprint_can_use_prebuilt_inputs_and_limit_rows(tmp_path):
    matrix_doc = sprint.build_source_coverage_matrix("developing_country_worker_protections")
    packet_doc = sprint.build_source_review_packet("developing_country_worker_protections")
    matrix_path = tmp_path / "matrix.json"
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "sprint.json"
    matrix_path.write_text(json.dumps(matrix_doc), encoding="utf-8")
    packet_path.write_text(json.dumps(packet_doc), encoding="utf-8")

    assert sprint.main([
        "--domain",
        "developing_country_worker_protections",
        "--matrix",
        str(matrix_path),
        "--review-packet",
        str(packet_path),
        "--max-source-rows",
        "2",
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_review_sprint_rows"] == 2
    assert doc["summary"]["scope_resolution_sprint_rows"] == 8
    assert not out.with_suffix(".md").exists()
