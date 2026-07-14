"""Tests for the source-gated regulatory miss pattern expansion plan."""
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


plan_builder = _load(
    "build_regulatory_miss_pattern_plan",
    _ROOT / "scripts" / "build_regulatory_miss_pattern_plan.py",
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


def test_default_catalog_builds_safe_non_scoring_plan():
    config = json.loads(
        (_ROOT / "configs" / "duecare" / "benchmarks" / "regulatory_miss_patterns.json").read_text(
            encoding="utf-8"
        )
    )

    doc = plan_builder.build_plan(config)
    manifest = doc["manifest"]

    assert manifest["safe_for_research_planning"] is True
    assert manifest["ready_for_comparable_scoring"] is False
    assert manifest["pattern_count"] >= 7
    assert manifest["active_seed_count"] == 1
    assert manifest["candidate_count"] >= 6
    assert manifest["candidate_queue_count"] == manifest["candidate_count"]
    assert manifest["top_candidate_id"] == doc["expansion_queue"][0]["pattern_id"]
    assert manifest["privacy_scan"]["ok"] is True
    assert any(p["active_domain"] == "developing_country_worker_protections" for p in doc["patterns"])
    assert all(p["ready_for_comparable_scoring"] is False for p in doc["patterns"])
    assert all(p["expansion_priority"]["ready_for_prompt_generation"] is False for p in doc["patterns"])
    assert all(row["ready_for_comparable_scoring"] is False for row in doc["expansion_queue"])
    assert [row["rank"] for row in doc["expansion_queue"]] == list(range(1, manifest["candidate_queue_count"] + 1))
    assert doc["expansion_queue"][0]["priority_score"] >= doc["expansion_queue"][-1]["priority_score"]
    assert "privacy_or_retaliation" in doc["coverage_summary"]["priority_signals"]
    assert "source_gate_count" in doc["coverage_summary"]


def test_plan_rejects_urls_and_sensitive_fields_without_copying_values():
    config = {
        "patterns": [
            _pattern(
                source_url="https://example.com/private-case",
                source_channels=["public authority page", "https://example.com/private-case"],
            )
        ]
    }

    doc = plan_builder.build_plan(config)
    encoded = json.dumps(doc)

    assert doc["manifest"]["safe_for_research_planning"] is False
    assert doc["manifest"]["issues"]["pattern_unexpected_fields"] == 1
    assert doc["manifest"]["issues"]["pattern_sensitive_fields_present"] == 1
    assert doc["manifest"]["issues"]["source_channels_contains_unsafe_text"] == 1
    assert "private-case" not in encoded


def test_plan_rejects_8_digit_case_like_values_without_copying_them():
    config = {
        "patterns": [
            _pattern(
                source_gates=["remove copied case12345678 before domain planning"],
            )
        ]
    }

    doc = plan_builder.build_plan(config)
    encoded = json.dumps(doc)

    assert doc["manifest"]["safe_for_research_planning"] is False
    assert doc["manifest"]["issues"]["source_gates_contains_unsafe_text"] == 1
    assert "case12345678" not in encoded


def test_privacy_scan_flags_8_digit_case_like_values_without_copying_them():
    scan = plan_builder._scan_privacy([
        {
            "id": "digital_consumer_credit_worker_debt",
            "source_gates": ["remove copied case12345678 before domain planning"],
        }
    ])
    encoded = json.dumps(scan)

    assert scan["ok"] is False
    assert scan["counts"]["long_digit"] == 1
    assert scan["long_digit_paths"] == ["$[0].source_gates[0]"]
    assert "case12345678" not in encoded


def test_duplicate_ids_are_flagged():
    config = {"patterns": [_pattern(), _pattern()]}

    doc = plan_builder.build_plan(config)

    assert doc["manifest"]["safe_for_research_planning"] is False
    assert doc["manifest"]["issues"]["pattern_id_duplicate"] == 1


def test_render_markdown_includes_summary_and_non_scoring_rule():
    doc = plan_builder.build_plan({"patterns": [_pattern()]})

    rendered = plan_builder.render_markdown(doc)

    assert "# Regulatory Miss Pattern Plan" in rendered
    assert "| Pattern count | 1 |" in rendered
    assert "## Expansion Queue" in rendered
    assert "| Ranked candidate queue | 1 |" in rendered
    assert "Every pattern remains blocked for comparable scoring" in rendered


def test_main_validate_and_write(tmp_path):
    config = tmp_path / "patterns.json"
    out = tmp_path / "plan.json"
    md = tmp_path / "plan.md"
    config.write_text(json.dumps({"patterns": [_pattern()]}), encoding="utf-8")

    assert plan_builder.main(["--config", str(config), "--validate"]) == 0
    assert plan_builder.main(["--config", str(config), "--out", str(out), "--markdown-out", str(md)]) == 0
    assert out.exists()
    assert md.exists()


def test_main_refuses_to_write_unsafe_plan(tmp_path):
    config = tmp_path / "patterns.json"
    out = tmp_path / "plan.json"
    md = tmp_path / "plan.md"
    config.write_text(json.dumps({"patterns": [_pattern(source_channels=["www.example.com/case"])]}), encoding="utf-8")

    assert plan_builder.main(["--config", str(config), "--out", str(out), "--markdown-out", str(md)]) == 1
    assert not out.exists()
    assert not md.exists()
