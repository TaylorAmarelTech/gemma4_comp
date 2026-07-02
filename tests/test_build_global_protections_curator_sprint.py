"""Tests for the global protections curator sprint packet."""
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
    "build_global_protections_curator_sprint",
    _ROOT / "scripts" / "build_global_protections_curator_sprint.py",
)


def test_curator_sprint_builds_immediate_handoff():
    doc = builder.build_curator_sprint()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["sprint_item_count"] == 24
    assert summary["execution_phase_count"] == 5
    assert summary["scope_resolution_items"] == 8
    assert summary["source_review_items"] == 6
    assert summary["regulatory_candidate_intake_items"] == 10
    assert summary["regulatory_priority_queue_items"] == 10
    assert summary["regulatory_top_candidate_id"]
    assert summary["blocked_later_items"] == 10
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["sprint_items_preserving_legal_anchor_source_channels"] == 24
    assert summary["blocked_later_items_preserving_legal_anchor_source_channels"] == 10
    assert summary["execution_phases_preserving_legal_anchor_source_channels"] == 5
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])
    assert doc["regulatory_candidate_intake_items"][0]["pattern_id"] == summary["regulatory_top_candidate_id"]
    assert doc["regulatory_candidate_intake_items"][0]["expansion_rank"] == 1
    assert doc["regulatory_candidate_intake_items"][0]["is_top_candidate"] is True
    assert [phase["phase_id"] for phase in doc["execution_phase_summary"]] == [
        "phase_01_scope_resolution",
        "phase_02_source_review",
        "phase_03_regulatory_intake",
        "phase_04_deferred_source_review",
        "phase_05_grounding_layer",
    ]
    phase_action_ids = sorted(
        action_id
        for phase in doc["execution_phase_summary"]
        for action_id in [*phase["sprint_action_ids"], *phase["blocked_later_action_ids"]]
    )
    sprint_action_ids = sorted(
        item["backlog_action_id"]
        for section in (
            doc["scope_resolution_items"],
            doc["source_review_items"],
            doc["regulatory_candidate_intake_items"],
            doc["blocked_later_items"],
        )
        for item in section
    )
    assert phase_action_ids == sprint_action_ids
    assert all(
        flag is False
        for phase in doc["execution_phase_summary"]
        for flag in phase["readiness_after_phase"].values()
    )
    expected_channels = [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert all(
        item["required_legal_claim_anchor_source_channel_ids"] == expected_channels
        for section in (
            doc["scope_resolution_items"],
            doc["source_review_items"],
            doc["regulatory_candidate_intake_items"],
            doc["blocked_later_items"],
        )
        for item in section
    )
    assert all(
        phase["required_legal_claim_anchor_source_channel_ids"] == expected_channels
        for phase in doc["execution_phase_summary"]
    )


def test_curator_sprint_includes_reviewer_fields_and_acceptance_checks():
    doc = builder.build_curator_sprint()

    assert len(doc["scope_resolution_items"][0]["review_fields"]) >= 5
    assert len(doc["source_review_items"][0]["acceptance_checks"]) >= 5
    assert doc["source_review_items"][0]["privacy_review_required"] is True
    assert doc["source_review_items"][0]["expert_review_required"] is True
    assert doc["source_review_items"][0]["ready_for_manifest_promotion"] is False
    assert len(doc["regulatory_candidate_intake_items"][0]["review_fields"]) >= 7
    assert doc["regulatory_candidate_intake_items"][0]["priority_signal_count"] > 0
    assert doc["regulatory_candidate_intake_items"][0]["readiness"]["ready_for_prompt_generation"] is False


def test_curator_sprint_is_privacy_safe_and_not_prompt_or_url_dump():
    doc = builder.build_curator_sprint()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded


def test_curator_sprint_markdown_lists_sections_and_exit_gates():
    doc = builder.build_curator_sprint()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Curator Sprint" in rendered
    assert "## Scope Resolution" in rendered
    assert "## Source Review" in rendered
    assert "## Regulatory Candidate Intake" in rendered
    assert "## Execution Phase Summary" in rendered
    assert "phase_01_scope_resolution" in rendered
    assert "Regulatory top candidate" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Sprint items preserving legal-anchor source channels" in rendered
    assert "Execution phases preserving legal-anchor source channels" in rendered
    assert "## Exit Gates" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_curator_sprint_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "sprint.json"
    md_out = tmp_path / "sprint.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "24 sprint items" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["sprint_item_count"] == 24
    assert md_out.exists()
    assert "# Global Protections Curator Sprint" in md_out.read_text(encoding="utf-8")


def test_curator_sprint_cli_can_write_next_actions_to_component_dir(tmp_path):
    out = tmp_path / "sprint.json"
    component_dir = tmp_path / "components"

    assert builder.main([
        "--out",
        str(out),
        "--no-md",
        "--write-next-actions",
        "--component-dir",
        str(component_dir),
    ]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["artifact_paths"]["global_protections_next_actions_json"] == "external/global_protections_next_actions.json"
    assert (component_dir / "global_protections_next_actions.json").exists()
    assert (component_dir / "global_protections_next_actions.md").exists()
