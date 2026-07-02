"""Tests for the global protections project-plan validator."""
from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
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
    "build_global_protections_project_plan",
    _ROOT / "scripts" / "build_global_protections_project_plan.py",
)
validator = _load(
    "validate_global_protections_project_plan",
    _ROOT / "scripts" / "validate_global_protections_project_plan.py",
)


def _default_config() -> dict:
    return json.loads(
        (
            _ROOT
            / "configs"
            / "duecare"
            / "benchmarks"
            / "sister_projects"
            / "global_protections_regulatory_benchmark.json"
        ).read_text(encoding="utf-8")
    )


def _plan_doc() -> dict:
    return builder.build_project_plan(_default_config())


def test_validator_accepts_current_project_plan():
    report = validator.validate_project_plan(_plan_doc())

    assert report["summary"]["valid"] is True
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["project_id"] == "global_protections_regulatory_benchmark"
    assert report["summary"]["safe_for_project_planning"] is True
    assert report["summary"]["registered_seed_domain_count"] == 1
    assert report["summary"]["regulatory_candidates_found_count"] == 11
    assert report["summary"]["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in report["checks"])


def test_validator_rejects_readiness_drift():
    doc = deepcopy(_plan_doc())
    doc["summary"]["ready_for_comparable_scoring"] = True
    doc["readiness"]["ready_for_comparable_scoring"] = True
    doc["readiness"]["first_build_phases"][0]["ready_for_public_scoring"] = True
    doc["readiness"]["first_build_phases"][0]["ready_for_training_use"] = True

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "all_downstream_readiness_flags_blocked" in report["summary"]["failed_check_ids"]
    assert "first_build_phase_shape" in report["summary"]["failed_check_ids"]
    assert "plan_matches_current_chain" not in report["summary"]["failed_check_ids"]


def test_validator_rejects_first_build_phase_training_use():
    doc = deepcopy(_plan_doc())
    doc["readiness"]["first_build_phases"][0]["ready_for_training_use"] = True

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "first_build_phase_shape" in report["summary"]["failed_check_ids"]
    assert "all_downstream_readiness_flags_blocked" in report["summary"]["failed_check_ids"]


def test_validator_rejects_summary_count_drift():
    doc = deepcopy(_plan_doc())
    doc["scope"]["benchmark_axes"].pop()

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "summary_counts_match_sections" in report["summary"]["failed_check_ids"]


def test_validator_rejects_seed_and_candidate_link_drift():
    doc = deepcopy(_plan_doc())
    doc["existing_pipeline_links"]["registered_seed_domains"] = []
    doc["existing_pipeline_links"]["missing_seed_domains"] = [
        "developing_country_worker_protections"
    ]
    doc["existing_pipeline_links"]["regulatory_candidates_found"].pop()

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "seed_and_candidate_links_complete" in report["summary"]["failed_check_ids"]
    assert "summary_counts_match_sections" in report["summary"]["failed_check_ids"]


def test_validator_rejects_missing_required_embedded_check():
    doc = deepcopy(_plan_doc())
    doc["checks"] = [
        check
        for check in doc["checks"]
        if check["id"] != "primary_seed_domain_registered"
    ]

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "embedded_checks_all_ok" in report["summary"]["failed_check_ids"]


def test_validator_rejects_unsafe_phase_output_path():
    doc = deepcopy(_plan_doc())
    doc["readiness"]["first_build_phases"][0]["output"] = "C:/tmp/project_plan.json"

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "phase_output_paths_are_repo_relative" in report["summary"]["failed_check_ids"]


def test_validator_rejects_privacy_and_raw_text_leak():
    doc = deepcopy(_plan_doc())
    doc["project"]["research_question"] = (
        "Use https://example.invalid/raw_text and contact reviewer@example.invalid"
    )

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "privacy_scan_ok" in report["summary"]["failed_check_ids"]
    assert "plan_contains_no_disallowed_text" in report["summary"]["failed_check_ids"]


def test_validator_rejects_nonempty_issues_map():
    doc = deepcopy(_plan_doc())
    doc["issues"]["privacy_scan_not_ok"] = 1

    report = validator.validate_project_plan(doc, compare_current_chain=False)

    assert report["summary"]["valid"] is False
    assert "issues_empty" in report["summary"]["failed_check_ids"]


def test_validator_render_markdown_reports_failed_ids():
    doc = deepcopy(_plan_doc())
    doc["summary"]["safe_for_project_planning"] = False
    report = validator.validate_project_plan(doc, compare_current_chain=False)

    rendered = validator.render_markdown(report)

    assert "# Global Protections Project Plan Validation" in rendered
    assert "all_downstream_readiness_flags_blocked" in rendered
    assert "Failed Check IDs" in rendered


def test_validator_cli_writes_json_and_markdown(tmp_path, capsys):
    plan_path = tmp_path / "global_protections_project_plan.json"
    out = tmp_path / "validation.json"
    md_out = tmp_path / "validation.md"
    plan_path.write_text(json.dumps(_plan_doc(), indent=2) + "\n", encoding="utf-8")

    assert validator.main([
        "--plan",
        str(plan_path),
        "--out",
        str(out),
        "--markdown-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "valid=true" in printed
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["valid"] is True
    assert "# Global Protections Project Plan Validation" in md_out.read_text(encoding="utf-8")


def test_validator_cli_nonzero_for_invalid_plan(tmp_path, capsys):
    plan_path = tmp_path / "global_protections_project_plan.json"
    doc = deepcopy(_plan_doc())
    doc["readiness"]["ready_for_prompt_generation"] = True
    plan_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    assert validator.main(["--plan", str(plan_path), "--validate", "--no-current-chain"]) == 1
    printed = capsys.readouterr().out
    assert '"valid": false' in printed
