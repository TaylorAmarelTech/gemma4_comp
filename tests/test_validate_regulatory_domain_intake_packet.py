"""Tests for validating filled regulatory domain intake packets."""
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


intake = _load(
    "build_regulatory_domain_intake_packet",
    _ROOT / "scripts" / "build_regulatory_domain_intake_packet.py",
)
validator = _load(
    "validate_regulatory_domain_intake_packet",
    _ROOT / "scripts" / "validate_regulatory_domain_intake_packet.py",
)


def _pattern(**overrides) -> dict:
    row = {
        "id": "digital_consumer_credit_worker_debt",
        "display_name": "Digital consumer credit, wage advances, and worker debt",
        "candidate_status": "candidate",
        "industry_scope": ["digital lending", "wage-advance products"],
        "legal_dimensions": ["consumer-credit regulation", "employment deductions"],
        "source_channels": ["central bank or financial regulator circulars"],
        "model_miss_patterns": ["invents interest caps, license status, or complaint portals"],
        "prompt_families": ["worker asks whether a job-linked loan can be deducted from wages"],
        "source_gates": ["dated source object for licensing, fee, interest, and collection rules"],
        "do_not_score_until": ["the product type and regulator jurisdiction are concrete"],
    }
    row.update(overrides)
    return row


def _active_seed() -> dict:
    return _pattern(
        id="cross_border_worker_protections",
        display_name="Cross-border worker protections and remedies",
        candidate_status="active_seed",
        active_domain="developing_country_worker_protections",
    )


def _packet() -> dict:
    return intake.build_intake_packet({"patterns": [_pattern(), _active_seed()]})


def _approve_first(packet: dict, domain_id: str = "digital_consumer_credit_worker_debt") -> dict:
    row = packet["candidate_domain_intake"][0]
    row["curator_scope"] = {
        "scope_decision": "approved_for_seed",
        "proposed_domain_id": domain_id,
        "approved_scope_statement": "Evaluate source-gated digital credit and wage-deduction misses",
        "concrete_jurisdiction_strategy": "Start with one regulator jurisdiction per prompt family",
        "primary_public_interest_use_case": "Research benchmark for safe legal uncertainty handling",
    }
    row["required_artifacts"] = {
        "scheme_pack_path": f"configs/duecare/benchmarks/domains/{domain_id}/scheme_prompts.jsonl",
        "grounding_manifest_path": f"configs/duecare/benchmarks/domains/{domain_id}/grounding_sources.json",
        "source_research_plan_path": f"reports/benchmark/{domain_id}_source_research_plan.json",
        "source_review_packet_path": f"reports/benchmark/{domain_id}_source_review_packet.json",
        "expert_review_evidence": "Practitioner review logged on 2026-06-29",
    }
    row["review_gates"] = {
        "privacy_review_status": "approved",
        "source_path_review_status": "approved",
        "expert_review_status": "approved",
        "domain_registry_review_status": "approved",
    }
    row["readiness"] = {
        "ready_for_domain_seed": True,
        "ready_for_prompt_generation": False,
        "ready_for_comparable_scoring": False,
    }
    return packet


def test_blank_packet_validates_as_pending_not_accepted():
    report = validator.validate_intake_packet(_packet())
    meta = report["_meta"]

    assert meta["validation_ok"] is True
    assert meta["candidate_count"] == 1
    assert meta["accepted_for_domain_seed_proposal_count"] == 0
    assert meta["pending_or_deferred_count"] == 1
    assert meta["ready_for_prompt_generation_count"] == 0
    assert meta["ready_for_comparable_scoring_count"] == 0
    assert report["candidate_rows"][0]["validation_status"] == "pending_or_deferred"


def test_approved_row_becomes_domain_seed_proposal_only():
    report = validator.validate_intake_packet(_approve_first(_packet()))
    meta = report["_meta"]

    assert meta["validation_ok"] is True
    assert meta["accepted_for_domain_seed_proposal_count"] == 1
    proposal = report["domain_seed_proposals"][0]
    assert proposal["proposed_domain_id"] == "digital_consumer_credit_worker_debt"
    assert proposal["scheme_pack_path"].endswith("scheme_prompts.jsonl")
    assert proposal["ready_for_prompt_generation"] is False
    assert proposal["ready_for_comparable_scoring"] is False


def test_claimed_prompt_generation_or_scoring_fails_closed():
    packet = _approve_first(_packet())
    packet["candidate_domain_intake"][0]["readiness"]["ready_for_prompt_generation"] = True
    packet["candidate_domain_intake"][0]["readiness"]["ready_for_comparable_scoring"] = True

    report = validator.validate_intake_packet(packet)

    assert report["_meta"]["validation_ok"] is False
    assert "candidate_row_validation_issues" in report["_meta"]["issues"]
    issues = report["candidate_rows"][0]["issues"]
    assert "ready_for_prompt_generation_must_remain_false" in issues
    assert "ready_for_comparable_scoring_must_remain_false" in issues
    assert report["domain_seed_proposals"] == []


def test_url_like_review_evidence_fails_privacy_scan_without_copying_value():
    packet = _approve_first(_packet())
    packet["candidate_domain_intake"][0]["required_artifacts"]["expert_review_evidence"] = (
        "https://example.com/private-review"
    )

    report = validator.validate_intake_packet(packet)
    encoded = json.dumps(report)

    assert report["_meta"]["validation_ok"] is False
    assert "packet_privacy_scan_not_ok" in report["_meta"]["issues"]
    assert "expert_review_evidence_missing_or_unsafe" in report["candidate_rows"][0]["issues"]
    assert "private-review" not in encoded


def test_existing_domain_id_conflict_is_invalid():
    packet = _approve_first(_packet(), domain_id="developing_country_worker_protections")

    report = validator.validate_intake_packet(packet)

    assert report["_meta"]["validation_ok"] is False
    assert "proposed_domain_id_conflicts_existing_domain" in report["candidate_rows"][0]["issues"]


def test_render_markdown_reports_proposal_counts():
    report = validator.validate_intake_packet(_approve_first(_packet()))

    rendered = validator.render_markdown(report)

    assert "# Regulatory Domain Intake Validation" in rendered
    assert "| Accepted domain-seed proposals | 1 |" in rendered
    assert "`digital_consumer_credit_worker_debt`" in rendered


def test_main_validate_and_write(tmp_path):
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "validation.json"
    md = tmp_path / "validation.md"
    packet_path.write_text(json.dumps(_approve_first(_packet())), encoding="utf-8")

    assert validator.main(["--packet", str(packet_path), "--validate"]) == 0
    assert validator.main(["--packet", str(packet_path), "--out", str(out), "--markdown-out", str(md)]) == 0
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_packet(tmp_path):
    packet = _approve_first(_packet())
    packet["candidate_domain_intake"][0]["readiness"]["ready_for_comparable_scoring"] = True
    packet_path = tmp_path / "packet.json"
    out = tmp_path / "validation.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    assert validator.main(["--packet", str(packet_path), "--out", str(out)]) == 1
    assert out.exists()
