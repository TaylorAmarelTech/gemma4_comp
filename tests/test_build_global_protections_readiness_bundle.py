"""Tests for the global protections composed readiness bundle."""
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


bundle = _load(
    "build_global_protections_readiness_bundle",
    _ROOT / "scripts" / "build_global_protections_readiness_bundle.py",
)


def test_readiness_bundle_summarizes_project_domain_and_regulatory_chains():
    doc = bundle.build_readiness_bundle()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["safe_for_project_planning"] is True
    assert summary["registered_seed_domain_count"] == 1
    assert summary["regulatory_pattern_count"] == 11
    assert summary["regulatory_candidate_count"] == 10
    assert summary["worker_prompt_count"] == 12
    assert summary["worker_prompts_blocked_for_comparable_run"] == 12
    assert summary["worker_verified_local_law_rows"] == 0
    assert summary["worker_source_object_tasks"] == 15
    assert summary["worker_scope_refinement_tasks"] == 8
    assert summary["regulatory_seed_scaffold_operations"] == 0
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_readiness_bundle_keeps_component_summaries_compact():
    doc = bundle.build_readiness_bundle()
    rendered = json.dumps(doc, ensure_ascii=False)

    assert doc["component_summaries"]["project_plan"]["registered_seed_domain_count"] == 1
    assert doc["component_summaries"]["domain_curation_bundle"]["prompt_count"] == 12
    assert doc["component_summaries"]["regulatory_curation_bundle"]["pattern_count"] == 11
    assert "Synthetic composite:" not in rendered
    assert "source_object_queue" not in doc
    assert "_domain_chain" not in doc


def test_readiness_bundle_artifact_paths_are_handoff_safe():
    doc = bundle.build_readiness_bundle()

    assert doc["artifact_paths"]["project_plan_json"] == (
        "reports/benchmark/global_protections_project_plan.json"
    )
    for value in doc["artifact_paths"].values():
        assert not value.startswith("/")
        assert not value.startswith("C:/")
        assert "\\" not in value
        assert ".." not in value.split("/")


def test_readiness_bundle_markdown_lists_readiness_flags_and_checks():
    doc = bundle.build_readiness_bundle()
    report = bundle.build_markdown_report(doc)

    assert "# Global Protections Readiness Bundle" in report
    assert "Ready for comparable scoring" in report
    assert "Legal-claim anchor source channels" in report
    assert "project_plan_safe" in report
    assert "legal_claim_anchor_source_channels_match_source_matrix" in report
    assert "domain_local_law_gap_blocks_scoring" in report
    assert "regulatory_comparable_scoring_blocked" in report
    assert "not comparable benchmark evidence" in report


def test_readiness_bundle_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    md_out = tmp_path / "bundle.md"

    assert bundle.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "ready_for_comparable_scoring=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["worker_prompts_blocked_for_comparable_run"] == 12
    assert md_out.exists()
    assert "# Global Protections Readiness Bundle" in md_out.read_text(encoding="utf-8")


def test_readiness_bundle_can_write_upstream_artifacts_to_custom_dir(tmp_path):
    chain = bundle.build_readiness_chain(component_dir=tmp_path)
    paths = bundle.write_upstream_artifacts(chain, output_dir=tmp_path)

    expected = {
        "project_plan_json",
        "domain_curation_bundle_json",
        "regulatory_curation_bundle_json",
    }
    assert expected.issubset(paths)
    for key in expected:
        assert paths[key].startswith("external/")
    assert (tmp_path / "global_protections_project_plan.md").exists()
    assert (tmp_path / "developing_country_worker_protections_curation_bundle.md").exists()
    assert (tmp_path / "regulatory_curation_bundle.md").exists()


def test_readiness_bundle_cli_can_write_all_components_to_custom_dir(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    component_dir = tmp_path / "components"

    assert bundle.main([
        "--out",
        str(out),
        "--no-md",
        "--write-all-components",
        "--component-dir",
        str(component_dir),
    ]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["project_plan_json"] == "external/global_protections_project_plan.json"
    assert doc["artifact_paths"]["global_protections_readiness_bundle_json"] == "external/bundle.json"
    assert (component_dir / "developing_country_worker_protections_source_review_validation.json").exists()
    assert (component_dir / "regulatory_domain_seed_proposal.json").exists()
