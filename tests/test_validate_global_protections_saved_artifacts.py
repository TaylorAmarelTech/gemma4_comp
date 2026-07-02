"""Tests for the global protections saved-artifact validation suite."""
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


curation_builder = _load(
    "build_global_protections_curation_bundle",
    _ROOT / "scripts" / "build_global_protections_curation_bundle.py",
)
suite = _load(
    "validate_global_protections_saved_artifacts",
    _ROOT / "scripts" / "validate_global_protections_saved_artifacts.py",
)


def _write_component_set(component_dir: Path, *, all_components: bool = False) -> None:
    out = component_dir / "global_protections_curation_bundle.json"
    md_out = component_dir / "global_protections_curation_bundle.md"
    args = [
        "--write-components",
        "--component-dir",
        str(component_dir),
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]
    if all_components:
        args.append("--write-all-components")
    assert curation_builder.main(args) == 0


def test_artifact_paths_externalize_hidden_workspace_segments():
    modules = [
        curation_builder,
        curation_builder.readiness_builder,
        curation_builder.next_actions_builder,
        curation_builder.curator_sprint_builder,
        curation_builder.readiness_builder.domain_bundle_builder,
        curation_builder.readiness_builder.regulatory_bundle_builder,
        suite,
    ]
    hidden_nested_path = _ROOT / "reports" / ".scratch" / "artifact.json"
    normal_report_path = _ROOT / "reports" / "benchmark" / "artifact.json"

    for module in modules:
        assert module._artifact_path(hidden_nested_path) == "external/artifact.json"
        assert module._artifact_path(normal_report_path) == "reports/benchmark/artifact.json"


def test_saved_artifacts_suite_accepts_written_component_set(tmp_path):
    _write_component_set(tmp_path)

    report = suite.validate_saved_artifacts(component_dir=tmp_path)

    assert report["summary"]["valid"] is True
    assert report["summary"]["artifact_count"] == 13
    assert report["summary"]["valid_artifact_count"] == 13
    assert report["summary"]["failed_artifact_count"] == 0
    assert report["summary"]["missing_or_unreadable_artifact_count"] == 0
    assert report["summary"]["missing_or_unreadable_markdown_count"] == 0
    assert report["summary"]["unsafe_markdown_count"] == 0
    assert report["summary"]["artifact_path_mismatch_count"] == 0
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert report["summary"]["curation_bundle_next_execution_phase_count"] == 5
    assert report["summary"]["curation_bundle_next_phase_covered_actions"] == 34
    assert report["summary"]["curation_bundle_curator_execution_phase_count"] == 5
    assert report["summary"]["curation_bundle_curator_phase_covered_actions"] == 34
    assert report["summary"]["curation_bundle_next_action_count"] == 34
    assert report["summary"]["curation_bundle_curator_phase_expected_actions"] == 34
    assert report["summary"]["next_actions_execution_phase_count"] == 5
    assert report["summary"]["next_actions_phase_covered_actions"] == 34
    assert report["summary"]["curator_sprint_execution_phase_count"] == 5
    assert report["summary"]["curator_sprint_phase_covered_actions"] == 34
    assert report["summary"]["phase_coverage_mismatch_count"] == 0
    assert report["summary"]["phase_coverage_mismatches"] == []
    assert report["summary"]["readiness_worker_prompt_count"] == 12
    assert report["summary"]["readiness_worker_prompts_blocked_for_comparable_run"] == 12
    assert report["summary"]["readiness_worker_verified_local_law_rows"] == 0
    assert report["summary"]["readiness_worker_source_object_tasks"] == 15
    assert report["summary"]["readiness_worker_scope_refinement_tasks"] == 8
    assert report["summary"]["readiness_regulatory_pattern_count"] == 11
    assert report["summary"]["readiness_regulatory_candidate_count"] == 10
    assert report["summary"]["readiness_regulatory_seed_scaffold_operations"] == 0
    assert report["summary"]["curation_worker_verified_local_law_rows"] == 0
    assert report["summary"]["curation_worker_source_object_tasks"] == 15
    assert report["summary"]["curation_worker_scope_refinement_tasks"] == 8
    assert report["summary"]["curation_regulatory_pattern_count"] == 11
    assert report["summary"]["curation_regulatory_candidate_count"] == 10
    assert report["summary"]["curation_regulatory_seed_scaffold_operations"] == 0
    assert report["summary"]["readiness_blocker_mismatch_count"] == 0
    assert report["summary"]["readiness_blocker_mismatches"] == []
    assert report["summary"]["jurisdiction_pack_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert report["summary"]["curation_jurisdiction_pack_scope_ids"] == [
        "bd_origin_state",
        "np_origin_state",
        "lk_origin_state",
        "ph_origin_state",
        "id_origin_destination",
        "ke_origin_destination",
        "gh_origin_destination",
        "qa_destination_forum",
    ]
    assert report["summary"]["jurisdiction_pack_domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert report["summary"]["curation_jurisdiction_pack_domain_lens_ids"] == [
        "cross_border_worker_protections",
        "digital_consumer_credit_worker_debt",
        "informal_housing_tenancy_eviction",
    ]
    assert report["summary"]["jurisdiction_pack_id_mismatch_count"] == 0
    assert report["summary"]["jurisdiction_pack_id_mismatches"] == []
    assert report["summary"]["benchmark_legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["benchmark_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["source_channel_matrix_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["source_channel_review_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["eval_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["diagnostic_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["judge_calibration_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["transition_gate_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["readiness_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["next_actions_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curator_sprint_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curation_judge_calibration_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"][
        "curation_source_channel_matrix_legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"][
        "curation_source_channel_review_legal_claim_anchor_source_channel_ids"
    ] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curation_transition_gate_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curation_readiness_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curation_next_actions_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["curation_curator_sprint_legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 0
    assert report["summary"]["legal_anchor_channel_mismatches"] == []
    assert all(row["valid"] for row in report["artifact_results"])
    assert all(row["markdown_safe"] for row in report["artifact_results"])
    assert all(check["ok"] for check in report["checks"])


def test_saved_artifacts_suite_derives_lower_level_inventory_from_builders(tmp_path):
    specs = suite._lower_level_artifact_specs(tmp_path, domain_id=suite.DEFAULT_DOMAIN)
    ids = [spec["artifact_id"] for spec in specs]
    stems = [spec["stem"] for spec in specs]

    assert len(specs) == 14
    assert ids == [
        "domain_grounding_queue",
        "domain_source_research_plan",
        "domain_source_coverage_matrix",
        "domain_source_review_packet",
        "domain_source_review_sprint",
        "domain_source_review_ledger",
        "domain_source_review_validation",
        "domain_grounding_manifest_proposal",
        "domain_curation_bundle",
        "regulatory_miss_pattern_plan",
        "regulatory_domain_intake_packet",
        "regulatory_domain_intake_validation",
        "regulatory_domain_seed_proposal",
        "regulatory_curation_bundle",
    ]
    assert "developing_country_worker_protections_source_review_packet" in stems
    assert "regulatory_domain_intake_packet" in stems
    assert all(Path(spec["json_path"]).parent == tmp_path for spec in specs)
    assert all(Path(spec["markdown_path"]).parent == tmp_path for spec in specs)


def test_saved_artifacts_suite_accepts_all_component_artifact_paths(tmp_path):
    _write_component_set(tmp_path, all_components=True)

    report = suite.validate_saved_artifacts(component_dir=tmp_path, validate_lower_components=True)

    assert report["summary"]["valid"] is True
    assert report["summary"]["artifact_count"] == 13
    assert report["summary"]["lower_level_expected_artifact_count"] == 14
    assert report["summary"]["lower_level_artifact_count"] == 14
    assert report["summary"]["lower_level_valid_artifact_count"] == 14
    assert report["summary"]["lower_level_failed_artifact_count"] == 0
    assert report["summary"]["lower_level_expected_artifact_ids"] == [
        row["artifact_id"] for row in report["lower_level_artifact_results"]
    ]
    assert report["summary"]["artifact_path_mismatch_count"] == 0
    lower_ids = {row["artifact_id"] for row in report["lower_level_artifact_results"]}
    assert "domain_curation_bundle" in lower_ids
    assert "domain_source_review_packet" in lower_ids
    assert "regulatory_domain_intake_packet" in lower_ids
    assert "regulatory_curation_bundle" in lower_ids
    assert report["summary"]["direct_domain_source_object_tasks"] == 15
    assert report["summary"]["direct_domain_scope_refinement_tasks"] == 8
    assert report["summary"]["direct_regulatory_pattern_count"] == 11
    assert report["summary"]["direct_regulatory_candidate_count"] == 10
    assert report["summary"]["direct_regulatory_seed_scaffold_operations"] == 0
    assert report["summary"]["readiness_blocker_mismatch_count"] == 0
    assert (tmp_path / "developing_country_worker_protections_source_review_validation.json").exists()
    assert (tmp_path / "regulatory_domain_seed_proposal.json").exists()


def test_saved_artifacts_suite_rejects_corrupted_lower_level_bundle(tmp_path):
    _write_component_set(tmp_path, all_components=True)
    path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["ready_for_comparable_run"] = True
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(
        component_dir=tmp_path,
        compare_current_chain=False,
        validate_lower_components=True,
    )

    assert report["summary"]["valid"] is False
    assert report["summary"]["lower_level_failed_artifact_ids"] == ["domain_curation_bundle"]
    assert report["summary"]["ready_for_comparable_scoring"] is True
    assert "all_lower_level_artifact_validations_pass" in report["summary"]["suite_failed_check_ids"]
    row = next(
        row for row in report["lower_level_artifact_results"] if row["artifact_id"] == "domain_curation_bundle"
    )
    assert "all_source_and_scope_readiness_blocked" in row["failed_check_ids"]


def test_saved_artifacts_suite_requires_lower_level_paths_when_validating_lower_components(tmp_path):
    _write_component_set(tmp_path, all_components=True)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["artifact_paths"].pop("source_review_validation_json")
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(
        component_dir=tmp_path,
        compare_current_chain=False,
        validate_lower_components=True,
    )

    assert report["summary"]["valid"] is False
    assert report["summary"]["artifact_path_mismatch_count"] == 1
    assert "curation_bundle_artifact_paths_match_files" in report["summary"]["suite_failed_check_ids"]
    mismatch = report["summary"]["artifact_path_mismatches"][0]
    assert mismatch["rule"] == "artifact_path_keys"
    assert mismatch["missing"] == ["source_review_validation_json"]
    assert (tmp_path / "developing_country_worker_protections_source_review_validation.json").exists()


def test_saved_artifacts_suite_rejects_lower_level_bundle_artifact_path_drift(tmp_path):
    _write_component_set(tmp_path, all_components=True)
    path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["artifact_paths"]["source_review_validation_json"] = (
        "external/stale_source_review_validation.json"
    )
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(
        component_dir=tmp_path,
        compare_current_chain=False,
        validate_lower_components=True,
    )

    assert report["summary"]["valid"] is False
    assert report["summary"]["lower_level_failed_artifact_ids"] == ["domain_curation_bundle"]
    row = next(
        row for row in report["lower_level_artifact_results"] if row["artifact_id"] == "domain_curation_bundle"
    )
    assert "lower_level_bundle_artifact_paths_match_files" in row["failed_check_ids"]


def test_saved_artifacts_suite_rejects_lower_level_domain_blocker_count_drift(tmp_path):
    _write_component_set(tmp_path, all_components=True)
    path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["source_object_tasks"] = 14
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(
        component_dir=tmp_path,
        compare_current_chain=False,
        validate_lower_components=True,
    )

    assert report["summary"]["valid"] is False
    assert report["summary"]["readiness_blocker_mismatch_count"] == 1
    assert report["summary"]["readiness_blocker_mismatches"] == [{
        "artifact_id": "lower_level.domain_curation_bundle",
        "rule": "readiness_blocker_counts_match",
        "expected": {
            "prompt_count": 12,
            "prompts_blocked_for_comparable_run": 12,
            "verified_local_law_rows": 0,
            "source_object_tasks": 15,
            "scope_refinement_tasks": 8,
            "ready_for_comparable_run": False,
        },
        "actual": {
            "prompt_count": 12,
            "prompts_blocked_for_comparable_run": 12,
            "verified_local_law_rows": 0,
            "source_object_tasks": 14,
            "scope_refinement_tasks": 8,
            "ready_for_comparable_run": False,
        },
    }]
    assert (
        "readiness_blocker_counts_match_across_artifacts"
        in report["summary"]["suite_failed_check_ids"]
    )
    rendered = suite.render_markdown(report)
    assert "Readiness Blocker Mismatches" in rendered
    assert "lower_level.domain_curation_bundle" in rendered


def test_saved_artifacts_suite_rejects_curation_readiness_blocker_count_drift(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["component_summaries"]["readiness_bundle"]["worker_verified_local_law_rows"] = 1
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["readiness_blocker_mismatch_count"] == 1
    assert report["summary"]["readiness_blocker_mismatches"] == [{
        "artifact_id": "curation_bundle.readiness_bundle",
        "rule": "readiness_blocker_counts_match",
        "expected": {
            "worker_prompt_count": 12,
            "worker_prompts_blocked_for_comparable_run": 12,
            "worker_verified_local_law_rows": 0,
            "ready_for_comparable_scoring": False,
        },
        "actual": {
            "worker_prompt_count": 12,
            "worker_prompts_blocked_for_comparable_run": 12,
            "worker_verified_local_law_rows": 1,
            "ready_for_comparable_scoring": False,
        },
    }]
    assert "curation_bundle" in report["summary"]["failed_artifact_ids"]
    assert (
        "readiness_blocker_counts_match_across_artifacts"
        in report["summary"]["suite_failed_check_ids"]
    )


def test_saved_artifacts_suite_rejects_curation_summary_blocker_count_drift(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["worker_source_object_tasks"] = 14
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["readiness_blocker_mismatch_count"] == 1
    assert report["summary"]["readiness_blocker_mismatches"] == [{
        "artifact_id": "curation_bundle.summary",
        "rule": "readiness_blocker_counts_match",
        "expected": {
            "worker_prompt_count": 12,
            "worker_prompts_blocked_for_comparable_run": 12,
            "worker_verified_local_law_rows": 0,
            "worker_source_object_tasks": 15,
            "worker_scope_refinement_tasks": 8,
                "regulatory_pattern_count": 11,
                "regulatory_candidate_count": 10,
            "regulatory_seed_scaffold_operations": 0,
        },
        "actual": {
            "worker_prompt_count": 12,
            "worker_prompts_blocked_for_comparable_run": 12,
            "worker_verified_local_law_rows": 0,
            "worker_source_object_tasks": 14,
            "worker_scope_refinement_tasks": 8,
                "regulatory_pattern_count": 11,
                "regulatory_candidate_count": 10,
            "regulatory_seed_scaffold_operations": 0,
        },
    }]
    assert "curation_bundle" in report["summary"]["failed_artifact_ids"]
    assert (
        "readiness_blocker_counts_match_across_artifacts"
        in report["summary"]["suite_failed_check_ids"]
    )


def test_saved_artifacts_suite_rejects_missing_artifact(tmp_path):
    _write_component_set(tmp_path)
    (tmp_path / "global_protections_project_plan.json").unlink()

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["missing_or_unreadable_artifact_count"] == 1
    assert report["summary"]["failed_artifact_ids"] == ["project_plan"]
    assert "all_artifacts_readable" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_missing_markdown(tmp_path):
    _write_component_set(tmp_path)
    (tmp_path / "global_protections_project_plan.md").unlink()

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["missing_or_unreadable_markdown_count"] == 1
    assert report["summary"]["missing_or_unreadable_markdown_ids"] == ["project_plan"]
    assert "all_markdown_reports_readable" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_markdown_leak(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_next_actions.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\nhttps://example.invalid/raw_text\n",
        encoding="utf-8",
    )

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["unsafe_markdown_ids"] == ["next_actions"]
    assert "all_markdown_reports_safe" in report["summary"]["suite_failed_check_ids"]
    next_row = next(row for row in report["artifact_results"] if row["artifact_id"] == "next_actions")
    assert "markdown_disallowed_text" in next_row["markdown_issue_ids"]


def test_saved_artifacts_suite_rejects_stale_bundle_artifact_path(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["artifact_paths"]["global_protections_project_plan_json"] = "external/stale_project_plan.json"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["artifact_path_mismatch_count"] == 1
    assert "curation_bundle_artifact_paths_match_files" in report["summary"]["suite_failed_check_ids"]
    mismatch = report["summary"]["artifact_path_mismatches"][0]
    assert mismatch["key"] == "global_protections_project_plan_json"


def test_saved_artifacts_suite_sanitizes_artifact_path_mismatch_details(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["artifact_paths"][
        "global_protections_project_plan_json"
    ] = "C:\\Users\\private\\worker-case-row.json"
    doc["artifact_paths"][
        "C:\\Users\\private\\raw-worker-case-key"
    ] = "C:\\Users\\private\\raw-worker-case-value.json"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)
    rendered_json = json.dumps(report, ensure_ascii=False)
    rendered_markdown = suite.render_markdown(report)

    assert report["summary"]["valid"] is False
    assert report["summary"]["artifact_path_mismatch_count"] == 2
    assert {
        finding["rule"] for finding in report["summary"]["artifact_path_mismatches"]
    } == {"artifact_path_keys", "artifact_path_value"}
    key_finding = next(
        finding
        for finding in report["summary"]["artifact_path_mismatches"]
        if finding["rule"] == "artifact_path_keys"
    )
    value_finding = next(
        finding
        for finding in report["summary"]["artifact_path_mismatches"]
        if finding["rule"] == "artifact_path_value"
    )
    assert key_finding["extra"] == ["custom_or_invalid"]
    assert value_finding["actual"] == "custom_or_invalid"
    assert "worker-case-row" not in rendered_json
    assert "raw-worker-case" not in rendered_json
    assert "C:\\Users\\private" not in rendered_json
    assert "worker-case-row" not in rendered_markdown
    assert "raw-worker-case" not in rendered_markdown
    assert "C:\\Users\\private" not in rendered_markdown


def test_saved_artifacts_suite_rejects_curation_phase_coverage_drift(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["curator_execution_phase_covered_actions"] = 29
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["curation_bundle_next_phase_covered_actions"] == 34
    assert report["summary"]["curation_bundle_curator_phase_covered_actions"] == 29
    assert "curation_bundle_phase_covered_action_counts_match" in report["summary"]["suite_failed_check_ids"]
    assert (
        "curation_bundle_curator_phase_coverage_matches_sprint_and_blocked"
        in report["summary"]["suite_failed_check_ids"]
    )


def test_saved_artifacts_suite_rejects_direct_phase_coverage_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_next_actions.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["execution_phases"][0]["action_ids"].pop()
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["next_actions_phase_covered_actions"] == 33
    assert report["summary"]["curation_bundle_next_phase_covered_actions"] == 34
    assert report["summary"]["phase_coverage_mismatch_count"] == 1
    assert report["summary"]["phase_coverage_mismatches"] == [{
        "artifact_id": "next_actions",
            "rule": "direct_phase_coverage_matches_curation_bundle",
            "expected": {
                "execution_phase_count": 5,
                "execution_phase_covered_action_count": 34,
            },
            "actual": {
                "execution_phase_count": 5,
                "execution_phase_covered_action_count": 33,
            },
        }]
    assert "direct_phase_coverage_matches_curation_bundle" in report["summary"]["suite_failed_check_ids"]
    rendered = suite.render_markdown(report)
    assert "Phase Coverage Mismatches" in rendered
    assert "direct_phase_coverage_matches_curation_bundle" in rendered


def test_saved_artifacts_suite_rejects_direct_jurisdiction_pack_id_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_jurisdiction_pack_matrix.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["jurisdiction_scope_ids"] = ["stale_scope"]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["jurisdiction_pack_id_mismatch_count"] == 1
    assert report["summary"]["jurisdiction_pack_id_mismatches"] == [{
        "artifact_id": "curation_bundle.jurisdiction_pack_matrix",
        "rule": "jurisdiction_pack_scope_ids_match_direct_matrix",
        "expected": {
            "jurisdiction_scope_count": 8,
            "jurisdiction_scope_ids": ["custom_or_invalid"],
        },
        "actual": {
            "jurisdiction_scope_count": 8,
            "jurisdiction_scope_ids": [
                "bd_origin_state",
                "np_origin_state",
                "lk_origin_state",
                "ph_origin_state",
                "id_origin_destination",
                "ke_origin_destination",
                "gh_origin_destination",
                "qa_destination_forum",
            ],
        },
    }]
    assert "jurisdiction_pack_matrix" in report["summary"]["failed_artifact_ids"]
    assert "jurisdiction_pack_ids_match_curation_bundle" in report["summary"]["suite_failed_check_ids"]
    rendered_json = json.dumps(report, ensure_ascii=False)
    rendered = suite.render_markdown(report)
    assert "stale_scope" not in rendered_json
    assert "stale_scope" not in rendered
    assert "custom_or_invalid" in rendered


def test_saved_artifacts_suite_rejects_curation_jurisdiction_pack_id_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["jurisdiction_pack_domain_lens_ids"] = ["stale_lens"]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["jurisdiction_pack_id_mismatch_count"] == 1
    assert report["summary"]["jurisdiction_pack_id_mismatches"] == [{
        "artifact_id": "curation_bundle.jurisdiction_pack_matrix",
        "rule": "jurisdiction_pack_domain_lens_ids_match_direct_matrix",
        "expected": {
            "domain_lens_count": 3,
            "domain_lens_ids": [
                "cross_border_worker_protections",
                "digital_consumer_credit_worker_debt",
                "informal_housing_tenancy_eviction",
            ],
        },
        "actual": {
            "domain_lens_count": 3,
            "domain_lens_ids": ["custom_or_invalid"],
        },
    }]
    assert "curation_bundle" in report["summary"]["failed_artifact_ids"]
    assert "jurisdiction_pack_ids_match_curation_bundle" in report["summary"]["suite_failed_check_ids"]
    rendered_json = json.dumps(report, ensure_ascii=False)
    rendered = suite.render_markdown(report)
    assert "Jurisdiction-Pack ID Mismatches" in rendered
    assert "stale_lens" not in rendered_json
    assert "stale_lens" not in rendered
    assert "custom_or_invalid" in rendered


def test_saved_artifacts_suite_rejects_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_eval_contract.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "eval_contract",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]
    rendered_json = json.dumps(report, ensure_ascii=False)
    rendered = suite.render_markdown(report)
    assert "Legal-Anchor Channel Mismatches" in rendered
    assert "social_channel_notice_or_scanned_circular" not in rendered_json
    assert "social_channel_notice_or_scanned_circular" not in rendered
    assert "custom_or_invalid" in rendered


def test_saved_artifacts_suite_rejects_source_matrix_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_source_channel_matrix.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "source_channel_matrix",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "source_channel_matrix" in report["summary"]["failed_artifact_ids"]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_source_review_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_source_channel_review_packet.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "source_channel_review_packet",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "source_channel_review_packet" in report["summary"]["failed_artifact_ids"]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_curation_source_layer_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["source_channel_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["source_channel_legal_claim_anchor_source_channel_ids"] = list(broadened)
    doc["summary"]["source_channel_review_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["source_channel_review_legal_claim_anchor_source_channel_ids"] = list(
        broadened
    )
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 2
    assert [item["artifact_id"] for item in report["summary"]["legal_anchor_channel_mismatches"]] == [
        "curation_bundle.source_channel_matrix",
        "curation_bundle.source_channel_review_packet",
    ]
    assert "curation_bundle" in report["summary"]["failed_artifact_ids"]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_judge_calibration_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_judge_calibration_plan.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "judge_calibration_plan",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_transition_gate_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_transition_gate.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "transition_gate",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_readiness_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_readiness_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "readiness_bundle",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_curation_readiness_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["readiness_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["readiness_legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "curation_bundle.readiness_bundle",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_next_actions_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_next_actions.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "next_actions",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_curation_next_actions_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["next_actions_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["next_actions_legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "curation_bundle.next_actions",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_curator_sprint_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curator_sprint.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "curator_sprint",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_curation_curator_sprint_legal_anchor_channel_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["curator_sprint_legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["curator_sprint_legal_claim_anchor_source_channel_ids"] = list(broadened)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert report["summary"]["legal_anchor_channel_mismatch_count"] == 1
    assert report["summary"]["legal_anchor_channel_mismatches"] == [{
        "artifact_id": "curation_bundle.curator_sprint",
        "rule": "legal_claim_anchor_source_channels_match_benchmark_blueprint",
        "expected": {
            "legal_claim_anchor_source_channel_count": 2,
            "legal_claim_anchor_source_channel_ids": [
                "official_gazette_or_law_portal",
                "labour_or_migration_ministry_notice",
            ],
        },
        "actual": {
            "legal_claim_anchor_source_channel_count": 3,
            "legal_claim_anchor_source_channel_ids": [*broadened[:2], "custom_or_invalid"],
        },
    }]
    assert "legal_anchor_source_channels_match_across_artifacts" in report["summary"]["suite_failed_check_ids"]


def test_saved_artifacts_suite_rejects_corrupted_component(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_next_actions.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["ready_for_comparable_scoring"] = True
    doc["actions"][0]["ready_for_comparable_scoring"] = True
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "next_actions" in report["summary"]["failed_artifact_ids"]
    assert report["summary"]["ready_for_comparable_scoring"] is True
    next_row = next(row for row in report["artifact_results"] if row["artifact_id"] == "next_actions")
    assert "all_readiness_flags_blocked" in next_row["failed_check_ids"]


def test_saved_artifacts_suite_markdown_lists_failed_artifacts(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_project_plan.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["summary"]["safe_for_project_planning"] = False
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)
    rendered = suite.render_markdown(report)

    assert "# Global Protections Saved Artifacts Validation" in rendered
    assert "project_plan" in rendered
    assert "Failed Artifacts" in rendered


def test_saved_artifacts_suite_markdown_lists_lower_level_check_coverage(tmp_path):
    _write_component_set(tmp_path, all_components=True)

    report = suite.validate_saved_artifacts(
        component_dir=tmp_path,
        compare_current_chain=False,
        validate_lower_components=True,
    )
    rendered = suite.render_markdown(report)

    assert "Lower-level component checks" in rendered
    assert (
        f"| Lower-level component checks | {report['summary']['lower_level_total_check_count']} |"
        in rendered
    )
    assert "| Failed lower-level component checks | 0 |" in rendered


def test_saved_artifacts_suite_markdown_lists_curation_phase_coverage(tmp_path):
    _write_component_set(tmp_path)

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)
    rendered = suite.render_markdown(report)

    assert "| Curation bundle next phases | 5 |" in rendered
    assert "| Curation bundle next phase-covered actions | 34 |" in rendered
    assert "| Curation bundle curator phases | 5 |" in rendered
    assert "| Curation bundle curator phase-covered actions | 34 |" in rendered
    assert "| Direct next-actions phases | 5 |" in rendered
    assert "| Direct next-actions phase-covered actions | 34 |" in rendered
    assert "| Direct jurisdiction-pack scopes | 8 |" in rendered
    assert "| Curation bundle jurisdiction-pack scopes | 8 |" in rendered
    assert "| Direct jurisdiction-pack domain lenses | 3 |" in rendered
    assert "| Curation bundle jurisdiction-pack domain lenses | 3 |" in rendered
    assert "| Jurisdiction-pack ID mismatches | 0 |" in rendered
    assert "| Readiness worker prompts | 12 |" in rendered
    assert "| Readiness worker prompts blocked | 12 |" in rendered
    assert "| Readiness verified local-law rows | 0 |" in rendered
    assert "| Readiness source-object tasks | 15 |" in rendered
    assert "| Readiness scope-refinement tasks | 8 |" in rendered
    assert "| Readiness regulatory patterns | 11 |" in rendered
    assert "| Readiness regulatory candidate domains | 10 |" in rendered
    assert "| Readiness regulatory seed scaffold operations | 0 |" in rendered
    assert "| Readiness blocker mismatches | 0 |" in rendered
    assert "| Direct source-channel matrix legal-anchor source channels | 2 |" in rendered
    assert "| Direct source-channel review legal-anchor source channels | 2 |" in rendered
    assert "| Curation bundle source-channel matrix legal-anchor source channels | 2 |" in rendered
    assert "| Curation bundle source-channel review legal-anchor source channels | 2 |" in rendered
    assert "| Direct readiness legal-anchor source channels | 2 |" in rendered
    assert "| Curation bundle readiness legal-anchor source channels | 2 |" in rendered
    assert "| Direct next-actions legal-anchor source channels | 2 |" in rendered
    assert "| Curation bundle next-actions legal-anchor source channels | 2 |" in rendered
    assert "| Direct curator-sprint legal-anchor source channels | 2 |" in rendered
    assert "| Curation bundle curator-sprint legal-anchor source channels | 2 |" in rendered
    assert "| Direct curator-sprint phases | 5 |" in rendered
    assert "| Direct curator-sprint phase-covered actions | 34 |" in rendered
    assert "| Phase coverage mismatches | 0 |" in rendered
    assert "| Legal-anchor source channels | 2 |" in rendered
    assert "| Legal-anchor channel mismatches | 0 |" in rendered


def test_saved_artifacts_suite_markdown_lists_unsafe_markdown(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_project_plan.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nC:/tmp/raw_text\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)
    rendered = suite.render_markdown(report)

    assert "Unsafe Markdown" in rendered
    assert "project_plan" in rendered
    assert "markdown_path_leak" in rendered


def test_saved_artifacts_suite_markdown_lists_artifact_path_mismatch(tmp_path):
    _write_component_set(tmp_path)
    path = tmp_path / "global_protections_curation_bundle.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["artifact_paths"]["global_protections_next_actions_markdown"] = "external/stale_next_actions.md"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    report = suite.validate_saved_artifacts(component_dir=tmp_path, compare_current_chain=False)
    rendered = suite.render_markdown(report)

    assert "Artifact Path Mismatches" in rendered
    assert "global_protections_next_actions_markdown" in rendered


def test_saved_artifacts_suite_cli_writes_json_and_markdown(tmp_path, capsys):
    _write_component_set(tmp_path)
    out = tmp_path / "suite_validation.json"
    md_out = tmp_path / "suite_validation.md"

    assert suite.main([
        "--component-dir",
        str(tmp_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert "phase_coverage=next:5/34,curator:5/34" in printed
    assert "phase_mismatches=0" in printed
    assert "readiness_blocker_mismatches=0" in printed
    assert "legal_anchor_mismatches=0" in printed
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["valid"] is True
    assert "# Global Protections Saved Artifacts Validation" in md_out.read_text(encoding="utf-8")


def test_saved_artifacts_suite_cli_json_prints_full_report_without_writes(tmp_path, capsys):
    _write_component_set(tmp_path)
    capsys.readouterr()
    out = tmp_path / "suite_validation.json"
    md_out = tmp_path / "suite_validation.md"

    assert suite.main([
        "--component-dir",
        str(tmp_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
        "--json",
    ]) == 0
    printed = capsys.readouterr().out
    report = json.loads(printed)

    assert report["summary"]["valid"] is True
    assert report["artifact_results"]
    assert report["checks"]
    assert report["_meta"]["refresh_components"] is False
    assert not out.exists()
    assert not md_out.exists()
    assert str(tmp_path) not in printed


def test_saved_artifacts_suite_cli_refreshes_components_before_validation(tmp_path, capsys):
    out = tmp_path / "suite_validation.json"
    md_out = tmp_path / "suite_validation.md"

    assert suite.main([
        "--component-dir",
        str(tmp_path),
        "--refresh-components",
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert (tmp_path / "global_protections_project_plan.json").exists()
    assert (tmp_path / "global_protections_project_plan.md").exists()
    assert (tmp_path / "global_protections_curation_bundle.json").exists()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["_meta"]["refresh_components"] is True
    assert report["summary"]["valid"] is True
    assert report["summary"]["artifact_path_mismatch_count"] == 0


def test_saved_artifacts_suite_cli_refreshes_all_components_before_validation(tmp_path, capsys):
    out = tmp_path / "suite_validation.json"
    md_out = tmp_path / "suite_validation.md"

    assert suite.main([
        "--component-dir",
        str(tmp_path),
        "--refresh-all-components",
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert "lower_level_artifacts=0/14" in printed
    assert "lower_level_checks=0/64" in printed
    assert "suite_checks=0/" in printed
    assert "phase_coverage=next:5/34,curator:5/34" in printed
    assert "phase_mismatches=0" in printed
    assert "readiness_blocker_mismatches=0" in printed
    assert "legal_anchor_mismatches=0" in printed
    assert (tmp_path / "global_protections_curation_bundle.json").exists()
    assert (tmp_path / "developing_country_worker_protections_source_review_validation.json").exists()
    assert (tmp_path / "regulatory_domain_seed_proposal.json").exists()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["_meta"]["refresh_components"] is True
    assert report["_meta"]["refresh_all_components"] is True
    assert report["_meta"]["validate_lower_components"] is True
    assert report["summary"]["valid"] is True
    assert report["summary"]["validate_lower_components"] is True
    assert report["summary"]["lower_level_expected_artifact_count"] == 14
    assert report["summary"]["lower_level_artifact_count"] == 14
    assert report["summary"]["lower_level_failed_artifact_count"] == 0
    assert report["summary"]["artifact_path_mismatch_count"] == 0


def test_saved_artifacts_suite_cli_nonzero_for_missing_artifact(tmp_path, capsys):
    _write_component_set(tmp_path)
    (tmp_path / "global_protections_transition_gate.json").unlink()

    assert suite.main(["--component-dir", str(tmp_path), "--validate", "--no-current-chain"]) == 1
    printed = capsys.readouterr().out
    assert '"valid": false' in printed
    assert '"transition_gate"' in printed
