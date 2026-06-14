"""Tests for scripts/merge_support_orgs.py -- migrant-support-org catalogue merge.

Offline, in-memory dicts. Covers org-type validation, contactability gating
(an org with no URL/phone/email is dropped), URL + (type,name,country) dedup,
INTL country handling, and idempotency.
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


mso = _load("merge_support_orgs", _ROOT / "scripts" / "merge_support_orgs.py")


def _raw(**over):
    base = {"name": "Sample Migrant Helpline", "org_type": "helpline", "country": "ph",
            "url": "https://help.example.org", "contact_phone": "1234",
            "contact_email": "", "services": "24/7 crisis line", "languages": "English",
            "scope": "national", "url_verified": True, "notes": "", "confidence": 0.9}
    base.update(over)
    return base


def test_make_id_scheme():
    assert mso.make_id("PH", "helpline", "Sample Migrant Helpline") == "ph_helpline_sample_migrant_helpline"


def test_normalize_uppercases_country_and_validates_type():
    rec = mso.normalize_org(_raw(country="hk", org_type="HELPLINE"))
    assert rec["country"] == "HK" and rec["org_type"] == "helpline"


def test_normalize_keeps_intl_country():
    assert mso.normalize_org(_raw(country="INTL"))["country"] == "INTL"


def test_unknown_org_type_falls_back_to_other():
    assert mso.normalize_org(_raw(org_type="ufo_club"))["org_type"] == "other"


def test_unknown_scope_defaults_national():
    assert mso.normalize_org(_raw(scope="galactic"))["scope"] == "national"


def test_org_with_no_contact_is_dropped():
    assert mso.normalize_org(_raw(url="", contact_phone="", contact_email="")) is None
    assert mso.normalize_org({"name": "X"}) is None


def test_org_with_only_phone_is_kept():
    rec = mso.normalize_org(_raw(url="", contact_phone="1-888-373-7888", contact_email=""))
    assert rec is not None and rec["contact_phone"] == "1-888-373-7888"


def test_merge_dedup_by_name_type_country_even_without_url():
    existing = [_raw(url="")]
    # same org, no url, slightly different phrasing of name -> still a dup by slug key
    res = mso.merge(existing, [_raw(url="", name="Sample Migrant Helpline")])
    assert res["added"] == 0 and res["skipped"] == 1


def test_merge_dedup_by_url():
    res = mso.merge([_raw()], [_raw(name="Different Name Same URL")])
    assert res["added"] == 0 and res["skipped"] == 1  # URL collision


def test_merge_adds_distinct_org():
    res = mso.merge([_raw()], [_raw(name="Other Shelter", org_type="shelter",
                                    url="https://shelter.example.org")])
    assert res["added"] == 1 and res["after"] == 2


def test_merge_is_idempotent():
    once = mso.merge([_raw(), _raw(name="B", url="https://b.org")], [])
    twice = mso.merge(once["orgs"], once["orgs"])
    assert twice["added"] == 0 and twice["after"] == once["after"]


def test_coverage_counts_contactability():
    orgs = mso.merge([], [
        _raw(country="PH", contact_phone="1348"),
        _raw(country="INTL", org_type="intl_org", url="https://iom.int",
             contact_phone="", contact_email="info@iom.int"),
    ])["orgs"]
    cov = mso.coverage(orgs)
    assert cov["total"] == 2 and cov["with_phone"] == 1 and cov["with_email"] == 1
    assert "helpline" in cov["by_type"]


def test_coerce_accepts_orgs_or_list():
    assert mso._coerce({"orgs": [{"a": 1}]}) == [{"a": 1}]
    assert mso._coerce([{"b": 2}]) == [{"b": 2}]
    assert mso._coerce({"nope": 1}) == []
