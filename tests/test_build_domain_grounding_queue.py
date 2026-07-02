"""Tests for scripts/build_domain_grounding_queue.py source-gap generation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bgq = _load("build_domain_grounding_queue", _ROOT / "scripts" / "build_domain_grounding_queue.py")


def test_worker_protection_grounding_queue_blocks_all_until_local_law_verified():
    doc = bgq.build_grounding_queue("developing_country_worker_protections")
    summary = doc["summary"]

    assert summary["prompt_count"] == 12
    assert summary["prompts_ready_for_comparable_run"] == 0
    assert summary["prompts_blocked_for_comparable_run"] == 12
    assert summary["verified_local_law_rows"] == 0
    # every category now has at least a pending manifest row, so the category-tag gap list is empty
    assert summary["missing_category_tags"] == []
    assert "HK" in summary["missing_jurisdictions"]
    assert "EU" in summary["missing_jurisdictions"]
    assert "VE" in summary["missing_jurisdictions"]
    assert "BD" in summary["pending_jurisdictions"]
    assert "KH" in summary["pending_jurisdictions"]
    assert {"BD", "EU", "VE", "CO", "HK"}.issubset(set(summary["missing_verified_local_jurisdictions"]))
    assert {"Gulf", "distant-water fleet"}.issubset(set(summary["unresolved_corridor_scopes"]))
    assert summary["prompts_needing_scope_refinement"] >= 5


def test_queue_reuses_existing_pending_manifest_rows_when_category_matches():
    doc = bgq.build_grounding_queue("developing_country_worker_protections")
    by_prompt = {row["prompt_id"]: row for row in doc["prompt_gaps"]}

    bd_gap = by_prompt["DCWP-SCHEME-0001"]
    assert bd_gap["pending_source_ids"] == ["LOCAL-BD-RECRUITMENT"]
    assert bd_gap["verified_local_source_ids"] == []
    assert bd_gap["missing_verified_local_jurisdictions"] == ["BD"]
    assert bd_gap["missing_category_source"] is False
    assert bd_gap["ready_for_comparable_run"] is False

    queue = {
        (item["jurisdiction"], item["category"]): item
        for item in doc["source_object_queue"]
    }
    bd_item = queue[("BD", "cross_border_recruitment_law")]
    assert bd_item["suggested_source_id"] == "LOCAL-BD-RECRUITMENT"
    assert bd_item["action"] == "curate_and_promote_existing_manifest_row"
    assert bd_item["blocked_prompt_ids"] == ["DCWP-SCHEME-0001"]


def test_queue_creates_missing_manifest_row_suggestions_for_uncovered_prompts():
    doc = bgq.build_grounding_queue("developing_country_worker_protections")
    queue = {
        (item["jurisdiction"], item["category"]): item
        for item in doc["source_object_queue"]
    }

    hk_item = queue[("HK", "fee_label_and_wage_recovery")]
    assert hk_item["suggested_source_id"] == "LOCAL-HK-FEE-LABEL-AND-WAGE-RECOVERY"
    assert hk_item["action"] == "add_manifest_row"
    assert hk_item["current_status"] == "missing"
    assert "archive/date trail" in " ".join(hk_item["required_evidence"])

    ve_item = queue[("VE", "tenancy_eviction_worker_housing")]
    assert ve_item["suggested_source_id"] == "LOCAL-VE-TENANCY-EVICTION-WORKER-HOUSING"
    assert ve_item["action"] == "add_manifest_row"

    eu_item = queue[("EU", "education_training_fee_fraud")]
    assert eu_item["suggested_source_id"] == "LOCAL-EU-EDUCATION-TRAINING-FEE-FRAUD"

    # categories whose manifest rows already exist route to curation, not duplicate row suggestions
    kh_item = queue[("KH", "wage_housing_and_association")]
    assert kh_item["suggested_source_id"] == "LOCAL-KH-WAGE-HOUSING-ASSOCIATION"
    assert kh_item["action"] == "curate_and_promote_existing_manifest_row"
    assert kh_item["current_status"] == "needs_source"

    co_item = queue[("CO", "tenancy_eviction_worker_housing")]
    assert co_item["suggested_source_id"] == "LOCAL-CO-VE-TENANCY-WORKER-HOUSING"
    assert co_item["action"] == "curate_and_promote_existing_manifest_row"


def test_grounding_queue_cli_writes_report(tmp_path, capsys):
    out = tmp_path / "queue.json"
    md_out = tmp_path / "queue.md"
    assert bgq.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--md-out",
        str(md_out),
    ]) == 0
    printed = capsys.readouterr().out
    assert "source-object queue items" in printed
    assert "report" in printed
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["_meta"]["domain"] == "developing_country_worker_protections"
    assert doc["summary"]["prompts_blocked_for_comparable_run"] == 12
    report = md_out.read_text(encoding="utf-8")
    assert "# Domain Grounding Curation Queue" in report
    assert "not legal advice" in report
    assert "| Prompts blocked for comparable run | 12 |" in report
    assert "`LOCAL-BD-RECRUITMENT`" in report
    assert "`DCWP-SCHEME-0001`" in report


def test_markdown_report_summarizes_queue_without_prompt_text():
    doc = bgq.build_grounding_queue("developing_country_worker_protections")
    report = bgq.build_markdown_report(doc)

    assert "## Source-Object Queue" in report
    assert "## Scope Refinement Queue" in report
    assert "## Prompt Blockers" in report
    assert "Missing verified-local jurisdictions" in report
    assert "Jurisdictions missing verified local law" in report
    assert "Unresolved corridor scopes" in report
    assert "SCOPE-GULF-FEE-LABEL-AND-WAGE-RECOVERY" in report
    assert "LOCAL-KH-WAGE-HOUSING-ASSOCIATION" in report
    assert "DCWP-SCHEME-0012" in report
    assert "Synthetic composite:" not in report


def test_grounding_queue_cli_can_skip_markdown(tmp_path, capsys):
    out = tmp_path / "queue.json"
    assert bgq.main([
        "--domain",
        "developing_country_worker_protections",
        "--out",
        str(out),
        "--no-md",
    ]) == 0
    printed = capsys.readouterr().out
    assert "report" not in printed
    assert out.exists()
    assert not out.with_suffix(".md").exists()


def test_multi_jurisdiction_prompt_requires_verified_local_for_every_jurisdiction(tmp_path, monkeypatch):
    root = tmp_path
    pack = root / "scheme.jsonl"
    pack.write_text(
        "\n".join([
            json.dumps({
                "id": "P-PARTIAL",
                "text": "synthetic",
                "category": "multi_jurisdiction",
                "corridor": "AA->BB",
            }),
            json.dumps({
                "id": "P-COMPLETE",
                "text": "synthetic",
                "category": "complete_multi_jurisdiction",
                "corridor": "AA->BB",
            }),
        ]),
        encoding="utf-8",
    )
    manifest_path = root / "grounding.json"
    manifest_path.write_text(json.dumps({
        "_meta": {
            "domain": "fixture_domain",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [
            {
                "id": "LOCAL-AA-MULTI",
                "title": "AA local law",
                "jurisdiction": "AA",
                "source_type": "local_law",
                "authority": "official source",
                "url": "https://example.test/aa",
                "verification_status": "verified_local_law",
                "verified_date": "2026-06-29",
                "coverage_tags": ["multi_jurisdiction"],
                "use_limitations": "fixture only",
            },
            {
                "id": "LOCAL-AA-COMPLETE",
                "title": "AA complete local law",
                "jurisdiction": "AA",
                "source_type": "local_law",
                "authority": "official source",
                "url": "https://example.test/aa-complete",
                "verification_status": "verified_local_law",
                "verified_date": "2026-06-29",
                "coverage_tags": ["complete_multi_jurisdiction"],
                "use_limitations": "fixture only",
            },
            {
                "id": "LOCAL-BB-COMPLETE",
                "title": "BB complete local law",
                "jurisdiction": "BB",
                "source_type": "local_law",
                "authority": "official source",
                "url": "https://example.test/bb-complete",
                "verification_status": "verified_local_law",
                "verified_date": "2026-06-29",
                "coverage_tags": ["complete_multi_jurisdiction"],
                "use_limitations": "fixture only",
            },
        ],
    }), encoding="utf-8")

    monkeypatch.setattr(bgq, "_ROOT", root)
    monkeypatch.setattr(bgq, "get_domain", lambda _domain: {"display_name": "Fixture domain"})
    monkeypatch.setattr(bgq, "resolve_scheme_pack", lambda _domain: pack)
    monkeypatch.setattr(bgq, "resolve_grounding_manifest", lambda _domain: manifest_path)

    doc = bgq.build_grounding_queue("fixture_domain")
    by_prompt = {row["prompt_id"]: row for row in doc["prompt_gaps"]}

    partial = by_prompt["P-PARTIAL"]
    assert partial["verified_local_source_ids"] == ["LOCAL-AA-MULTI"]
    assert partial["missing_verified_local_jurisdictions"] == ["BB"]
    assert partial["ready_for_comparable_run"] is False

    complete = by_prompt["P-COMPLETE"]
    assert complete["verified_local_source_ids"] == ["LOCAL-AA-COMPLETE", "LOCAL-BB-COMPLETE"]
    assert complete["missing_verified_local_jurisdictions"] == []
    assert complete["ready_for_comparable_run"] is True


def test_corridor_aliases_and_unresolved_scopes_are_reported():
    doc = bgq.build_grounding_queue("developing_country_worker_protections")
    by_prompt = {row["prompt_id"]: row for row in doc["prompt_gaps"]}

    fee_gap = by_prompt["DCWP-SCHEME-0007"]
    assert fee_gap["jurisdictions"] == ["PH", "HK"]
    assert fee_gap["unresolved_corridor_scopes"] == ["Gulf"]
    assert fee_gap["missing_verified_local_jurisdictions"] == ["PH", "HK"]
    assert fee_gap["ready_for_comparable_run"] is False

    maritime_gap = by_prompt["DCWP-SCHEME-0003"]
    assert maritime_gap["unresolved_corridor_scopes"] == ["distant-water fleet"]

    scopes = {
        (item["scope"], item["category"]): item
        for item in doc["scope_refinement_queue"]
    }
    assert scopes[("Gulf", "fee_label_and_wage_recovery")]["blocked_prompt_ids"] == ["DCWP-SCHEME-0007"]
    assert scopes[("distant-water fleet", "maritime_fisheries")]["suggested_scope_id"] == (
        "SCOPE-DISTANT-WATER-FLEET-MARITIME-FISHERIES"
    )


def test_grounding_queue_rejects_domain_without_manifest():
    with pytest.raises(ValueError, match="has no grounding_manifest"):
        bgq.build_grounding_queue("money_laundering")
