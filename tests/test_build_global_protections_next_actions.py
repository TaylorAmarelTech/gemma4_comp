"""Tests for the global protections next-actions backlog."""
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
    "build_global_protections_next_actions",
    _ROOT / "scripts" / "build_global_protections_next_actions.py",
)
source_matrix_builder = _load(
    "build_global_protections_source_channel_matrix_for_next_actions_tests",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_next_actions_builds_compact_operator_backlog():
    doc = builder.build_next_actions()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["action_count"] == 34
    assert summary["execution_phase_count"] == 5
    assert summary["immediate_action_count"] == 24
    assert summary["blocked_action_count"] == 10
    assert summary["scope_resolution_items"] == 8
    assert summary["source_review_items"] == 6
    assert summary["deferred_source_review_items"] == 9
    assert summary["regulatory_candidate_intake_items"] == 10
    assert summary["regulatory_priority_queue_items"] == 10
    assert summary["regulatory_top_candidate_id"]
    assert summary["grounding_layer_items"] == 1
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    assert summary["actions_preserving_legal_anchor_source_channels"] == 34
    assert summary["execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])
    regulatory_actions = [
        action for action in doc["actions"] if action["item_type"] == "candidate_domain_intake"
    ]
    assert regulatory_actions[0]["pattern_id"] == summary["regulatory_top_candidate_id"]
    assert regulatory_actions[0]["expansion_rank"] == 1
    assert regulatory_actions[0]["is_top_candidate"] is True
    assert [action["expansion_rank"] for action in regulatory_actions] == list(range(1, 11))
    assert [phase["id"] for phase in doc["execution_phases"]] == [
        "phase_01_scope_resolution",
        "phase_02_source_review",
        "phase_03_regulatory_intake",
        "phase_04_deferred_source_review",
        "phase_05_grounding_layer",
    ]
    phase_action_ids = sorted(
        action_id
        for phase in doc["execution_phases"]
        for action_id in phase["action_ids"]
    )
    assert phase_action_ids == sorted(action["id"] for action in doc["actions"])
    assert all(
        flag is False
        for phase in doc["execution_phases"]
        for flag in phase["readiness_after_phase"].values()
    )
    assert all(
        action["required_legal_claim_anchor_source_channel_ids"]
        == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        for action in doc["actions"]
    )
    assert all(
        phase["required_legal_claim_anchor_source_channel_ids"]
        == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        for phase in doc["execution_phases"]
    )


def test_next_actions_keeps_backlog_privacy_safe_and_not_prompt_dump():
    doc = builder.build_next_actions()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert doc["counts_by_lane"]["worker_protection_source_curation"] == 23
    assert doc["counts_by_lane"]["regulatory_candidate_intake"] == 10
    assert doc["counts_by_lane"]["runner_grounding_layer"] == 1


def test_next_actions_markdown_lists_actions_and_non_scoring_rule():
    doc = builder.build_next_actions()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Next Actions" in rendered
    assert "Execution Phases" in rendered
    assert "phase_01_scope_resolution" in rendered
    assert "Immediate actions" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Actions preserving legal-anchor source channels" in rendered
    assert "Execution phases preserving legal-anchor source channels" in rendered
    assert "Regulatory top candidate" in rendered
    assert "GP-SCOPE-001" in rendered
    assert "GP-GROUNDING-LAYER-001" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_next_actions_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "actions.json"
    md_out = tmp_path / "actions.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "34 actions" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["action_count"] == 34
    assert doc["artifact_paths"]["global_protections_next_actions_json"] == "external/actions.json"
    assert doc["artifact_paths"]["global_protections_next_actions_markdown"] == "external/actions.md"
    assert md_out.exists()
    assert "# Global Protections Next Actions" in md_out.read_text(encoding="utf-8")


def test_next_actions_cli_can_write_readiness_artifacts_to_component_dir(tmp_path):
    out = tmp_path / "actions.json"
    component_dir = tmp_path / "components"

    assert builder.main([
        "--out",
        str(out),
        "--no-md",
        "--write-readiness",
        "--component-dir",
        str(component_dir),
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["project_plan_json"] == "external/global_protections_project_plan.json"
    assert doc["artifact_paths"]["global_protections_next_actions_json"] == "external/actions.json"
    assert (component_dir / "global_protections_project_plan.json").exists()
    assert (component_dir / "developing_country_worker_protections_curation_bundle.json").exists()
    assert (component_dir / "regulatory_curation_bundle.json").exists()
