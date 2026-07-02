"""Tests for the global protections readiness-bundle validator."""
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
    "build_global_protections_readiness_bundle",
    _ROOT / "scripts" / "build_global_protections_readiness_bundle.py",
)
validator = _load(
    "validate_global_protections_readiness_bundle",
    _ROOT / "scripts" / "validate_global_protections_readiness_bundle.py",
)


def _bundle_doc() -> dict:
    return builder.build_readiness_bundle()


def test_validator_accepts_current_readiness_bundle():
    report = validator.validate_readiness_bundle(_bundle_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["safe_for_project_planning"] is True
    assert report["summary"]["worker_prompt_count"] == 12
    assert report["summary"]["worker_prompts_blocked_for_comparable_run"] == 12
    assert report["summary"]["worker_verified_local_law_rows"] == 0
    assert report["summary"]["regulatory_pattern_count"] == 11
    assert report["summary"]["regulatory_candidate_count"] == 10
    assert report["summary"]["legal_claim_anchor_source_channel_count"] == 2
    assert report["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert report["summary"]["ready_for_prompt_generation"] is False
    assert report["summary"]["ready_for_worker_facing_use"] is False
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_prompt_and_scoring_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["ready_for_prompt_generation"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True
    doc["component_summaries"]["regulatory_curation_bundle"]["ready_for_prompt_generation"] = True

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_components" in report["summary"]["failed_check_ids"]
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "readiness_bundle_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_worker_prompt_unblock_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["worker_prompts_blocked_for_comparable_run"] = 11
    doc["component_summaries"]["domain_curation_bundle"]["prompts_blocked_for_comparable_run"] = 11

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_local_law_row_promotion_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["worker_verified_local_law_rows"] = 1
    doc["component_summaries"]["domain_curation_bundle"]["verified_local_law_rows"] = 1

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_readiness_flags_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_legal_anchor_source_channel_drift_without_current_chain():
    doc = _bundle_doc()
    broadened = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
        "social_channel_notice_or_scanned_circular",
    ]
    doc["summary"]["legal_claim_anchor_source_channel_count"] = 3
    doc["summary"]["legal_claim_anchor_source_channel_ids"] = list(broadened)

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_components" in report["summary"]["failed_check_ids"]
    assert (
        "legal_claim_anchor_source_channels_match_source_matrix"
        in report["summary"]["failed_check_ids"]
    )


def test_validator_rejects_raw_payload_section_without_current_chain():
    doc = _bundle_doc()
    doc["_domain_chain"] = {"source_object_queue": []}

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "top_level_shape" in report["summary"]["failed_check_ids"]
    assert "raw_payload_sections_absent" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_component_key_without_current_chain():
    doc = _bundle_doc()
    doc["component_summaries"]["domain_curation_bundle"].pop("verified_local_law_rows")

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "component_summary_shape" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_components" in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_source_or_prompt_dump_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["policy"] += " Never copy prompt_text or source_url from https://example.invalid/source."

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "readiness_bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unsafe_artifact_path_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["project_plan_json"] = "https://example.invalid/project.json"

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_are_handoff_safe" in report["summary"]["failed_check_ids"]
    assert "readiness_bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_validator_rejects_local_absolute_artifact_paths_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["project_plan_json"] = "C:/Users/example/reports/benchmark/project.json"
    doc["artifact_paths"]["domain_curation_bundle_json"] = "/tmp/project.json"
    doc["artifact_paths"]["regulatory_curation_bundle_json"] = "../reports/project.json"

    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_are_handoff_safe" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_readiness_bundle(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Readiness Bundle Validation" in rendered
    assert "all_readiness_flags_blocked" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Ready for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path, capsys):
    bundle_path = tmp_path / "global_protections_readiness_bundle.json"
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


def test_main_returns_nonzero_for_invalid_bundle(tmp_path):
    doc = _bundle_doc()
    doc["summary"]["ready_for_worker_facing_use"] = True
    bundle_path = tmp_path / "global_protections_readiness_bundle.json"
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
