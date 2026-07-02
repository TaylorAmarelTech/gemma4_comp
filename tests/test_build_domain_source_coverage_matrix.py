"""Tests for the source-coverage matrix builder."""
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


matrix = _load(
    "build_domain_source_coverage_matrix",
    _ROOT / "scripts" / "build_domain_source_coverage_matrix.py",
)


def test_source_coverage_matrix_summarizes_research_plan_cells():
    doc = matrix.build_source_coverage_matrix("developing_country_worker_protections")
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["coverage_cells"] == 15
    assert summary["jurisdiction_count"] == 15
    assert summary["category_count"] == 12
    assert summary["blocked_prompt_count"] == 12
    assert summary["pending_manifest_rows_to_promote"] == 12
    assert summary["missing_manifest_rows_to_add"] == 3
    assert summary["scope_refinement_tasks"] == 8
    assert summary["scope_blocked_cells"] > 0
    assert summary["prompts_ready_for_comparable_run"] == 0
    assert summary["prompts_blocked_for_comparable_run"] == 12
    assert summary["ready_for_comparable_run"] is False
    assert all(check["ok"] for check in doc["consistency_checks"])


def test_source_coverage_matrix_prioritizes_scope_and_pending_rows():
    doc = matrix.build_source_coverage_matrix("developing_country_worker_protections")
    rows = {row["cell_id"]: row for row in doc["matrix_rows"]}

    bd_recruitment = rows["BD:cross_border_recruitment_law"]
    assert bd_recruitment["coverage_status"] == "pending_manifest_row"
    assert bd_recruitment["priority_band"] == "1_scope_refinement_first"
    assert bd_recruitment["scope_blocked"] is True
    assert "Gulf" in bd_recruitment["related_unresolved_scopes"]

    gh_training = rows["GH:education_training_fee_fraud"]
    assert gh_training["coverage_status"] == "pending_manifest_row"
    assert gh_training["priority_band"] == "2_promote_existing_pending_row"
    assert gh_training["scope_blocked"] is False
    assert "existing pending manifest row" in gh_training["next_step"]

    hk_fee = rows["HK:fee_label_and_wage_recovery"]
    assert hk_fee["coverage_status"] == "missing_manifest_row"
    assert hk_fee["priority_band"] == "1_scope_refinement_first"
    assert hk_fee["scope_blocked"] is True
    assert "Gulf" in hk_fee["related_unresolved_scopes"]
    assert "DCWP-SCHEME-0007" in hk_fee["blocked_prompt_ids"]


def test_source_coverage_matrix_keeps_payload_compact():
    doc = matrix.build_source_coverage_matrix("developing_country_worker_protections")
    rendered = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in rendered
    assert "official labour law" not in rendered
    assert "search_queries" not in rendered
    assert "matrix_rows" in doc
    assert "source_research_tasks" not in doc


def test_source_coverage_matrix_markdown_lists_priority_and_checks():
    doc = matrix.build_source_coverage_matrix("developing_country_worker_protections")
    report = matrix.build_markdown_report(doc)

    assert "# Domain Source Coverage Matrix" in report
    assert "Priority Bands" in report
    assert "HK:fee_label_and_wage_recovery" in report
    assert "source_task_count_matches_matrix" in report
    assert "not comparable benchmark evidence" in report


def test_source_coverage_matrix_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "matrix.json"
    md_out = tmp_path / "matrix.md"

    assert matrix.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "coverage cells" in printed
    assert "ready_for_comparable_run=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["coverage_cells"] == 15
    assert md_out.exists()
    assert "# Domain Source Coverage Matrix" in md_out.read_text(encoding="utf-8")


def test_source_coverage_matrix_can_build_from_prebuilt_plan(tmp_path):
    plan = matrix.build_source_research_plan("developing_country_worker_protections")
    plan_path = tmp_path / "plan.json"
    out = tmp_path / "matrix.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    assert matrix.main([
        "--domain",
        "developing_country_worker_protections",
        "--plan",
        str(plan_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["pending_manifest_rows_to_promote"] == 12
    assert not out.with_suffix(".md").exists()
