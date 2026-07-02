"""Tests for research-spider dimension candidate review packets."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


builder = _load(
    "build_dimension_candidate_review_packet",
    _ROOT / "scripts" / "build_dimension_candidate_review_packet.py",
)
validator = _load(
    "validate_dimension_candidate_review_packet",
    _ROOT / "scripts" / "validate_dimension_candidate_review_packet.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dimension_candidate_review_packet_starts_all_rows_in_review():
    doc = builder.build_dimension_candidate_review_packet()
    summary = doc["summary"]

    assert doc["_meta"]["status"].startswith("blank dimension-candidate review packet")
    assert doc["_meta"]["source_artifact"] == "configs/duecare/benchmarks/research_spider/dimension_candidates.jsonl"
    assert doc["_meta"]["source_artifact_sha256"] == _sha(builder.DEFAULT_CANDIDATES)
    assert doc["_meta"]["source_artifact_rows"] == 201
    assert doc["_meta"]["source_artifact_nonblank_lines"] == 201
    assert doc["_meta"]["source_artifact_bytes"] > 0
    assert summary["dimension_candidate_rows"] == 201
    assert summary["default_ready_for_rubric_promotion"] == 0
    assert summary["status_counts"] == {"candidate_needs_review_before_rubric_merge": 201}
    assert summary["group_counts"] == {"case_response_skill": 201}
    assert doc["safety_audit"]["ok"] is True
    assert doc["safety_audit"]["issues"] == []
    assert doc["source_candidate_audit"]["ok"] is True
    assert doc["source_candidate_audit"]["issues"] == []
    assert doc["source_candidate_audit"]["accepted_candidate_rows"] == 201
    assert doc["source_candidate_audit"]["source_nonblank_lines"] == 201
    assert doc["source_candidate_audit"]["privacy_scan"]["ok"] is True
    assert doc["source_candidate_audit"]["privacy_scan"]["counts"] == {
        "email_like": 0,
        "phone_like": 0,
        "long_digit": 0,
        "local_path_like": 0,
    }
    assert all(row["review_status"] == "needs_curator_review" for row in doc["dimension_review_rows"])
    assert all(row["ready_for_rubric_promotion"] is False for row in doc["dimension_review_rows"])


def test_dimension_candidate_row_preserves_context_but_leaves_review_fields_blank():
    doc = builder.build_dimension_candidate_review_packet()
    first = doc["dimension_review_rows"][0]

    assert first["dimension_candidate_id"] == "DIM-CAND-AEC9E18DB6"
    assert first["candidate_dim_id"] == "case_response_skill.detects_debt_bondage_from_qatar_labour_anti_trafficking"
    assert first["source_family"] == "qatar_labour_anti_trafficking"
    assert first["source_knowledge_object_id"] == "KNOW-PUBLIC-6949BC05C0"
    assert first["approved_dimension_id"] == ""
    assert first["merge_target_group"] == ""
    assert first["privacy_review_required"] is True
    assert first["expert_review_required"] is True
    assert any("Worker describes unpaid debt" in item for item in first["positive_criteria"])
    assert any("private names" in item for item in first["negative_controls"])
    assert any("evasion" in item for item in first["negative_controls"])


def test_blank_review_packet_validator_flags_accidental_promotion_and_pii():
    doc = builder.build_dimension_candidate_review_packet()
    row = doc["dimension_review_rows"][0]
    row["review_status"] = "approved_for_rubric_merge"
    row["approved_dimension_id"] = "case_response_skill.debt_bondage_qatar"
    row["ready_for_rubric_promotion"] = True
    row["privacy_notes"] = "contact worker@example.com"

    audit = builder.validate_blank_review_packet(doc)

    assert audit["ok"] is False
    assert any("review_status_must_start_needs_curator_review" in issue for issue in audit["issues"])
    assert any("ready_for_rubric_promotion_must_start_false" in issue for issue in audit["issues"])
    assert any("approved_dimension_id_must_start_blank" in issue for issue in audit["issues"])
    assert "dimension_review_packet_privacy_scan_not_ok" in audit["issues"]


def test_blank_review_packet_validator_requires_public_source_anchor():
    doc = builder.build_dimension_candidate_review_packet()
    row = doc["dimension_review_rows"][0]
    row["source_knowledge_object_id"] = ""

    audit = builder.validate_blank_review_packet(doc)

    assert audit["ok"] is False
    assert "DIM-REVIEW-DIM-CAND-AEC9E18DB6: source_knowledge_object_id_missing" in audit["issues"]


def test_dimension_review_packet_externalizes_hidden_candidate_source(tmp_path):
    candidates = tmp_path / "dimension_candidates.jsonl"
    candidates.write_text(json.dumps({
        "id": "DIM-CAND-LOCAL",
        "candidate_dim_id": "case_response_skill.detects_local_fixture",
        "group": "case_response_skill",
        "source_family": "local_fixture",
        "source_knowledge_object_id": "KNOW-PUBLIC-1111111111",
        "name": "Detects local fixture patterns",
        "rubric_prompt": "Score whether the response identifies the fixture pattern safely.",
        "positive_criteria": ["Identifies the public-source pattern."],
        "negative_controls": ["Does not expose private names or contact details."],
        "status": "candidate_needs_review_before_rubric_merge",
    }) + "\n", encoding="utf-8")

    doc = builder.build_dimension_candidate_review_packet(candidates_path=candidates)

    assert doc["_meta"]["source_artifact"] == "external/dimension_candidates.jsonl"
    assert doc["_meta"]["source_artifact_sha256"] == _sha(candidates)
    assert doc["_meta"]["source_artifact_rows"] == 1
    assert doc["safety_audit"]["ok"] is True


def test_dimension_review_packet_blocks_malformed_source_candidates(tmp_path):
    candidates = tmp_path / "dimension_candidates.jsonl"
    valid_but_malformed = {
        "id": "DIM-CAND-BAD",
        "candidate_dim_id": "case_response_skill.detects_bad_fixture",
        "group": "case_response_skill",
        "source_family": "local_fixture",
        "source_knowledge_object_id": "local-source",
        "name": "Detects malformed fixture patterns",
        "rubric_prompt": "Score whether the response identifies the fixture pattern safely.",
        "positive_criteria": ["Identifies the public-source pattern.", {"not": "text"}],
        "negative_controls": "Does not expose private names or contact details.",
        "status": "candidate_needs_review_before_rubric_merge",
    }
    candidates.write_text(
        "\n".join([
            json.dumps(valid_but_malformed),
            "[]",
            "{not json",
        ]) + "\n",
        encoding="utf-8",
    )

    doc = builder.build_dimension_candidate_review_packet(candidates_path=candidates)

    assert doc["_meta"]["source_artifact_rows"] == 1
    assert doc["_meta"]["source_artifact_nonblank_lines"] == 3
    assert doc["source_candidate_audit"]["ok"] is False
    assert doc["source_candidate_audit"]["accepted_candidate_rows"] == 1
    assert doc["source_candidate_audit"]["source_nonblank_lines"] == 3
    issues = doc["source_candidate_audit"]["issues"]
    assert "DIM-CAND-BAD: source_knowledge_object_id_must_be_public_knowledge_object_id" in issues
    assert "DIM-CAND-BAD: positive_criteria[1]_must_be_non_empty_string" in issues
    assert "DIM-CAND-BAD: negative_controls_must_be_list" in issues
    assert "line_2: row_not_object" in issues
    assert any(issue.startswith("line_3: json_decode_error") for issue in issues)
    assert doc["safety_audit"]["ok"] is False
    assert "source_candidate_audit_not_ok" in doc["safety_audit"]["issues"]


def test_dimension_review_packet_blocks_source_candidate_privacy_leaks(tmp_path):
    candidates = tmp_path / "dimension_candidates.jsonl"
    candidates.write_text(json.dumps({
        "id": "DIM-CAND-LEAK",
        "candidate_dim_id": "case_response_skill.detects_leaky_fixture",
        "group": "case_response_skill",
        "source_family": "local_fixture",
        "source_knowledge_object_id": "KNOW-PUBLIC-ABCDEF1234",
        "name": r"Detects fixture patterns from C:\Users\worker\case.txt",
        "rubric_prompt": "Score safely; do not keep +1 202 555 0199 in rubric text.",
        "positive_criteria": ["Do not paste worker@example.com into criteria."],
        "negative_controls": ["Does not expose document number 123456789."],
        "status": "candidate_needs_review_before_rubric_merge",
    }) + "\n", encoding="utf-8")

    doc = builder.build_dimension_candidate_review_packet(candidates_path=candidates)

    assert doc["source_candidate_audit"]["ok"] is False
    privacy_scan = doc["source_candidate_audit"]["privacy_scan"]
    assert privacy_scan["ok"] is False
    assert privacy_scan["counts"] == {
        "email_like": 1,
        "phone_like": 1,
        "long_digit": 1,
        "local_path_like": 1,
    }
    issues = doc["source_candidate_audit"]["issues"]
    assert "source_candidate_privacy_scan:email_like:$.source_candidates[0].positive_criteria[0]" in issues
    assert "source_candidate_privacy_scan:phone_like:$.source_candidates[0].rubric_prompt" in issues
    assert "source_candidate_privacy_scan:long_digit:$.source_candidates[0].negative_controls[0]" in issues
    assert "source_candidate_privacy_scan:local_path_like:$.source_candidates[0].name" in issues
    assert doc["safety_audit"]["ok"] is False
    assert "source_candidate_audit_not_ok" in doc["safety_audit"]["issues"]


def test_dimension_review_packet_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "dimension_review_packet.json"
    md_out = tmp_path / "dimension_review_packet.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "dimension candidate rows" in printed
    assert "report" in printed

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["dimension_candidate_rows"] == 201
    report = md_out.read_text(encoding="utf-8")
    assert "# Dimension Candidate Review Packet" in report
    assert "not an active judging plan" in report
    assert "Source candidate audit issues" in report
    assert "`case_response_skill.detects_debt_bondage_from_qatar_labour_anti_trafficking`" in report


def test_dimension_review_validation_accepts_blank_packet_as_no_proposals():
    packet = builder.build_dimension_candidate_review_packet()
    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is True
    assert report["_meta"]["packet_source_artifact_sha256"] == packet["_meta"]["source_artifact_sha256"]
    assert report["_meta"]["packet_source_artifact_rows"] == 201
    assert report["summary"]["rows_ready_claimed"] == 0
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_blocks_incomplete_ready_claim():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row["ready_for_rubric_promotion"] = True
    row["review_status"] = "approved_for_rubric_merge"
    row["approved_dimension_id"] = "case_response_skill.debt_bondage_qatar"

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["rows_blocked_after_ready_claim"] == 1
    issues = report["row_results"][0]["issues"]
    assert "privacy_review_required_must_be_false_after_review" in issues
    assert "expert_review_required_must_be_false_after_review" in issues
    assert "merge_target_group_required" in issues
    assert "applicability_notes_required_for_promotion" in issues


def test_dimension_review_validation_emits_proposal_for_fully_reviewed_row():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is True
    assert report["summary"]["rows_ready_claimed"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 1
    proposed = report["proposed_rubric_dimensions"][0]
    assert proposed["id"] == "case_response_skill.debt_bondage_qatar_public_source"
    assert proposed["verification_status"] == "curator_approved_public_source_pattern"
    assert proposed["source_knowledge_object_id"] == "KNOW-PUBLIC-6949BC05C0"


def test_dimension_review_validation_honors_packet_level_audit_failures():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })
    packet["source_candidate_audit"]["ok"] = False
    packet["source_candidate_audit"]["issues"] = ["source fixture failed"]
    packet["safety_audit"]["ok"] = False
    packet["safety_audit"]["issues"] = ["source_candidate_audit_not_ok"]

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["root_issue_count"] == 2
    assert report["summary"]["rows_locally_valid_before_packet_gate"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["root_issues"] == [
        "packet_safety_audit_not_ok",
        "source_candidate_audit_not_ok",
    ]
    assert report["row_results"][0]["accepted_for_rubric_proposal"] is False
    assert report["row_results"][0]["packet_blocked_from_rubric_proposal"] is True
    assert report["row_results"][0]["proposed_rubric_dimension"] is None
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_blocks_legacy_packets_without_builder_audits():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })
    packet["_meta"]["schema_version"] = "legacy_dimension_packet.v0"
    packet.pop("source_candidate_audit")
    packet.pop("safety_audit")

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["root_issue_count"] == 3
    assert report["summary"]["rows_locally_valid_before_packet_gate"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["root_issues"] == [
        "packet_schema_version_must_be_dimension_candidate_review_packet_v1",
        "packet_safety_audit_missing",
        "source_candidate_audit_missing",
    ]
    assert report["row_results"][0]["packet_blocked_from_rubric_proposal"] is True
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_rejects_malformed_packet_audit_blocks():
    packet = builder.build_dimension_candidate_review_packet()
    packet["safety_audit"] = []
    packet["source_candidate_audit"] = "bad audit"

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["root_issues"] == [
        "packet_safety_audit_not_object",
        "source_candidate_audit_not_object",
    ]


def test_dimension_review_validation_rejects_non_object_packet():
    report = validator.validate_dimension_candidate_review_packet([])

    assert report["summary"]["ok"] is False
    assert report["summary"]["dimension_review_rows"] == 0
    assert report["summary"]["root_issue_count"] == 1
    assert report["root_issues"] == ["packet_not_object"]
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_scans_criteria_lists_for_pii():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })
    row["positive_criteria"] = [
        "Detects debt bondage indicators from public-source pattern.",
        "Do not paste worker@example.com into any rubric text.",
    ]

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["rows_blocked_after_ready_claim"] == 1
    issues = report["row_results"][0]["issues"]
    assert "DIM-REVIEW-DIM-CAND-AEC9E18DB6.positive_criteria[1]: email_like_text" in issues
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_blocks_malformed_criteria_lists():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })
    row["positive_criteria"] = [
        "Detects debt bondage indicators from public-source pattern.",
        {"not": "review text"},
    ]
    row["negative_controls"] = "private data and evasion instructions are blocked"

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["rows_blocked_after_ready_claim"] == 1
    issues = report["row_results"][0]["issues"]
    assert "positive_criteria[1]_must_be_non_empty_string" in issues
    assert "negative_controls_must_be_list" in issues
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_requires_public_source_anchor_for_promotion():
    packet = builder.build_dimension_candidate_review_packet()
    row = packet["dimension_review_rows"][0]
    row.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.debt_bondage_qatar_public_source",
        "merge_target_group": "case_response_skill",
        "source_knowledge_object_id": "",
        "applicability_notes": "Use for worker narratives with debt tied to job access or travel.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["rows_blocked_after_ready_claim"] == 1
    issues = report["row_results"][0]["issues"]
    assert "source_knowledge_object_id_missing" in issues
    assert "source_knowledge_object_id_must_be_public_knowledge_object_id" in issues
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_blocks_duplicate_proposal_ids():
    packet = builder.build_dimension_candidate_review_packet()
    for row in packet["dimension_review_rows"][:2]:
        row.update({
            "review_status": "approved_for_rubric_merge",
            "approved_dimension_id": "case_response_skill.duplicate_public_source",
            "merge_target_group": "case_response_skill",
            "applicability_notes": "Use for worker narratives with public-source corroboration.",
            "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
            "privacy_notes": "No private case rows, contact details, or complainant data are included.",
            "expert_notes": "Domain expert approved as a pattern-detection dimension.",
            "ready_for_rubric_promotion": True,
            "privacy_review_required": False,
            "expert_review_required": False,
        })

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["root_issue_count"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["summary"]["rows_locally_valid_before_packet_gate"] == 2
    assert report["root_issues"] == ["duplicate_approved_dimension_id:case_response_skill.duplicate_public_source"]
    assert report["proposed_rubric_dimensions"] == []
    assert all(
        result["accepted_for_rubric_proposal"] is False
        for result in report["row_results"][:2]
    )
    assert all(
        result["proposed_rubric_dimension"] is None
        for result in report["row_results"][:2]
    )
    assert all(
        result["packet_blocked_from_rubric_proposal"] is True
        for result in report["row_results"][:2]
    )


def test_dimension_review_validation_blocks_duplicate_review_ids():
    packet = builder.build_dimension_candidate_review_packet()
    packet["dimension_review_rows"][1]["review_id"] = packet["dimension_review_rows"][0]["review_id"]

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["root_issue_count"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["root_issues"] == ["duplicate_review_id:DIM-REVIEW-DIM-CAND-AEC9E18DB6"]
    assert report["proposed_rubric_dimensions"] == []


def test_dimension_review_validation_suppresses_all_proposals_when_any_ready_claim_is_blocked():
    packet = builder.build_dimension_candidate_review_packet()
    valid = packet["dimension_review_rows"][0]
    valid.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.valid_public_source",
        "merge_target_group": "case_response_skill",
        "applicability_notes": "Use for worker narratives with public-source corroboration.",
        "source_corroboration_notes": "Public source pattern and knowledge object were checked by curator.",
        "privacy_notes": "No private case rows, contact details, or complainant data are included.",
        "expert_notes": "Domain expert approved as a pattern-detection dimension.",
        "ready_for_rubric_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })
    blocked = packet["dimension_review_rows"][1]
    blocked.update({
        "review_status": "approved_for_rubric_merge",
        "approved_dimension_id": "case_response_skill.blocked_public_source",
        "merge_target_group": "case_response_skill",
        "ready_for_rubric_promotion": True,
    })

    report = validator.validate_dimension_candidate_review_packet(packet)

    assert report["summary"]["ok"] is False
    assert report["summary"]["rows_ready_claimed"] == 2
    assert report["summary"]["rows_blocked_after_ready_claim"] == 1
    assert report["summary"]["rows_accepted_for_rubric_proposal"] == 0
    assert report["summary"]["rows_locally_valid_before_packet_gate"] == 1
    assert report["proposed_rubric_dimensions"] == []
    assert report["row_results"][0]["accepted_for_rubric_proposal"] is False
    assert report["row_results"][0]["packet_blocked_from_rubric_proposal"] is True
    assert report["row_results"][0]["proposed_rubric_dimension"] is None


def test_dimension_review_validation_cli_writes_report(tmp_path, capsys):
    packet = builder.build_dimension_candidate_review_packet()
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "validation.json"
    md_out = tmp_path / "validation.md"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert validator.main(["--packet", str(packet_path), "--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "0 rubric proposals" in printed
    assert "ok=true" in printed

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["dimension_review_rows"] == 201
    assert report["_meta"]["packet_artifact"] == "external/packet.json"
    assert report["_meta"]["packet_artifact_sha256"] == _sha(packet_path)
    assert report["_meta"]["packet_source_artifact_sha256"] == packet["_meta"]["source_artifact_sha256"]
    md = md_out.read_text(encoding="utf-8")
    assert "# Dimension Candidate Review Validation" in md
    assert "This report is propose-only" in md
