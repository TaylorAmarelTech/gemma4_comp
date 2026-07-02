"""Tests for the end-to-end regulatory curation bundle."""
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
    "build_regulatory_curation_bundle",
    _ROOT / "scripts" / "build_regulatory_curation_bundle.py",
)


def test_regulatory_curation_bundle_summarizes_full_blank_chain():
    doc = bundle.build_regulatory_curation_bundle()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["pattern_count"] == 11
    assert summary["active_seed_count"] == 1
    assert summary["candidate_count"] == 10
    assert summary["candidate_queue_count"] == 10
    assert summary["top_candidate_id"]
    assert summary["defer_count"] == 0
    assert summary["candidate_intake_rows"] == 10
    assert summary["active_seed_followups"] == 1
    assert summary["validation_candidate_rows"] == 10
    assert summary["validation_pending_or_deferred_rows"] == 10
    assert summary["validation_accepted_domain_seed_proposals"] == 0
    assert summary["validation_invalid_rows"] == 0
    assert summary["seed_scaffold_operations"] == 0
    assert summary["seed_rejected_proposals"] == 0
    assert summary["ready_for_seed_file_creation"] is False
    assert summary["ready_for_manual_registry_patch"] is False
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["consistency_checks"])
    assert any(check["id"] == "candidate_queue_count_matches_candidates" for check in doc["consistency_checks"])
    assert any(check["id"] == "candidate_queue_keeps_scoring_blocked" for check in doc["consistency_checks"])


def test_regulatory_curation_bundle_keeps_component_summaries_compact():
    doc = bundle.build_regulatory_curation_bundle()
    rendered = json.dumps(doc, ensure_ascii=False)

    assert doc["component_summaries"]["miss_pattern_plan"]["source_gate_count"] > 0
    assert doc["component_summaries"]["miss_pattern_plan"]["candidate_queue_count"] == 10
    assert doc["component_summaries"]["miss_pattern_plan"]["priority_signal_count"] > 0
    assert doc["component_summaries"]["domain_intake_packet"]["candidate_count"] == 10
    assert doc["component_summaries"]["domain_intake_packet"]["candidate_queue_count"] == 10
    assert doc["component_summaries"]["domain_intake_validation"]["pending_or_deferred_count"] == 10
    assert doc["component_summaries"]["domain_seed_proposal"]["accepted_operations"] == 0
    assert "worker asks whether a job-linked loan can be deducted from wages" not in rendered
    assert "candidate_domain_intake" not in doc
    assert "patterns" not in doc


def test_regulatory_curation_bundle_artifact_paths_are_handoff_safe():
    doc = bundle.build_regulatory_curation_bundle()

    assert doc["artifact_paths"]["miss_pattern_plan_json"] == (
        "reports/benchmark/regulatory_miss_pattern_plan.json"
    )
    for value in doc["artifact_paths"].values():
        assert not value.startswith("/")
        assert not value.startswith("C:/")
        assert "\\" not in value
        assert ".." not in value.split("/")


def test_regulatory_curation_bundle_markdown_lists_checks_and_paths():
    doc = bundle.build_regulatory_curation_bundle()
    report = bundle.build_markdown_report(doc)

    assert "# Regulatory Curation Bundle" in report
    assert "Consistency OK" in report
    assert "candidate_count_matches" in report
    assert "Ranked candidate queue" in report
    assert "regulatory_curation_bundle.json" in report
    assert "not comparable benchmark evidence" in report


def test_regulatory_curation_bundle_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    md_out = tmp_path / "bundle.md"

    assert bundle.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "ready_for_comparable_scoring=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["candidate_count"] == 10
    assert doc["summary"]["candidate_queue_count"] == 10
    assert doc["artifact_paths"]["regulatory_curation_bundle_json"] == "external/bundle.json"
    assert doc["artifact_paths"]["regulatory_curation_bundle_markdown"] == "external/bundle.md"
    assert md_out.exists()
    assert "# Regulatory Curation Bundle" in md_out.read_text(encoding="utf-8")


def test_regulatory_curation_bundle_can_write_component_artifacts(tmp_path):
    chain = bundle.build_regulatory_curation_chain(component_dir=tmp_path)
    paths = bundle.write_component_artifacts(chain, output_dir=tmp_path)

    expected_keys = {
        "miss_pattern_plan_json",
        "domain_intake_packet_json",
        "domain_intake_validation_json",
        "domain_seed_proposal_json",
    }
    assert expected_keys.issubset(paths)
    for key in expected_keys:
        assert paths[key].startswith("external/")
    assert (tmp_path / "regulatory_miss_pattern_plan.md").exists()
    assert (tmp_path / "regulatory_domain_seed_proposal.md").exists()
    assert (tmp_path / "regulatory_domain_intake_validation.json").exists()


def test_regulatory_curation_bundle_cli_can_write_components_to_custom_dir(tmp_path, capsys):
    out = tmp_path / "bundle.json"
    component_dir = tmp_path / "components"

    assert bundle.main([
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
    assert doc["artifact_paths"]["miss_pattern_plan_json"] == "external/regulatory_miss_pattern_plan.json"
    assert doc["artifact_paths"]["regulatory_curation_bundle_json"] == "external/bundle.json"
    assert (component_dir / "regulatory_domain_intake_validation.json").exists()
