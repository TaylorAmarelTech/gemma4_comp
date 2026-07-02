"""Tests for the end-to-end domain curation bundle."""
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


bundle = _load(
    "build_domain_curation_bundle",
    _ROOT / "scripts" / "build_domain_curation_bundle.py",
)


def test_curation_bundle_summarizes_source_gating_chain():
    doc = bundle.build_curation_bundle("developing_country_worker_protections")
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["prompt_count"] == 12
    assert summary["prompts_ready_for_comparable_run"] == 0
    assert summary["prompts_blocked_for_comparable_run"] == 12
    assert summary["verified_local_law_rows"] == 0
    assert summary["source_object_tasks"] == 15
    assert summary["scope_refinement_tasks"] == 8
    assert summary["source_coverage_cells"] == 15
    assert summary["source_coverage_scope_blocked_cells"] > 0
    assert summary["source_coverage_pending_manifest_rows_to_promote"] == 12
    assert summary["source_coverage_missing_manifest_rows_to_add"] == 3
    assert summary["source_review_sprint_rows"] == 6
    assert summary["scope_resolution_sprint_rows"] == 8
    assert summary["source_review_sprint_deferred_scope_blocked_rows"] == 9
    assert summary["source_review_ledger_source_rows_not_started"] == 15
    assert summary["source_review_ledger_scope_rows_not_started"] == 8
    assert summary["source_review_ledger_source_rows_in_progress_not_ready"] == 0
    assert summary["source_review_ledger_scope_rows_in_progress_not_ready"] == 0
    assert summary["source_review_validation_ok"] is True
    assert summary["source_rows_ready_claimed"] == 0
    assert summary["source_rows_accepted_for_manifest_proposal"] == 0
    assert summary["manifest_proposal_ok"] is True
    assert summary["manifest_operations_ready_for_manual_patch"] == 0
    assert summary["ready_for_manual_manifest_patch"] is False
    assert summary["ready_for_comparable_run"] is False
    assert all(check["ok"] for check in doc["consistency_checks"])


def test_curation_bundle_keeps_component_summaries_without_prompt_text():
    doc = bundle.build_curation_bundle("developing_country_worker_protections")
    rendered = json.dumps(doc, ensure_ascii=False)

    assert "component_summaries" in doc
    assert doc["component_summaries"]["grounding_queue"]["prompt_count"] == 12
    assert doc["component_summaries"]["source_research_plan"]["source_object_tasks"] == 15
    assert doc["component_summaries"]["source_coverage_matrix"]["coverage_cells"] == 15
    assert doc["component_summaries"]["source_review_sprint"]["source_review_sprint_rows"] == 6
    assert doc["component_summaries"]["source_review_ledger"]["source_rows_not_started"] == 15
    assert "Synthetic composite:" not in rendered
    assert "candidate_manifest_rows" not in doc


def test_curation_bundle_artifact_paths_are_handoff_safe():
    doc = bundle.build_curation_bundle("developing_country_worker_protections")

    assert doc["artifact_paths"]["grounding_queue_json"] == (
        "reports/benchmark/developing_country_worker_protections_grounding_queue.json"
    )
    for value in doc["artifact_paths"].values():
        assert not value.startswith("/")
        assert not value.startswith("C:/")
        assert "\\" not in value
        assert ".." not in value.split("/")


def test_curation_bundle_artifact_paths_can_target_component_dir(tmp_path):
    doc = bundle.build_curation_bundle(
        "developing_country_worker_protections",
        component_dir=tmp_path,
    )

    assert doc["artifact_paths"]["grounding_queue_json"] == (
        "external/developing_country_worker_protections_grounding_queue.json"
    )
    assert doc["artifact_paths"]["source_review_validation_json"] == (
        "external/developing_country_worker_protections_source_review_validation.json"
    )
    assert doc["artifact_paths"]["curation_bundle_json"] == (
        "external/developing_country_worker_protections_curation_bundle.json"
    )


def test_curation_bundle_markdown_lists_checks_and_paths():
    doc = bundle.build_curation_bundle("developing_country_worker_protections")
    report = bundle.build_markdown_report(doc)

    assert "# Domain Curation Bundle" in report
    assert "Consistency OK" in report
    assert "Source-coverage cells" in report
    assert "Source-review sprint rows" in report
    assert "Source-review ledger source rows not started" in report
    assert "source_object_counts_match" in report
    assert "developing_country_worker_protections_curation_bundle.json" in report
    assert "not comparable benchmark evidence" in report


def test_curation_bundle_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    md_out = tmp_path / "bundle.md"

    assert bundle.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "ready_for_comparable_run=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["source_object_tasks"] == 15
    assert doc["artifact_paths"]["curation_bundle_json"] == "external/bundle.json"
    assert doc["artifact_paths"]["curation_bundle_markdown"] == "external/bundle.md"
    assert md_out.exists()
    assert "# Domain Curation Bundle" in md_out.read_text(encoding="utf-8")


def test_curation_bundle_can_write_component_artifacts(tmp_path):
    chain = bundle.build_curation_chain("developing_country_worker_protections")
    paths = bundle.write_component_artifacts(
        "developing_country_worker_protections",
        chain,
        output_dir=tmp_path,
    )

    expected_keys = {
        "grounding_queue_json",
        "source_research_plan_json",
        "source_coverage_matrix_json",
        "source_review_packet_json",
        "source_review_sprint_json",
        "source_review_ledger_json",
        "source_review_validation_json",
        "grounding_manifest_proposal_json",
    }
    assert expected_keys.issubset(paths)
    for key in expected_keys:
        assert paths[key].startswith("external/")
    assert (tmp_path / "developing_country_worker_protections_grounding_queue.md").exists()
    assert (tmp_path / "developing_country_worker_protections_source_review_validation.json").exists()


def test_curation_bundle_cli_can_write_components_to_custom_dir(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    component_dir = tmp_path / "components"

    assert bundle.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--no-md",
        "--write-components",
        "--component-dir",
        str(component_dir),
    ]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["grounding_queue_json"] == (
        "external/developing_country_worker_protections_grounding_queue.json"
    )
    assert doc["artifact_paths"]["source_coverage_matrix_json"] == (
        "external/developing_country_worker_protections_source_coverage_matrix.json"
    )
    assert doc["artifact_paths"]["source_review_sprint_json"] == (
        "external/developing_country_worker_protections_source_review_sprint.json"
    )
    assert doc["artifact_paths"]["source_review_ledger_json"] == (
        "external/developing_country_worker_protections_source_review_ledger.json"
    )
    assert doc["artifact_paths"]["curation_bundle_json"] == "external/bundle.json"
    assert (component_dir / "developing_country_worker_protections_source_review_validation.json").exists()
