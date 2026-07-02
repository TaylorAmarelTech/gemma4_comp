"""Tests for source-research planning from domain grounding queues."""
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


bsrp = _load(
    "build_domain_source_research_plan",
    _ROOT / "scripts" / "build_domain_source_research_plan.py",
)


def test_worker_protection_source_research_plan_summarizes_all_blockers():
    doc = bsrp.build_source_research_plan("developing_country_worker_protections")
    summary = doc["summary"]

    assert doc["_meta"]["status"].startswith("source-research plan")
    assert summary["source_object_tasks"] == 15
    assert summary["scope_refinement_tasks"] == 8
    assert summary["blocked_prompt_count"] == 12
    assert summary["prompts_ready_for_comparable_run"] == 0
    assert "HK" in summary["missing_verified_local_jurisdictions"]
    assert "Gulf" in summary["unresolved_corridor_scopes"]


def test_source_research_task_uses_labels_queries_and_rejection_criteria():
    doc = bsrp.build_source_research_plan("developing_country_worker_protections")
    by_source = {
        task["source_id"]: task
        for task in doc["source_research_tasks"]
    }

    hk_task = by_source["LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"]
    assert hk_task["jurisdiction"] == "HK"
    assert hk_task["jurisdiction_label"] == "Hong Kong"
    assert hk_task["category_phrase"] == "fee label and wage recovery"
    assert "DCWP-SCHEME-0007" in hk_task["blocked_prompt_ids"]
    assert any("Hong Kong" in query for query in hk_task["search_queries"])
    assert any("site:gov.hk" in query for query in hk_task["search_queries"])
    assert any("social-media post" in rule for rule in hk_task["reject_if"])
    assert "verified_local_source_ids" not in hk_task


def test_scope_refinement_task_requires_concrete_jurisdictions():
    doc = bsrp.build_source_research_plan("developing_country_worker_protections")
    by_scope = {
        (task["scope"], task["category"]): task
        for task in doc["scope_refinement_tasks"]
    }

    gulf_task = by_scope[("Gulf", "fee_label_and_wage_recovery")]
    assert "DCWP-SCHEME-0007" in gulf_task["blocked_prompt_ids"]
    assert any("concrete destination" in q for q in gulf_task["research_questions"])
    assert any("Gulf states" in query for query in gulf_task["search_queries"])
    assert any("responsible jurisdiction" in rule for rule in gulf_task["reject_if"])


def test_source_research_plan_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "plan.json"
    md_out = tmp_path / "plan.md"

    assert bsrp.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source-object tasks" in printed
    assert "scope-refinement tasks" in printed
    assert "report" in printed

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_object_tasks"] == 15
    report = md_out.read_text(encoding="utf-8")
    assert "# Domain Source Research Plan" in report
    assert "not legal advice" in report
    assert "`RESEARCH-LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY`" in report
    assert "Synthetic composite:" not in report


def test_source_research_plan_cli_can_skip_markdown(tmp_path, capsys):
    out = tmp_path / "plan.json"

    assert bsrp.main([
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


def test_source_research_plan_can_build_from_precomputed_queue(tmp_path):
    queue = bsrp.build_grounding_queue("developing_country_worker_protections")
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    out = tmp_path / "plan.json"

    assert bsrp.main([
        "--domain",
        "developing_country_worker_protections",
        "--queue",
        str(queue_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["_meta"]["grounding_queue_inputs"]["grounding_manifest"].endswith("grounding_sources.json")
