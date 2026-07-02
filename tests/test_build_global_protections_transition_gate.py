"""Tests for the global protections transition gate."""
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
    "build_global_protections_transition_gate",
    _ROOT / "scripts" / "build_global_protections_transition_gate.py",
)
source_matrix_builder = _load(
    "build_global_protections_source_channel_matrix_for_transition_gate_tests",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_transition_gate_builds_blocked_go_no_go_rows():
    doc = builder.build_transition_gate()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["transition_count"] == 9
    assert summary["blocked_transition_count"] == 9
    assert summary["source_grounding_transition_count"] == 4
    assert summary["temporal_validity_transition_count"] == 5
    assert summary["language_access_transition_count"] == 5
    assert summary["entity_resolution_transition_count"] == 5
    assert summary["remedy_forum_transition_count"] == 5
    assert summary["authority_hierarchy_transition_count"] == 5
    assert summary["coverage_scope_transition_count"] == 5
    assert summary["jurisdiction_chain_transition_count"] == 5
    assert summary["implementation_access_transition_count"] == 5
    assert summary["procedural_burden_transition_count"] == 5
    assert summary["source_review_rows"] == 70
    assert summary["source_review_not_started_rows"] == 70
    assert summary["task_blueprint_count"] == 7
    assert summary["diagnostic_cell_count"] == 7
    assert summary["calibration_case_count"] == 16
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == (
        source_matrix_builder.legal_claim_anchor_source_channel_ids()
    )
    assert summary["transitions_preserving_legal_anchor_source_channels"] == 9
    assert summary["ready_for_manifest_promotion"] is False
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_task_instantiation"] is False
    assert summary["ready_for_model_response_capture"] is False
    assert summary["ready_for_judge_output"] is False
    assert summary["ready_for_judge_calibration"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_transition_gate_names_core_blocked_transitions():
    doc = builder.build_transition_gate()
    keys = {row["transition_key"] for row in doc["transitions"]}

    assert "source_review_to_manifest_promotion" in keys
    assert "manifest_to_prompt_instantiation" in keys
    assert "prompt_to_diagnostic_capture" in keys
    assert "judge_output_to_calibration" in keys
    assert "calibration_to_public_claims" in keys
    assert "calibration_to_comparable_scoring" in keys
    assert all(row["status"] == "blocked" for row in doc["transitions"])
    assert all(row["required_evidence"] for row in doc["transitions"])
    assert all(
        row["required_legal_claim_anchor_source_channel_ids"]
        == source_matrix_builder.legal_claim_anchor_source_channel_ids()
        for row in doc["transitions"]
    )
    source_grounding_rows = [
        row for row in doc["transitions"] if row["source_grounding_gate"]
    ]
    temporal_validity_rows = [
        row for row in doc["transitions"] if row["temporal_validity_gate"]
    ]
    language_access_rows = [
        row for row in doc["transitions"] if row["language_access_gate"]
    ]
    entity_resolution_rows = [
        row for row in doc["transitions"] if row["entity_resolution_gate"]
    ]
    remedy_forum_rows = [
        row for row in doc["transitions"] if row["remedy_forum_gate"]
    ]
    authority_hierarchy_rows = [
        row for row in doc["transitions"] if row["authority_hierarchy_gate"]
    ]
    coverage_scope_rows = [
        row for row in doc["transitions"] if row["coverage_scope_gate"]
    ]
    jurisdiction_chain_rows = [
        row for row in doc["transitions"] if row["jurisdiction_chain_gate"]
    ]
    implementation_access_rows = [
        row for row in doc["transitions"] if row["implementation_access_gate"]
    ]
    procedural_burden_rows = [
        row for row in doc["transitions"] if row["procedural_burden_gate"]
    ]
    assert {row["transition_key"] for row in source_grounding_rows} == {
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in temporal_validity_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in language_access_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in entity_resolution_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in remedy_forum_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in authority_hierarchy_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in coverage_scope_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in jurisdiction_chain_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in implementation_access_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert {row["transition_key"] for row in procedural_burden_rows} == {
        "source_review_to_manifest_promotion",
        "manifest_to_prompt_instantiation",
        "prompt_to_diagnostic_capture",
        "diagnostic_capture_to_judge_output",
        "judge_output_to_calibration",
    }
    assert any(
        "legal-claim anchor source identifiers recorded" in row["required_evidence"]
        for row in source_grounding_rows
    )
    assert any(
        "source-grounding contract findings required" in row["required_evidence"]
        for row in source_grounding_rows
    )
    assert any(
        "temporal-validity status recorded" in row["required_evidence"]
        for row in temporal_validity_rows
    )
    assert any(
        "temporal-validity findings required" in row["required_evidence"]
        for row in temporal_validity_rows
    )
    assert any(
        "source-language and translation-review status recorded" in row["required_evidence"]
        for row in language_access_rows
    )
    assert any(
        "language-access findings required" in row["required_evidence"]
        for row in language_access_rows
    )
    assert any(
        "entity-resolution and registry/license-status basis recorded" in row["required_evidence"]
        for row in entity_resolution_rows
    )
    assert any(
        "entity-resolution findings required" in row["required_evidence"]
        for row in entity_resolution_rows
    )
    assert any(
        "remedy/forum status and complaint-path basis recorded" in row["required_evidence"]
        for row in remedy_forum_rows
    )
    assert any(
        "forum competence and remedy-routing findings required" in row["required_evidence"]
        for row in remedy_forum_rows
    )
    assert any(
        "authority-hierarchy status and controlling-source basis recorded" in row["required_evidence"]
        for row in authority_hierarchy_rows
    )
    assert any(
        "authority-hierarchy findings required" in row["required_evidence"]
        for row in authority_hierarchy_rows
    )
    assert any(
        "coverage-scope status and worker-category basis recorded" in row["required_evidence"]
        for row in coverage_scope_rows
    )
    assert any(
        "coverage-scope findings required" in row["required_evidence"]
        for row in coverage_scope_rows
    )
    assert any(
        "jurisdiction-chain status and cross-border responsibility basis recorded"
        in row["required_evidence"]
        for row in jurisdiction_chain_rows
    )
    assert any(
        "jurisdiction-chain findings required" in row["required_evidence"]
        for row in jurisdiction_chain_rows
    )
    assert any(
        "implementation-access status and operational/enforcement basis recorded"
        in row["required_evidence"]
        for row in implementation_access_rows
    )
    assert any(
        "implementation-access findings required" in row["required_evidence"]
        for row in implementation_access_rows
    )
    assert any(
        "procedural-burden status and deadline/document/evidence basis recorded"
        in row["required_evidence"]
        for row in procedural_burden_rows
    )
    assert any(
        "procedural-burden findings required" in row["required_evidence"]
        for row in procedural_burden_rows
    )


def test_transition_gate_is_privacy_safe_and_not_prompt_or_response_dump():
    doc = builder.build_transition_gate()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "prompt_text" not in encoded
    assert "response_text" not in encoded
    assert "unredacted_response" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert doc["summary"]["consistency_ok"] is True


def test_transition_gate_markdown_lists_transitions_and_non_scoring_rule():
    doc = builder.build_transition_gate()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Transition Gate" in rendered
    assert "Transitions" in rendered
    assert "Source-grounding transitions" in rendered
    assert "Legal-claim anchor source channels" in rendered
    assert "Transitions preserving legal-anchor source channels" in rendered
    assert "Temporal-validity transitions" in rendered
    assert "Language-access transitions" in rendered
    assert "Entity-resolution transitions" in rendered
    assert "Remedy/forum transitions" in rendered
    assert "Authority-hierarchy transitions" in rendered
    assert "Coverage-scope transitions" in rendered
    assert "Jurisdiction-chain transitions" in rendered
    assert "Implementation-access transitions" in rendered
    assert "Procedural-burden transitions" in rendered
    assert "source_review_to_manifest_promotion" in rendered
    assert "calibration_to_comparable_scoring" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_transition_gate_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "transition_gate.json"
    md_out = tmp_path / "transition_gate.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "9 transitions" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["transition_count"] == 9
    assert md_out.exists()
    assert "# Global Protections Transition Gate" in md_out.read_text(encoding="utf-8")
