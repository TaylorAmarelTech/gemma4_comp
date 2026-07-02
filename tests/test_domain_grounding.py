"""Tests for scripts/domain_grounding.py source-manifest validation."""
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


dg = _load("domain_grounding", _ROOT / "scripts" / "domain_grounding.py")


def test_worker_protections_grounding_manifest_validates_and_summarizes():
    path = (
        _ROOT
        / "configs"
        / "duecare"
        / "benchmarks"
        / "domains"
        / "developing_country_worker_protections"
        / "grounding_sources.json"
    )

    doc = dg.load_grounding_manifest(path)
    summary = dg.summarize_grounding(doc)

    assert summary["verified_source_count"] == 4
    assert summary["pending_source_count"] >= 6
    assert "BD" in summary["pending_jurisdictions"]
    assert "cross_jurisdiction" in summary["pending_jurisdictions"]
    assert {row["id"] for row in summary["verified_sources"]} == {
        "ILO-C029",
        "ILO-C095",
        "ILO-C181",
        "ILO-C189",
    }
    assert "country-law mappings remain pending" in summary["status"]


def test_load_domain_grounding_resolves_registry_manifest():
    summary = dg.load_domain_grounding("developing_country_worker_protections")

    assert summary["manifest_path"].endswith("grounding_sources.json")
    assert summary["verified_source_count"] == 4
    assert "KE" in summary["pending_jurisdictions"]


def test_pending_rows_cannot_carry_verified_dates():
    doc = {
        "_meta": {
            "domain": "x",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [
            {
                "id": "LOCAL-X",
                "title": "local row",
                "jurisdiction": "XX",
                "source_type": "country_law_placeholder",
                "authority": "official source pending",
                "url": "",
                "verification_status": "needs_source",
                "verified_date": "2026-06-29",
                "coverage_tags": ["local_law"],
                "use_limitations": "pending",
            }
        ],
    }

    with pytest.raises(dg.GroundingError, match="pending rows must not carry verified_date"):
        dg.validate_grounding_manifest(doc)


def test_verified_rows_require_https_url_and_date():
    doc = {
        "_meta": {
            "domain": "x",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [
            {
                "id": "LAW-X",
                "title": "verified row",
                "jurisdiction": "XX",
                "source_type": "local_law",
                "authority": "official source",
                "url": "",
                "verification_status": "verified_local_law",
                "verified_date": None,
                "coverage_tags": ["local_law"],
                "use_limitations": "verified",
            }
        ],
    }

    with pytest.raises(dg.GroundingError, match="verified rows require an HTTPS url"):
        dg.validate_grounding_manifest(doc)


def test_required_text_fields_must_be_non_empty():
    doc = {
        "_meta": {
            "domain": "x",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [
            {
                "id": "ANCHOR-X",
                "title": "",
                "jurisdiction": "international",
                "source_type": "international_standard",
                "authority": "official source",
                "url": "https://example.test/source",
                "verification_status": "verified_international_anchor",
                "verified_date": "2026-06-29",
                "coverage_tags": ["anchor"],
                "use_limitations": "anchor only",
            }
        ],
    }

    with pytest.raises(dg.GroundingError, match="title must be a non-empty string"):
        dg.validate_grounding_manifest(doc)


def test_grounding_cli_prints_summary(tmp_path, capsys):
    manifest = tmp_path / "grounding.json"
    manifest.write_text(json.dumps({
        "_meta": {
            "domain": "x",
            "schema_version": "0.1",
            "last_updated": "2026-06-29",
        },
        "sources": [
            {
                "id": "ANCHOR-X",
                "title": "anchor row",
                "jurisdiction": "international",
                "source_type": "international_standard",
                "authority": "official source",
                "url": "https://example.test/source",
                "verification_status": "verified_international_anchor",
                "verified_date": "2026-06-29",
                "coverage_tags": ["anchor"],
                "use_limitations": "anchor only",
            }
        ],
    }), encoding="utf-8")

    assert dg.main([str(manifest)]) == 0
    out = capsys.readouterr().out
    assert "verified_source_count" in out
    assert "ANCHOR-X" in out
