"""Tests for the global protections source-channel matrix."""
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
    "build_global_protections_source_channel_matrix",
    _ROOT / "scripts" / "build_global_protections_source_channel_matrix.py",
)


def test_source_channel_matrix_builds_rows_for_every_family_and_channel():
    doc = builder.build_source_channel_matrix()
    summary = doc["summary"]

    assert summary["consistency_ok"] is True
    assert summary["safe_for_project_planning"] is True
    assert summary["jurisdiction_family_count"] == 7
    assert summary["source_channel_count"] == 10
    assert summary["authority_tier_count"] == 10
    assert summary["matrix_row_count"] == 70
    assert summary["legal_claim_anchor_rows"] == 14
    assert summary["legal_claim_anchor_source_channel_count"] == 2
    assert summary["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert summary["authenticity_volatility_control_rows"] == 70
    assert summary["informal_authenticity_volatility_control_rows"] == 7
    assert len(doc["matrix_rows"]) == 70
    assert all(count == 7 for count in doc["counts_by_source_channel"].values())
    assert summary["ready_for_manifest_promotion"] is False
    assert summary["ready_for_prompt_generation"] is False
    assert summary["ready_for_training_use"] is False
    assert summary["ready_for_public_claims"] is False
    assert summary["ready_for_worker_facing_use"] is False
    assert summary["ready_for_comparable_scoring"] is False
    assert all(check["ok"] for check in doc["checks"])


def test_source_channel_matrix_keeps_social_publications_as_leads_only():
    doc = builder.build_source_channel_matrix()
    social_rows = [
        row
        for row in doc["matrix_rows"]
        if row["source_channel_id"] == "social_channel_notice_or_scanned_circular"
    ]

    assert len(social_rows) == 7
    assert doc["summary"]["informal_publication_rows"] == 7
    assert doc["summary"]["lead_only_rows"] == 7
    assert all(row["informal_publication"] is True for row in social_rows)
    assert all("lead_only" in row["evidence_status"] for row in social_rows)
    assert all(row["authority_tier"] == "informal_publication_lead" for row in social_rows)
    assert all(row["claim_use"] == "lead_only_never_standalone_legal_claim" for row in social_rows)
    assert all("official-source follow-up" in row["corroboration_required"] for row in social_rows)
    assert all(
        "capture provenance and hash recorded" in row["authenticity_controls_required"]
        for row in social_rows
    )
    assert all(
        "official-source follow-up target recorded" in row["volatility_controls_required"]
        for row in social_rows
    )
    assert all(
        row["informal_publication_claim_boundary"]
        == "lead_only_until_authenticity_volatility_and_official_follow_up_review"
        for row in social_rows
    )
    assert all(row["ready_for_manifest_promotion"] is False for row in social_rows)
    assert all(row["ready_for_comparable_scoring"] is False for row in social_rows)


def test_source_channel_matrix_only_official_law_or_admin_rows_anchor_legal_claims():
    doc = builder.build_source_channel_matrix()
    anchor_rows = [
        row
        for row in doc["matrix_rows"]
        if row["claim_use"].startswith("may_support_legal_claim")
    ]

    assert len(anchor_rows) == 14
    assert {row["source_channel_id"] for row in anchor_rows} == {
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    }
    assert doc["summary"]["legal_claim_anchor_source_channel_ids"] == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert builder.legal_claim_anchor_source_channel_ids() == [
        "official_gazette_or_law_portal",
        "labour_or_migration_ministry_notice",
    ]
    assert all(len(row["corroboration_required"]) >= 3 for row in doc["matrix_rows"])


def test_source_channel_matrix_is_privacy_safe_and_not_url_or_case_dump():
    doc = builder.build_source_channel_matrix()
    encoded = json.dumps(doc, ensure_ascii=False)

    assert "Synthetic composite:" not in encoded
    assert "prompt_family_sketches" not in encoded
    assert "candidate_url" not in encoded
    assert "source_url" not in encoded
    assert "raw_text" not in encoded
    assert "case_text" not in encoded
    assert "https://" not in encoded
    assert "www." not in encoded
    assert doc["summary"]["consistency_ok"] is True


def test_source_channel_matrix_markdown_lists_channels_and_non_scoring_rule():
    doc = builder.build_source_channel_matrix()
    rendered = builder.build_markdown_report(doc)

    assert "# Global Protections Source-Channel Matrix" in rendered
    assert "social_channel_notice_or_scanned_circular" in rendered
    assert "lead_only_never_standalone_legal_claim" in rendered
    assert "may_support_legal_claim_after_source_path_privacy_and_expert_review" in rendered
    assert "lead_only_until_archived_dated_and_public_interest_reviewed" in rendered
    assert "Legal-claim anchor source channel IDs" in rendered
    assert "Authenticity/volatility control rows" in rendered
    assert "Informal authenticity/volatility control rows" in rendered
    assert "Ready for comparable scoring" in rendered
    assert "not comparable benchmark evidence" in rendered


def test_source_channel_matrix_cli_writes_json_and_markdown(tmp_path, capsys):
    out = tmp_path / "source_channel_matrix.json"
    md_out = tmp_path / "source_channel_matrix.md"

    assert builder.main(["--out", str(out), "--md-out", str(md_out)]) == 0
    printed = capsys.readouterr().out
    assert "consistency_ok=true" in printed
    assert "70 rows" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["matrix_row_count"] == 70
    assert md_out.exists()
    assert "# Global Protections Source-Channel Matrix" in md_out.read_text(encoding="utf-8")
