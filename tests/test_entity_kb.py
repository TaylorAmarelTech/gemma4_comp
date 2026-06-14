"""Tests for scripts/entity_kb.py -- the migration-world entity knowledge base.

Pure-offline: exercises normalization, provenance-tier merge/dedup, query
filters, JSONL round-trip, and the committed synthetic sample. ``scripts/`` is
not an installed package, so the module is loaded by path; the frozen
dataclass requires the module be registered in ``sys.modules`` before exec.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_MOD_PATH = _ROOT / "scripts" / "entity_kb.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("entity_kb", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen dataclass needs the module resolvable
    spec.loader.exec_module(mod)
    return mod


ekb = _load_module()


# --- normalization ---------------------------------------------------------

def test_normalize_name_strips_legal_suffixes_only():
    # legal-form suffix + punctuation are dropped...
    assert ekb.normalize_name("Sunrise Overseas Manpower Inc.") == "sunrise overseas manpower"
    assert ekb.normalize_name("Pacific Bridge Recruitment Corp.") == "pacific bridge recruitment"
    # ...but distinguishing industry words are KEPT (conservative, avoids false merges)
    assert ekb.normalize_name("MediCheck Diagnostics Center") == "medicheck diagnostics center"
    # case + whitespace are normalized so surface variants share one key
    assert ekb.normalize_name("MEDICHECK  diagnostics  Center") == ekb.normalize_name("MediCheck Diagnostics Center")


def test_normalize_status_maps_synonyms():
    assert ekb.normalize_status("Licensed") == "valid"
    assert ekb.normalize_status("REVOKED") == "cancelled"
    assert ekb.normalize_status("Blacklisted") == "delisted"
    assert ekb.normalize_status("") == "unknown"
    assert ekb.normalize_status("some-novel-state") == "some-novel-state"


def test_normalize_type_maps_broker_aliases():
    assert ekb.normalize_type("Recruitment-Agency") == "recruitment_agency"
    assert ekb.normalize_type("fixer") == "broker"
    assert ekb.normalize_type("sub agent") == "broker"


def test_entity_types_cover_licensed_industries():
    for t in ("medical_clinic", "training_center", "lender", "financial_services",
              "remittance", "hotel", "company", "security_services"):
        assert t in ekb.ENTITY_TYPES


def test_normalize_type_industry_aliases():
    assert ekb.normalize_type("money lender") == "lender"
    assert ekb.normalize_type("Remittance Company") == "remittance"
    assert ekb.normalize_type("fintech") == "financial_services"
    assert ekb.normalize_type("company registry") == "company"
    assert ekb.normalize_type("hospitality") == "hotel"
    assert ekb.normalize_type("security company") == "security_services"


# --- record_from_dict ------------------------------------------------------

def test_record_from_dict_accepts_alternate_keys():
    rec = ekb.record_from_dict(
        {"agency_name": "Acme Manpower", "poea_no": "POEA-9", "country": "ph",
         "phone": "+63-2-5550-1; +63-917-555-2", "license_status": "active"},
        default_type="recruitment_agency",
    )
    assert rec.entity_type == "recruitment_agency"
    assert rec.name == "Acme Manpower"
    assert rec.license_no == "POEA-9"
    assert rec.jurisdiction == "PH"
    assert rec.status == "valid"
    assert rec.phones == ("+63-2-5550-1", "+63-917-555-2")  # split on ';'


def test_record_from_dict_clamps_confidence():
    assert ekb.record_from_dict({"name": "X", "confidence": 5}).confidence == 1.0
    assert ekb.record_from_dict({"name": "X", "confidence": "bad"}).confidence == 0.5


# --- merge / dedup ---------------------------------------------------------

def test_merge_dedups_by_type_name_jurisdiction():
    # only case / legal-suffix / whitespace differ -> same entity, must merge
    recs = [
        ekb.record_from_dict({"name": "Sunrise Overseas Manpower Inc.", "type": "recruitment_agency",
                              "country": "PH", "phones": ["+63-2-5550-1001"]}),
        ekb.record_from_dict({"name": "SUNRISE  overseas  manpower", "type": "recruitment_agency",
                              "country": "ph", "phones": ["+63-917-555-0000"]}),
    ]
    merged = ekb.merge_entities(recs)
    assert len(merged) == 1
    # phones union, both kept
    assert set(merged[0].phones) == {"+63-2-5550-1001", "+63-917-555-0000"}


def test_merge_keeps_distinct_industry_qualifier_separate():
    # "Sunrise Overseas" vs "Sunrise Overseas Manpower" are NOT collapsed:
    # conservative normalization avoids merging possibly-different entities.
    recs = [
        ekb.record_from_dict({"name": "Sunrise Overseas", "type": "recruitment_agency", "country": "PH"}),
        ekb.record_from_dict({"name": "Sunrise Overseas Manpower", "type": "recruitment_agency", "country": "PH"}),
    ]
    assert len(ekb.merge_entities(recs)) == 2


def test_merge_higher_tier_wins_scalar_fields():
    official = ekb.record_from_dict({"name": "Acme", "type": "employer", "country": "SA",
                                     "status": "valid", "address": "Official Addr",
                                     "source_tier": "official"})
    community = ekb.record_from_dict({"name": "Acme", "type": "employer", "country": "SA",
                                      "status": "watchlisted", "address": "Field Addr",
                                      "notes": "field note", "source_tier": "community"})
    merged = ekb.merge_entities([community, official])  # order should not matter
    assert len(merged) == 1
    m = merged[0]
    assert m.status == "valid"           # official scalar wins
    assert m.address == "Official Addr"  # official scalar wins
    assert m.notes == "field note"       # but official's empty field is filled from community


def test_merge_records_alias_from_variant_name():
    recs = [
        ekb.record_from_dict({"name": "Blue Horizon Crewing Inc.", "type": "manning_agency",
                              "country": "PH", "source_tier": "official"}),
        ekb.record_from_dict({"name": "Blue Horizon Crewing", "type": "manning_agency",
                              "country": "PH", "source_tier": "community"}),
    ]
    merged = ekb.merge_entities(recs)
    assert len(merged) == 1
    # the lower-tier surface form is preserved as an alias when it differs
    assert any("Crewing" in a for a in merged[0].aliases)


def test_merge_skips_nameless_records():
    assert ekb.merge_entities([ekb.record_from_dict({"name": "", "type": "broker"})]) == []


# --- query -----------------------------------------------------------------

def test_query_by_type_and_jurisdiction():
    recs = ekb.load_entities()
    clinics = ekb.query_entities(recs, entity_type="medical_clinic", jurisdiction="PH")
    assert len(clinics) >= 2
    assert all(r.entity_type == "medical_clinic" for r in clinics)


def test_query_by_status_flip():
    recs = ekb.load_entities()
    cancelled = ekb.query_entities(recs, status="cancelled")
    assert any("Pacific Bridge" in r.name for r in cancelled)
    valid = ekb.query_entities(recs, status="valid", entity_type="recruitment_agency")
    assert all(r.status == "valid" for r in valid)


def test_query_by_name_substring_and_alias():
    recs = ekb.load_entities()
    assert ekb.query_entities(recs, name="sunrise")
    # alias hit: the broker record carries a "Fast-Track Recruitment" alias
    assert ekb.query_entities(recs, name="fast-track recruitment")


# --- sample store ----------------------------------------------------------

def test_sample_store_loads_all_entity_types():
    recs = ekb.load_entities()
    assert len(recs) >= 13
    present = {r.entity_type for r in recs}
    # the sample is meant to exercise the full type taxonomy
    for t in ("recruitment_agency", "manning_agency", "employer", "medical_clinic",
              "training_center", "broker", "lender", "sanctioned_entity",
              "regulator", "ngo", "hotline"):
        assert t in present, f"sample missing {t}"


def test_sample_store_is_synthetic_only():
    """Real-not-faked guard: every committed sample record must self-identify
    as synthetic/composite and use a reserved example domain, never a real one."""
    recs = ekb.load_entities()
    for r in recs:
        blob = (r.notes + r.source).lower()
        assert "synthetic" in blob or "composite" in blob, f"{r.name} not labelled synthetic"
        assert ".test" in r.website or not r.website, f"{r.name} has non-example website {r.website}"


def test_stats_shape():
    st = ekb.stats(ekb.load_entities())
    assert st["n_entities"] >= 13
    assert "recruitment_agency" in st["by_type"]
    assert st["by_status"].get("cancelled", 0) >= 1
    assert set(st["by_source_tier"]) <= {"official", "secondary", "community"}


# --- round-trip ------------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    recs = ekb.load_entities()
    out = tmp_path / "rt.jsonl"
    ekb.save_entities(out, recs)
    reloaded = ekb.load_entities(out)
    assert len(reloaded) == len(recs)
    assert {r.key for r in reloaded} == {r.key for r in recs}


def test_load_skips_comment_and_blank_lines(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text(
        "# a comment\n\n"
        '{"entity_type": "ngo", "name": "Helper Org", "jurisdiction": "PH"}\n'
        "// another comment\n",
        encoding="utf-8",
    )
    recs = ekb.load_entities(p)
    assert len(recs) == 1 and recs[0].name == "Helper Org"


def test_ingest_is_propose_only_and_merges(tmp_path):
    """--ingest must merge into a STAGED file and never touch the source store."""
    src = tmp_path / "scraped.json"
    src.write_text(
        '[{"agency_name": "Sunrise Overseas Manpower Inc.", "country": "PH",'
        ' "phones": ["+63-917-555-1234"], "source_tier": "community"}]',
        encoding="utf-8",
    )
    staged = tmp_path / "staged.jsonl"
    store_before = _MOD_PATH  # the real default store must be untouched
    rc = ekb.main(["--ingest", str(src), "--as", "recruitment_agency", "--out", str(staged)])
    assert rc == 0
    assert staged.exists()
    merged = ekb.load_entities(staged)
    # the community phone got merged into the official Sunrise record
    sunrise = [r for r in merged if "sunrise" in ekb.normalize_name(r.name)]
    assert sunrise and "+63-917-555-1234" in sunrise[0].phones
    # default store on disk is unchanged (propose-only)
    assert store_before.exists()


def test_ingest_stamps_jurisdiction_and_type_from_scraper_export(tmp_path):
    """Bridge from the scrapers: a scrape_agency_sources export is a
    {"records": [AgencyProfile...]} envelope whose records carry a sub-region,
    not a country. --as + --jurisdiction must stamp type and origin, and the
    record's own value must still win when present."""
    export = tmp_path / "scraped.json"
    export.write_text(json.dumps({
        "_synthetic": True, "source": "html:dmw_list.html", "n_records": 2,
        "records": [
            {"name": "Sunrise Overseas Manpower Inc.", "license_no": "POEA-1001",
             "status": "valid", "region": "NCR", "phones": ["+63-2-5550-1001"],
             "official_source": "https://example.test/dmw"},
            {"name": "Gulf Star Recruitment", "license_no": "POEA-2002",
             "status": "cancelled", "jurisdiction": "AE"},  # own value must win
        ],
    }), encoding="utf-8")
    staged = tmp_path / "out.jsonl"
    rc = ekb.main(["--ingest", str(export), "--as", "recruitment_agency",
                   "--jurisdiction", "PH", "--out", str(staged)])
    assert rc == 0
    recs = {r.name: r for r in ekb.load_entities(staged)}
    sunrise = recs["Sunrise Overseas Manpower Inc."]
    assert sunrise.entity_type == "recruitment_agency"
    assert sunrise.jurisdiction == "PH"   # stamped (region 'NCR' did NOT leak in)
    gulf = recs["Gulf Star Recruitment"]
    assert gulf.jurisdiction == "AE"      # record's own jurisdiction wins over the stamp


def test_ingest_source_tier_stamp_marks_official_registry(tmp_path):
    """A government registry pull must be stampable as 'official' so it wins
    merges over lower-tier community field reports."""
    export = tmp_path / "dmw.json"
    export.write_text(json.dumps({"records": [
        {"name": "Sunrise Overseas Manpower Inc.", "status": "valid", "region": "NCR"},
    ]}), encoding="utf-8")
    staged = tmp_path / "out.jsonl"
    empty = tmp_path / "empty.jsonl"  # isolate from the default sample store
    rc = ekb.main(["--store", str(empty), "--ingest", str(export), "--as", "recruitment_agency",
                   "--jurisdiction", "PH", "--source-tier", "official", "--out", str(staged)])
    assert rc == 0
    recs = ekb.load_entities(staged)
    assert len(recs) == 1 and recs[0].source_tier == "official"
