"""Tests for the domain curation-bundle validator."""
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
    "build_domain_curation_bundle",
    _ROOT / "scripts" / "build_domain_curation_bundle.py",
)
validator = _load(
    "validate_domain_curation_bundle",
    _ROOT / "scripts" / "validate_domain_curation_bundle.py",
)


def _bundle_doc() -> dict:
    return builder.build_curation_bundle("developing_country_worker_protections")


def test_validator_accepts_current_domain_curation_bundle():
    report = validator.validate_domain_curation_bundle(_bundle_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["prompt_count"] == 12
    assert report["summary"]["prompts_blocked_for_comparable_run"] == 12
    assert report["summary"]["verified_local_law_rows"] == 0
    assert report["summary"]["source_object_tasks"] == 15
    assert report["summary"]["scope_refinement_tasks"] == 8
    assert report["summary"]["source_rows_ready_claimed"] == 0
    assert report["summary"]["ready_for_comparable_run"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_comparable_run_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_run"] = True
    doc["component_summaries"]["source_coverage_matrix"]["ready_for_comparable_run"] = True

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_source_and_scope_readiness_blocked" in report["summary"]["failed_check_ids"]
    assert "domain_curation_bundle_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_prompt_unblock_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["prompts_blocked_for_comparable_run"] = 11
    doc["component_summaries"]["grounding_queue"]["prompts_blocked_for_comparable_run"] = 11

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_source_and_scope_readiness_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_manifest_patch_readiness_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["manifest_operations_ready_for_manual_patch"] = 1
    doc["summary"]["ready_for_manual_manifest_patch"] = True
    doc["component_summaries"]["grounding_manifest_proposal"]["accepted_operations"] = 1
    doc["component_summaries"]["grounding_manifest_proposal"]["ready_for_manual_manifest_patch"] = True

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_source_and_scope_readiness_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_required_consistency_check_without_current_chain():
    doc = _bundle_doc()
    doc["consistency_checks"] = [
        check for check in doc["consistency_checks"] if check["id"] != "manifest_preview_valid"
    ]

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "consistency_checks_all_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_count_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["source_object_tasks"] = 99

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_component_summaries" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_payload_or_url_dump_without_current_chain():
    doc = _bundle_doc()
    doc["source_object_queue"] = [{
        "candidate_url": "https://example.invalid/private-case",
        "reviewer_notes": "synthetic worker@example.invalid contact must not be copied",
    }]

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "top_level_shape" in report["summary"]["failed_check_ids"]
    assert "raw_payload_sections_absent" in report["summary"]["failed_check_ids"]
    assert "domain_curation_bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unsafe_artifact_path_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["curation_bundle_json"] = "https://example.invalid/bundle.json"

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_safe" in report["summary"]["failed_check_ids"]
    assert "domain_curation_bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_validator_rejects_local_absolute_artifact_paths_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["grounding_queue_json"] = "C:/Users/example/reports/queue.json"
    doc["artifact_paths"]["source_review_packet_json"] = "/tmp/source_review_packet.json"
    doc["artifact_paths"]["grounding_manifest_proposal_json"] = "../reports/proposal.json"

    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_safe" in report["summary"]["failed_check_ids"]


def test_validator_rejects_artifact_path_drift_for_component_dir(tmp_path):
    doc = builder.build_curation_bundle(
        "developing_country_worker_protections",
        component_dir=tmp_path,
    )
    doc["artifact_paths"]["source_review_validation_json"] = (
        "external/stale_source_review_validation.json"
    )

    report = validator.validate_domain_curation_bundle(
        doc,
        component_dir=tmp_path,
        compare_current_chain=False,
    )

    assert report["summary"]["valid"] is False
    assert "artifact_paths_match_component_dir" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_run"] = True
    report = validator.validate_domain_curation_bundle(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Domain Curation Bundle Validation" in rendered
    assert "all_source_and_scope_readiness_blocked" in rendered
    assert "Ready for comparable run" in rendered


def test_render_markdown_reports_component_dir(tmp_path):
    doc = builder.build_curation_bundle(
        "developing_country_worker_protections",
        component_dir=tmp_path,
    )
    report = validator.validate_domain_curation_bundle(
        doc,
        component_dir=tmp_path,
        compare_current_chain=False,
    )

    rendered = validator.render_markdown(report)

    assert "Component dir" in rendered
    assert validator._display_path(tmp_path) in rendered


def test_main_validate_and_write(tmp_path, capsys):
    bundle_path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    bundle_path.write_text(json.dumps(_bundle_doc()), encoding="utf-8")

    assert validator.main(["--bundle", str(bundle_path), "--validate"]) == 0
    assert validator.main([
        "--bundle",
        str(bundle_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    assert out.exists()
    assert md.exists()


def test_main_accepts_component_dir_for_saved_custom_bundle(tmp_path):
    bundle_path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    doc = builder.build_curation_bundle(
        "developing_country_worker_protections",
        component_dir=tmp_path,
    )
    bundle_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--bundle",
        str(bundle_path),
        "--component-dir",
        str(tmp_path),
        "--validate",
        "--no-current-chain",
    ]) == 0


def test_main_returns_nonzero_for_invalid_bundle(tmp_path):
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_run"] = True
    bundle_path = tmp_path / "developing_country_worker_protections_curation_bundle.json"
    out = tmp_path / "validation.json"
    bundle_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main([
        "--bundle",
        str(bundle_path),
        "--out",
        str(out),
        "--no-current-chain",
    ]) == 1
    assert out.exists()
