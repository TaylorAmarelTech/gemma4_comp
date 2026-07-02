"""Tests for the global protections sister-project plan builder."""
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
    "build_global_protections_project_plan",
    _ROOT / "scripts" / "build_global_protections_project_plan.py",
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


def test_default_project_plan_links_existing_seed_and_regulatory_catalog():
    doc = builder.build_project_plan(_default_config())
    summary = doc["summary"]

    assert summary["safe_for_project_planning"] is True
    assert summary["primary_seed_domain_count"] == 1
    assert summary["registered_seed_domain_count"] == 1
    assert summary["candidate_pattern_count"] == 11
    assert summary["regulatory_candidates_found_count"] == 11
    assert summary["readiness_gate_count"] >= 5
    assert summary["ready_for_comparable_scoring"] is False
    assert doc["readiness"]["ready_for_prompt_generation"] is False
    assert doc["readiness"]["ready_for_training_use"] is False
    assert doc["readiness"]["ready_for_worker_facing_use"] is False
    assert all(
        phase["ready_for_training_use"] is False
        for phase in doc["readiness"]["first_build_phases"]
    )
    assert doc["existing_pipeline_links"]["registered_seed_domains"] == [
        "developing_country_worker_protections"
    ]
    assert not doc["existing_pipeline_links"]["missing_seed_domains"]
    assert not doc["existing_pipeline_links"]["missing_candidate_patterns"]
    assert all(check["ok"] for check in doc["checks"])


def test_project_plan_rejects_urls_and_sensitive_fields_without_copying_values():
    config = _default_config()
    config["source_url"] = "https://example.com/private-case"
    config["source_admission_rules"] = ["Use https://example.com/private-case as proof"]

    doc = builder.build_project_plan(config)
    rendered = json.dumps(doc, ensure_ascii=False)

    assert doc["summary"]["safe_for_project_planning"] is False
    assert doc["issues"]["unexpected_fields"] == 1
    assert doc["issues"]["sensitive_top_level_fields_present"] == 1
    assert doc["issues"]["source_admission_rules_contains_unsafe_text"] == 1
    assert doc["issues"]["privacy_scan_not_ok"] == 1
    assert "private-case" not in rendered


def test_project_plan_flags_missing_registry_and_catalog_links():
    config = _default_config()

    doc = builder.build_project_plan(
        config,
        registry={"domains": {}},
        regulatory_catalog={"patterns": []},
    )

    assert doc["summary"]["safe_for_project_planning"] is False
    assert doc["issues"]["primary_seed_domain_not_registered"] == 1
    assert doc["issues"]["candidate_pattern_missing_from_catalog"] == 11
    assert doc["existing_pipeline_links"]["registered_seed_domains"] == []
    assert doc["existing_pipeline_links"]["missing_seed_domains"] == [
        "developing_country_worker_protections"
    ]


def test_project_plan_markdown_lists_axes_gates_and_non_scoring_rule():
    doc = builder.build_project_plan(_default_config())
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Regulatory Benchmark" in rendered
    assert "## Benchmark Axes" in rendered
    assert "local law versus international anchor discipline" in rendered
    assert "## Readiness Gates" in rendered
    assert "source_object_coverage" in rendered
    assert "Prompt expansion, training use, public claims" in rendered


def test_project_plan_main_validate_and_write(tmp_path):
    config = tmp_path / "project.json"
    out = tmp_path / "plan.json"
    md = tmp_path / "plan.md"
    config.write_text(json.dumps(_default_config()), encoding="utf-8")

    assert builder.main(["--config", str(config), "--validate"]) == 0
    assert builder.main(["--config", str(config), "--out", str(out), "--markdown-out", str(md)]) == 0
    assert out.exists()
    assert md.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["safe_for_project_planning"] is True
    assert "# Global Protections Regulatory Benchmark" in md.read_text(encoding="utf-8")


def test_project_plan_main_refuses_to_write_unsafe_config(tmp_path):
    config = _default_config()
    config["candidate_pattern_ids"] = ["https://example.com/private-case"]
    config_path = tmp_path / "project.json"
    out = tmp_path / "plan.json"
    md = tmp_path / "plan.md"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    assert builder.main(["--config", str(config_path), "--out", str(out), "--markdown-out", str(md)]) == 1
    assert not out.exists()
    assert not md.exists()
