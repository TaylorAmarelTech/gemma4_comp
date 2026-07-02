"""Tests for non-mutating regulatory domain seed scaffold proposals."""
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
    "build_regulatory_domain_intake_packet_for_seed_proposal_tests",
    _ROOT / "scripts" / "build_regulatory_domain_intake_packet.py",
)
validator = _load(
    "validate_regulatory_domain_intake_packet_for_seed_proposal_tests",
    _ROOT / "scripts" / "validate_regulatory_domain_intake_packet.py",
)
seed_proposal = _load(
    "build_regulatory_domain_seed_proposal",
    _ROOT / "scripts" / "build_regulatory_domain_seed_proposal.py",
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


def _validation_with_accepted() -> dict:
    return validator.validate_intake_packet(_approve_first(_packet()))


def test_blank_validation_report_builds_noop_seed_proposal():
    validation = validator.validate_intake_packet(_packet())

    doc = seed_proposal.build_seed_proposal(validation)
    meta = doc["_meta"]

    assert meta["proposal_ok"] is True
    assert meta["accepted_validation_proposals"] == 0
    assert meta["accepted_operations"] == 0
    assert meta["ready_for_seed_file_creation"] is False
    assert meta["ready_for_manual_registry_patch"] is False
    assert meta["ready_for_comparable_scoring"] is False
    assert doc["accepted_operations"] == []


def test_accepted_validation_report_builds_registry_preview_and_file_scaffold():
    doc = seed_proposal.build_seed_proposal(_validation_with_accepted())
    meta = doc["_meta"]

    assert meta["proposal_ok"] is True
    assert meta["accepted_validation_proposals"] == 1
    assert meta["accepted_operations"] == 1
    assert meta["ready_for_seed_file_creation"] is True
    assert meta["ready_for_manual_registry_patch"] is False
    op = doc["accepted_operations"][0]
    assert op["operation"] == "add_domain_seed_scaffold"
    assert op["ready_for_prompt_generation"] is False
    assert op["ready_for_comparable_scoring"] is False
    assert len(op["file_scaffold"]) == 5
    preview = doc["registry_preview"]["domains"]["digital_consumer_credit_worker_debt"]
    assert preview["scheme_pack_format"] == "jsonl"
    assert preview["grounding_manifest"].endswith("grounding_sources.json")
    assert "A_indicator" in preview["rubric_anchors"]


def test_registry_collision_rejects_even_if_validation_report_was_old(tmp_path):
    validation = _validation_with_accepted()
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({
            "domains": {
                "digital_consumer_credit_worker_debt": {
                    "display_name": "Existing",
                    "scheme_pack": "x",
                    "scheme_pack_format": "jsonl",
                    "rag_vertical": "x",
                    "rubric_anchors": {"A_indicator": "x", "B_law": "x", "C_refuse": "x", "D_resources": "x", "E_safety": "x"},
                    "instruments": ["x"],
                    "regulators": ["x"],
                    "jurisdictions": ["x"],
                }
            }
        }),
        encoding="utf-8",
    )

    doc = seed_proposal.build_seed_proposal(validation, registry_path=registry)

    assert doc["_meta"]["proposal_ok"] is False
    assert doc["_meta"]["accepted_operations"] == 0
    assert doc["rejected_proposals"][0]["reasons"] == ["proposed_domain_id_conflicts_current_registry"]


def test_invalid_validation_report_blocks_seed_proposal():
    validation = _validation_with_accepted()
    validation["_meta"]["validation_ok"] = False

    doc = seed_proposal.build_seed_proposal(validation)

    assert doc["_meta"]["proposal_ok"] is False
    assert doc["_meta"]["source_validation_ok"] is False
    assert doc["_meta"]["ready_for_seed_file_creation"] is False


def test_render_markdown_mentions_blocked_registry_patch():
    doc = seed_proposal.build_seed_proposal(_validation_with_accepted())

    rendered = seed_proposal.render_markdown(doc)

    assert "# Regulatory Domain Seed Proposal" in rendered
    assert "| Ready for manual registry patch | false |" in rendered
    assert "`digital_consumer_credit_worker_debt`" in rendered


def test_main_validate_and_write(tmp_path):
    validation = tmp_path / "validation.json"
    out = tmp_path / "seed_proposal.json"
    md = tmp_path / "seed_proposal.md"
    validation.write_text(json.dumps(_validation_with_accepted()), encoding="utf-8")

    assert seed_proposal.main(["--validation", str(validation), "--validate"]) == 0
    assert seed_proposal.main(["--validation", str(validation), "--out", str(out), "--markdown-out", str(md)]) == 0
    assert out.exists()
    assert md.exists()


def test_main_returns_nonzero_for_invalid_validation_report(tmp_path):
    validation_doc = _validation_with_accepted()
    validation_doc["_meta"]["validation_ok"] = False
    validation = tmp_path / "validation.json"
    out = tmp_path / "seed_proposal.json"
    validation.write_text(json.dumps(validation_doc), encoding="utf-8")

    assert seed_proposal.main(["--validation", str(validation), "--out", str(out)]) == 1
    assert out.exists()
