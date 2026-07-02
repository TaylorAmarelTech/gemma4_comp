"""Tests for the regulatory-miss domain intake packet."""
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


def test_default_catalog_builds_blank_safe_intake_packet():
    config_path = _ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    packet = intake.build_intake_packet(config, config_path=config_path)
    meta = packet["_meta"]

    assert meta["safe_for_curator_intake"] is True
    assert meta["source_catalog_sha256"]
    assert meta["candidate_count"] == 10
    assert meta["candidate_queue_count"] == 10
    assert meta["top_candidate_id"]
    assert meta["active_seed_count"] == 1
    assert meta["ready_for_domain_seed_count"] == 0
    assert meta["ready_for_prompt_generation_count"] == 0
    assert meta["ready_for_comparable_scoring_count"] == 0
    assert meta["blank_field_audit"]["ok"] is True
    assert meta["privacy_scan"]["ok"] is True
    assert packet["active_seed_followups"][0]["active_domain"] == "developing_country_worker_protections"
    assert packet["candidate_domain_intake"][0]["pattern_id"] == meta["top_candidate_id"]
    assert packet["candidate_domain_intake"][0]["expansion_priority"]["rank"] == 1
    assert packet["candidate_domain_intake"][0]["expansion_priority"]["ready_for_comparable_scoring"] is False
    assert [row["expansion_priority"]["rank"] for row in packet["candidate_domain_intake"]] == list(range(1, 11))
    assert all(row["curator_scope"]["scope_decision"] == "needs_review" for row in packet["candidate_domain_intake"])
    assert all(row["readiness"]["ready_for_domain_seed"] is False for row in packet["candidate_domain_intake"])


def test_upstream_unsafe_pattern_blocks_intake_without_copying_sensitive_value():
    config = {
        "patterns": [
            _pattern(
                source_url="https://example.com/private-case",
                source_channels=["central bank notices", "https://example.com/private-case"],
            )
        ]
    }

    packet = intake.build_intake_packet(config)
    encoded = json.dumps(packet)

    assert packet["_meta"]["safe_for_curator_intake"] is False
    assert "source_pattern_plan_not_safe" in packet["_meta"]["issues"]
    assert "private-case" not in encoded


def test_blank_field_audit_flags_claimed_ready_rows():
    packet = intake.build_intake_packet({"patterns": [_pattern(), _active_seed()]})
    packet["candidate_domain_intake"][0]["readiness"]["ready_for_domain_seed"] = True

    audit = intake._blank_field_audit(packet)

    assert audit["ok"] is False
    assert "candidate_domain_intake[0].readiness.ready_for_domain_seed_not_false" in audit["issues"]


def test_render_markdown_includes_active_seed_and_intake_rule():
    packet = intake.build_intake_packet({"patterns": [_pattern(), _active_seed()]})

    rendered = intake.render_markdown(packet)

    assert "# Regulatory Domain Intake Packet" in rendered
    assert "`cross_border_worker_protections`" in rendered
    assert "| Ranked candidate queue | 1 |" in rendered
    assert "readiness flags set to `false`" in rendered


def test_main_writes_safe_packet(tmp_path):
    config = tmp_path / "patterns.json"
    out = tmp_path / "packet.json"
    md = tmp_path / "packet.md"
    config.write_text(json.dumps({"patterns": [_pattern(), _active_seed()]}), encoding="utf-8")

    assert intake.main(["--config", str(config), "--validate"]) == 0
    assert intake.main(["--config", str(config), "--out", str(out), "--markdown-out", str(md)]) == 0
    assert out.exists()
    assert md.exists()


def test_main_refuses_unsafe_packet(tmp_path):
    config = tmp_path / "patterns.json"
    out = tmp_path / "packet.json"
    md = tmp_path / "packet.md"
    config.write_text(json.dumps({"patterns": [_pattern(source_channels=["www.example.com/case"])]}), encoding="utf-8")

    assert intake.main(["--config", str(config), "--out", str(out), "--markdown-out", str(md)]) == 1
    assert not out.exists()
    assert not md.exists()
