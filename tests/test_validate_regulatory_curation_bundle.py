"""Tests for the regulatory curation-bundle validator."""
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
    "build_regulatory_curation_bundle",
    _ROOT / "scripts" / "build_regulatory_curation_bundle.py",
)
validator = _load(
    "validate_regulatory_curation_bundle",
    _ROOT / "scripts" / "validate_regulatory_curation_bundle.py",
)


def _bundle_doc() -> dict:
    return builder.build_regulatory_curation_bundle()


def test_validator_accepts_current_regulatory_curation_bundle():
    report = validator.validate_regulatory_curation_bundle(_bundle_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["candidate_queue_count"] == 10
    assert report["summary"]["top_candidate_id"]
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_prompt_generation_and_scoring_drift():
    doc = _bundle_doc()
    doc["summary"]["ready_for_prompt_generation"] = True
    doc["summary"]["ready_for_comparable_scoring"] = True

    report = validator.validate_regulatory_curation_bundle(doc)

    assert report["summary"]["valid"] is False
    assert "all_prompt_and_scoring_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" in report["summary"]["failed_check_ids"]


def test_validator_rejects_candidate_queue_count_drift_without_current_chain():
    doc = _bundle_doc()
    doc["summary"]["candidate_queue_count"] = 0
    doc["component_summaries"]["miss_pattern_plan"]["candidate_queue_count"] = 0
    doc["component_summaries"]["domain_intake_packet"]["candidate_queue_count"] = 0

    report = validator.validate_regulatory_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "candidate_queue_invariants_hold" in report["summary"]["failed_check_ids"]
    assert "summary_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_raw_payload_or_url_dump_without_current_chain():
    doc = _bundle_doc()
    doc["patterns"] = [{"source_url": "https://example.invalid/private-case"}]

    report = validator.validate_regulatory_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "top_level_shape" in report["summary"]["failed_check_ids"]
    assert "raw_payload_sections_absent" in report["summary"]["failed_check_ids"]
    assert "bundle_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_required_consistency_check_without_current_chain():
    doc = _bundle_doc()
    doc["consistency_checks"] = [
        check
        for check in doc["consistency_checks"]
        if check["id"] != "candidate_queue_keeps_scoring_blocked"
    ]

    report = validator.validate_regulatory_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "consistency_checks_all_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unsafe_artifact_path_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["regulatory_curation_bundle_json"] = "https://example.invalid/bundle.json"

    report = validator.validate_regulatory_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_safe" in report["summary"]["failed_check_ids"]


def test_validator_rejects_local_absolute_artifact_paths_without_current_chain():
    doc = _bundle_doc()
    doc["artifact_paths"]["miss_pattern_plan_json"] = "C:/Users/example/reports/plan.json"
    doc["artifact_paths"]["domain_intake_packet_json"] = "/tmp/intake.json"
    doc["artifact_paths"]["domain_seed_proposal_json"] = "../reports/proposal.json"

    report = validator.validate_regulatory_curation_bundle(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "artifact_paths_safe" in report["summary"]["failed_check_ids"]


def test_validator_rejects_artifact_path_drift_for_component_dir(tmp_path):
    doc = builder.build_regulatory_curation_bundle(component_dir=tmp_path)
    doc["artifact_paths"]["domain_seed_proposal_json"] = "external/stale_seed_proposal.json"

    report = validator.validate_regulatory_curation_bundle(
        doc,
        component_dir=tmp_path,
        compare_current_chain=False,
    )

    assert report["summary"]["valid"] is False
    assert "artifact_paths_match_component_dir" in report["summary"]["failed_check_ids"]


def test_render_markdown_reports_failed_ids():
    doc = _bundle_doc()
    doc["summary"]["ready_for_comparable_scoring"] = True
    report = validator.validate_regulatory_curation_bundle(doc)

    rendered = validator.render_markdown(report)

    assert "# Regulatory Curation Bundle Validation" in rendered
    assert "all_prompt_and_scoring_flags_blocked" in rendered
    assert "Ready for comparable scoring" in rendered


def test_render_markdown_reports_component_dir(tmp_path):
    doc = builder.build_regulatory_curation_bundle(component_dir=tmp_path)
    report = validator.validate_regulatory_curation_bundle(
        doc,
        component_dir=tmp_path,
        compare_current_chain=False,
    )

    rendered = validator.render_markdown(report)

    assert "Component dir" in rendered
    assert validator._display_path(tmp_path) in rendered


def test_main_validate_and_write(tmp_path, capsys):
    bundle_path = tmp_path / "regulatory_curation_bundle.json"
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
    bundle_path = tmp_path / "regulatory_curation_bundle.json"
    doc = builder.build_regulatory_curation_bundle(component_dir=tmp_path)
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
    doc["summary"]["candidate_queue_count"] = 999
    bundle_path = tmp_path / "regulatory_curation_bundle.json"
    out = tmp_path / "validation.json"
    bundle_path.write_text(json.dumps(doc), encoding="utf-8")

    assert validator.main(["--bundle", str(bundle_path), "--out", str(out)]) == 1
    assert out.exists()
