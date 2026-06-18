"""Tests for scripts/harvest_opensanctions_sources.py.

Pure/offline: the parser maps real OpenSanctions metadata YAML (verbatim fixtures
pulled from opensanctions/opensanctions on 2026-06-18) to our catalog-source shape.
No network, no clone -- YAML text is fed directly.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")  # PyYAML is in the recovery venv

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hos = _load("harvest_opensanctions_sources", _ROOT / "scripts" / "harvest_opensanctions_sources.py")

# --- real fixtures (verbatim from the opensanctions repo) -------------------

GPPB = """\
title: Philippines GPPB Consolidated Blacklisting Report
entry_point: crawler.py
prefix: ph-gppb
coverage:
  frequency: daily
  start: 2026-06-03
summary: >-
  Companies debarred from Philippine government procurement by the
  Government Procurement Policy Board (GPPB).
url: https://onlineblacklistingportal.gppb.gov.ph/
publisher:
  name: Government Procurement Policy Board
  acronym: GPPB
  country: ph
  url: https://www.gppb.gov.ph
  official: true
data:
  url: https://onlineblacklistingportal.gppb.gov.ph/obp-backend/cbr/cbr_public/
  format: JSON
  lang: eng
tags:
  - list.debarment
"""

HK_PEP = """\
title: Hong Kong Principal Officials
entry_point: crawler.py
url: https://www.gov.hk/en/about/govdirectory/po/index.htm
summary: The principal officials of the Government of Hong Kong.
publisher:
  name: GovHK
  country: hk
  url: https://www.gov.hk/en/about/aboutus.htm
  official: true
data:
  url: https://www.gov.hk/en/about/govdirectory/po/index.htm
  format: HTML
tags:
  - list.pep
"""

# a collection has no publisher / no concrete source of its own
COLLECTION = """\
title: Sanctions
type: collection
datasets:
  - us_ofac_sdn
  - eu_fsf
"""


def test_debarment_source_maps_to_full_record():
    rec = hos.to_record(yaml.safe_load(GPPB), region="ph")
    assert rec is not None
    assert rec["category"] == "debarment"
    assert rec["country"] == "PH"                       # uppercased ISO
    assert rec["entity_type"] == "company"
    assert rec["industry"] == "debarment_list"
    assert rec["official"] is True
    assert rec["has_data_endpoint"] is True
    assert rec["data_url"].endswith("/cbr/cbr_public/")
    assert rec["data_format"] == "JSON"
    assert rec["publisher"].startswith("Government Procurement Policy Board")
    assert rec["url_verified"] is False                 # we never claim verified
    assert "no entity data fetched" in rec["notes"]     # license-clean provenance


def test_pep_list_classified_and_individual_typed():
    rec = hos.to_record(yaml.safe_load(HK_PEP), region="hk")
    assert rec["category"] == "pep" and rec["entity_type"] == "individual"
    assert rec["country"] == "HK" and rec["data_format"] == "HTML"


def test_collection_without_publisher_is_skipped():
    assert hos.to_record(yaml.safe_load(COLLECTION), region="_collections") is None


def test_registry_title_overrides_generic_watchlist_tag():
    meta = {"title": "National Company Register", "publisher": {"country": "xx", "name": "Reg"},
            "tags": ["poi"]}
    assert hos.classify(meta) == "registry"


def test_classify_falls_back_to_other_without_tags_or_registry_words():
    meta = {"title": "Most Wanted Fugitives", "publisher": {"name": "X"}}
    assert hos.classify(meta) == "other"


def test_country_prefers_publisher_over_dir():
    # publisher.country (lk) wins over the region dir (_global); a "Register" title
    # classifies as a company registry even with no tags
    meta = {"title": "Sri Lanka Foreign Employment Agency Register",
            "publisher": {"country": "lk", "name": "SLBFE", "official": True},
            "data": {"url": "https://x", "format": "HTML"}, "tags": []}
    rec = hos.to_record(meta, region="_global")
    assert rec["country"] == "LK" and rec["industry"] == "company_registry"


def test_make_id_matches_catalog_shape():
    assert hos.make_id("PH", "Philippines GPPB Consolidated Blacklisting Report",
                       "debarment_list") == "ph_debarment_list_philippines_gppb_consolidated"


def test_harvest_dedups_and_sorts():
    items = [("ph", GPPB), ("ph", GPPB), ("hk", HK_PEP)]
    recs = hos.harvest(items)
    ids = [r["id"] for r in recs]
    assert len(ids) == len(set(ids)) == 2               # GPPB deduped
    assert recs[0]["country"] == "HK"                   # sorted by country


def test_summarize_counts_endpoints_and_categories():
    recs = hos.harvest([("ph", GPPB), ("hk", HK_PEP)])
    s = hos.summarize(recs)
    assert s["total"] == 2 and s["with_endpoint"] == 2 and s["official"] == 2
    assert s["by_category"]["debarment"] == 1 and s["by_category"]["pep"] == 1


def test_emit_yaml_is_propose_only_catalog():
    recs = hos.harvest([("ph", GPPB)])
    text = hos._emit_yaml(recs)
    parsed = yaml.safe_load(text)
    assert parsed["catalog"] == "opensanctions_ported_sources"
    assert "PROPOSE-ONLY" in parsed["purpose"]
    assert parsed["sources"][0]["name"].startswith("Philippines GPPB")
