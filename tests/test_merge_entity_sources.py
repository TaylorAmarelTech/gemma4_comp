"""Tests for scripts/merge_entity_sources.py -- catalogue merge + hygiene.

Offline: pure functions exercised on in-memory dicts; no YAML/network. Covers
deterministic id generation, industry->entity_type mapping, URL/id dedup,
mojibake repair, and the idempotency that lets a swarm be re-merged safely.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mes = _load("merge_entity_sources", _ROOT / "scripts" / "merge_entity_sources.py")


def _raw(**over):
    base = {"name": "Sample Overseas Agency", "url": "https://reg.example.gov/list",
            "country": "ph", "industry": "recruitment_agency"}
    base.update(over)
    return base


# ---- id + slug ------------------------------------------------------------

def test_make_id_matches_existing_scheme():
    # <cc>_<industry[:14]>_<name-slug[:30]>
    assert mes.make_id("PH", "company_registry", "UAE National Economic Register") \
        == "ph_company_regist_uae_national_economic_register"


def test_make_id_is_deterministic_and_lowercase():
    a = mes.make_id("TH", "fishing_seafood", "Dept of Fisheries Vessel List")
    assert a == mes.make_id("th", "fishing_seafood", "Dept of Fisheries Vessel List")
    assert a.startswith("th_fishing_seafoo_")  # 15-char industry trimmed to 14


# ---- text hygiene ---------------------------------------------------------

def test_sanitize_repairs_replacement_char_and_smart_punct():
    assert mes.sanitize_text("Register � federal registry") == "Register - federal registry"
    assert mes.sanitize_text("don’t “quote”") == "don't \"quote\""
    assert mes.sanitize_text("a   b\n c") == "a b c"


# ---- normalization --------------------------------------------------------

def test_normalize_uppercases_country_and_maps_entity_type():
    rec = mes.normalize_record(_raw(industry="money_lender", country="hk"))
    assert rec["country"] == "HK" and rec["entity_type"] == "lender"


def test_normalize_new_industries_map_to_company():
    for ind in ("construction", "fishing_seafood", "manufacturing", "agriculture",
                "care_home", "facility_management"):
        assert mes.normalize_record(_raw(industry=ind))["entity_type"] == "company"
    # domestic-worker placement agencies are recruiters
    assert mes.normalize_record(_raw(industry="domestic_worker"))["entity_type"] == "recruitment_agency"


def test_normalize_unknown_industry_falls_back_to_other():
    rec = mes.normalize_record(_raw(industry="cryptomining"))
    assert rec["industry"] == "other" and rec["entity_type"] == "company"


def test_normalize_clamps_confidence_and_defaults_access_tier():
    assert mes.normalize_record(_raw(confidence=9.0))["confidence"] == 1.0
    assert mes.normalize_record(_raw(access_tier="bogus"))["access_tier"] == "free"


def test_normalize_drops_record_without_http_url():
    assert mes.normalize_record(_raw(url="")) is None
    assert mes.normalize_record(_raw(url="ftp://x")) is None
    assert mes.normalize_record({"url": "https://x", "name": ""}) is None


def test_normalize_generates_id_when_absent_keeps_when_present():
    assert mes.normalize_record(_raw())["id"].startswith("ph_recruitment_ag_")
    assert mes.normalize_record(_raw(id="custom_id"))["id"] == "custom_id"


# ---- merge / dedup --------------------------------------------------------

def test_merge_appends_new_and_skips_url_duplicate():
    existing = [_raw()]
    incoming = [_raw(),  # exact URL dup -> skip
                _raw(name="New Manning Agency", url="https://reg.example.gov/manning",
                     industry="manning_agency")]
    res = mes.merge(existing, incoming)
    assert res["before"] == 1 and res["added"] == 1 and res["skipped"] == 1
    assert res["after"] == 2


def test_merge_url_dedup_ignores_trailing_slash_and_case():
    existing = [_raw(url="https://Reg.Example.GOV/list/")]
    res = mes.merge(existing, [_raw(url="https://reg.example.gov/list")])
    assert res["added"] == 0 and res["skipped"] == 1


def test_merge_is_idempotent_when_remerged():
    existing = [_raw(), _raw(name="B", url="https://reg.example.gov/b")]
    once = mes.merge(existing, [])
    twice = mes.merge(once["sources"], once["sources"])
    assert twice["added"] == 0 and twice["after"] == once["after"]


def test_merge_drops_unusable_incoming():
    res = mes.merge([], [_raw(url=""), _raw()])
    assert res["dropped"] == 1 and res["added"] == 1


def test_merge_sorts_by_country_then_industry_then_name():
    res = mes.merge([], [
        _raw(name="Zeta", url="https://z.gov", country="TH", industry="hotel"),
        _raw(name="Alpha", url="https://a.gov", country="OM", industry="construction"),
        _raw(name="Beta", url="https://b.gov", country="OM", industry="construction"),
    ])
    order = [(s["country"], s["industry"], s["name"]) for s in res["sources"]]
    assert order == [("OM", "construction", "Alpha"), ("OM", "construction", "Beta"),
                     ("TH", "hotel", "Zeta")]


def test_merge_repairs_existing_mojibake_in_place():
    existing = [_raw(name="Register � federal")]
    res = mes.merge(existing, [])
    assert "�" not in res["sources"][0]["name"]
    assert res["sources"][0]["name"] == "Register - federal"


# ---- coverage + coerce ----------------------------------------------------

def test_coverage_counts_countries_industries_and_flags():
    srcs = mes.merge([], [
        _raw(country="OM", has_data_endpoint=True, url_verified=True, url="https://1.gov"),
        _raw(country="TH", industry="fishing_seafood", url="https://2.gov"),
    ])["sources"]
    cov = mes.coverage(srcs)
    assert cov["total"] == 2 and cov["n_countries"] == 2
    assert cov["with_data_endpoint"] == 1 and cov["url_verified"] == 1
    assert set(cov["by_industry"]) == {"recruitment_agency", "fishing_seafood"}


def test_coerce_incoming_accepts_registries_sources_or_bare_list():
    assert mes._coerce_incoming({"registries": [{"a": 1}]}) == [{"a": 1}]
    assert mes._coerce_incoming({"sources": [{"b": 2}]}) == [{"b": 2}]
    assert mes._coerce_incoming([{"c": 3}]) == [{"c": 3}]
    assert mes._coerce_incoming({"nope": 1}) == []
