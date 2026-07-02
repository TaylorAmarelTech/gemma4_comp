"""Tests for non-mutating grounding-manifest proposals."""
from __future__ import annotations

import importlib.util
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


review_builder = _load(
    "build_domain_source_review_packet_for_manifest_proposal_tests",
    _ROOT / "scripts" / "build_domain_source_review_packet.py",
)
review_validator = _load(
    "validate_domain_source_review_packet_for_manifest_proposal_tests",
    _ROOT / "scripts" / "validate_domain_source_review_packet.py",
)
proposal_builder = _load(
    "build_domain_grounding_manifest_proposal",
    _ROOT / "scripts" / "build_domain_grounding_manifest_proposal.py",
)
grounding = _load(
    "domain_grounding_for_manifest_proposal_tests",
    _ROOT / "scripts" / "domain_grounding.py",
)


def _packet():
    return review_builder.build_source_review_packet("developing_country_worker_protections")


def _fill_valid_source_row(row, *, title="Official source fixture"):
    row.update({
        "candidate_title": title,
        "candidate_authority": "Official Labour Department",
        "candidate_url": "https://www.example.gov/source",
        "candidate_archive_url": "https://archive.example.org/source",
        "candidate_source_type": "official_regulator_guidance",
        "candidate_publication_date": "2026-06-01",
        "candidate_accessed_date": "2026-06-29",
        "candidate_language": "en",
        "official_or_public_interest": "official",
        "legal_scope_note": "Synthetic review fixture for local-law scope.",
        "privacy_notes": "No worker or complainant data in this synthetic fixture.",
        "pii_risk": "none_detected",
        "license_or_terms_note": "Public official web page fixture.",
        "reviewer_notes": "Reviewed by synthetic domain reviewer.",
        "proposed_manifest_verification_status": "verified_local_law",
        "ready_for_manifest_promotion": True,
        "privacy_review_required": False,
        "expert_review_required": False,
    })


def _validation_report_from_packet(packet):
    return review_validator.validate_source_review_packet(
        packet,
        domain_id="developing_country_worker_protections",
    )


def test_blank_validation_report_builds_noop_manifest_proposal():
    report = _validation_report_from_packet(_packet())

    proposal = proposal_builder.build_grounding_manifest_proposal(
        "developing_country_worker_protections",
        validation_doc=report,
    )

    assert proposal["summary"]["proposal_ok"] is True
    assert proposal["summary"]["candidate_rows"] == 0
    assert proposal["summary"]["accepted_operations"] == 0
    assert proposal["summary"]["ready_for_manual_manifest_patch"] is False
    assert proposal["accepted_operations"] == []
    assert proposal["rejected_candidate_rows"] == []
    assert proposal["summary"]["preview_manifest_source_count"] == (
        proposal["summary"]["current_manifest_source_count"]
    )


def test_new_valid_source_candidate_is_added_to_preview_manifest():
    packet = _packet()
    hk = next(
        row for row in packet["source_candidate_intake_rows"]
        if row["source_id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    )
    _fill_valid_source_row(hk, title="Hong Kong wage recovery official guidance")
    report = _validation_report_from_packet(packet)

    proposal = proposal_builder.build_grounding_manifest_proposal(
        "developing_country_worker_protections",
        validation_doc=report,
    )

    assert proposal["summary"]["proposal_ok"] is True
    assert proposal["summary"]["ready_for_manual_manifest_patch"] is True
    assert proposal["summary"]["add_source_rows"] == 1
    assert proposal["summary"]["promote_existing_source_rows"] == 0
    op = proposal["accepted_operations"][0]
    assert op["operation"] == "add_source_row"
    assert op["source_id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    assert proposal["summary"]["preview_manifest_source_count"] == (
        proposal["summary"]["current_manifest_source_count"] + 1
    )
    grounding.validate_grounding_manifest(proposal["proposed_manifest_preview"])


def test_existing_pending_candidate_promotes_existing_row_without_count_change():
    packet = _packet()
    bd = next(
        row for row in packet["source_candidate_intake_rows"]
        if row["source_id"] == "LOCAL-BD-RECRUITMENT"
    )
    _fill_valid_source_row(bd, title="Bangladesh recruitment official source")
    report = _validation_report_from_packet(packet)

    proposal = proposal_builder.build_grounding_manifest_proposal(
        "developing_country_worker_protections",
        validation_doc=report,
    )

    assert proposal["summary"]["proposal_ok"] is True
    assert proposal["summary"]["promote_existing_source_rows"] == 1
    assert proposal["summary"]["add_source_rows"] == 0
    op = proposal["accepted_operations"][0]
    assert op["operation"] == "promote_existing_source_row"
    assert op["source_id"] == "LOCAL-BD-RECRUITMENT"
    assert op["replaces_status"] == "needs_source"
    assert proposal["summary"]["preview_manifest_source_count"] == (
        proposal["summary"]["current_manifest_source_count"]
    )
    preview_by_id = {
        row["id"]: row
        for row in proposal["proposed_manifest_preview"]["sources"]
    }
    assert preview_by_id["LOCAL-BD-RECRUITMENT"]["verification_status"] == "verified_local_law"
    assert preview_by_id["LOCAL-BD-RECRUITMENT"]["source_type"] != "country_law_placeholder"


def test_candidate_cannot_replace_verified_international_anchor():
    report = {
        "_meta": {"status": "source-review validation report"},
        "summary": {"ok": True},
        "candidate_manifest_rows": [
            {
                "id": "ILO-C029",
                "title": "Wrong local source",
                "jurisdiction": "international",
                "source_type": "official_regulator_guidance",
                "authority": "Official source",
                "url": "https://example.test/source",
                "verification_status": "verified_local_law",
                "verified_date": "2026-06-29",
                "coverage_tags": ["forced_labour"],
                "use_limitations": "Synthetic invalid replacement fixture.",
            }
        ],
    }

    proposal = proposal_builder.build_grounding_manifest_proposal(
        "developing_country_worker_protections",
        validation_doc=report,
    )

    assert proposal["summary"]["proposal_ok"] is False
    assert proposal["summary"]["accepted_operations"] == 0
    assert proposal["summary"]["rejected_candidates"] == 1
    assert "existing_source_row_is_not_pending" in proposal["rejected_candidate_rows"][0]["reasons"]


def test_validation_report_not_ok_blocks_manifest_proposal(tmp_path, capsys):
    validation_path = tmp_path / "validation.json"
    out = tmp_path / "proposal.json"
    validation_path.write_text(json.dumps({
        "_meta": {"status": "source-review validation report"},
        "summary": {"ok": False},
        "candidate_manifest_rows": [],
    }), encoding="utf-8")

    assert proposal_builder.main([
        "--domain",
        "developing_country_worker_protections",
        "--validation-report",
        str(validation_path),
        "--out",
        str(out),
        "--no-md",
    ]) == 1
    printed = capsys.readouterr().out
    assert "ready=false" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["proposal_ok"] is False
    assert doc["validation_issues"] == ["source_review_validation_report_not_ok"]


def test_manifest_proposal_cli_writes_json_and_markdown(tmp_path, capsys):
    packet = _packet()
    hk = next(
        row for row in packet["source_candidate_intake_rows"]
        if row["source_id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    )
    _fill_valid_source_row(hk, title="Hong Kong wage recovery official guidance")
    report = _validation_report_from_packet(packet)
    validation_path = tmp_path / "validation.json"
    out = tmp_path / "proposal.json"
    md_out = tmp_path / "proposal.md"
    validation_path.write_text(json.dumps(report), encoding="utf-8")

    assert proposal_builder.main([
        "--domain",
        "developing_country_worker_protections",
        "--validation-report",
        str(validation_path),
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "accepted operations" in printed
    assert "ready=true" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["ready_for_manual_manifest_patch"] is True
    md = md_out.read_text(encoding="utf-8")
    assert "# Domain Grounding Manifest Proposal" in md
    assert "non-mutating proposal" in md
    assert "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY" in md
