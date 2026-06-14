"""Tests for scripts/adverse_media.py -- negative-news / adverse-media screening.

Fully offline: `fetch` and `classify` are injectable, so query building, GDELT +
OpenSanctions parsing, the allegation classifier, risk scoring, and the optional
Gemma refinement are tested with synthetic payloads -- no network, no model.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


am = _load("adverse_media", _ROOT / "scripts" / "adverse_media.py")


def _gdelt_json(*titles):
    return json.dumps({"articles": [
        {"title": t, "url": f"https://news.test/{i}", "seendate": "20260601T120000Z",
         "domain": "news.test", "sourcecountry": "US"} for i, t in enumerate(titles)]})


def _os_json(*entities):
    return json.dumps({"results": [
        {"id": f"os-{i}", "caption": cap, "schema": "Company", "datasets": ["us_ofac_sdn"],
         "properties": {"topics": topics}} for i, (cap, topics) in enumerate(entities)]})


# ---- classifier -----------------------------------------------------------

def test_classify_adverse_detects_allegation_categories():
    assert "trafficking" in am.classify_adverse("Agency boss jailed for human trafficking ring")
    assert "wage_theft" in am.classify_adverse("Workers report unpaid wages and withheld salaries")
    assert set(am.classify_adverse("recruitment scam: unpaid wages")) >= {"illegal_recruitment", "wage_theft"}
    assert am.classify_adverse("Agency opens new training centre") == ()  # benign


# ---- GDELT parsing --------------------------------------------------------

def test_gdelt_search_parses_dates_and_flags_adverse():
    fetch = lambda url: _gdelt_json("Manpower firm charged with forced labour",
                                    "Agency wins industry award")
    hits = am._gdelt_search("Acme Manpower", fetch)
    assert len(hits) == 2
    assert hits[0].date == "2026-06-01"
    adverse = [h for h in hits if h.adverse]
    assert len(adverse) == 1 and "forced_labor" in adverse[0].categories


# ---- OpenSanctions parsing -----------------------------------------------

def test_opensanctions_match_filters_loose_names_and_flags_topics():
    fetch = lambda url: _os_json(("Acme Manpower Corporation", ["sanction"]),
                                 ("Totally Unrelated Bank", ["sanction"]))
    hits = am._opensanctions_search("Acme Manpower", fetch)
    # only the well-matching caption survives the name-match threshold
    assert len(hits) == 1
    assert hits[0].kind == "sanction" and hits[0].adverse is True
    assert hits[0].extra["name_match"] >= 0.5


# ---- risk scoring ---------------------------------------------------------

def test_score_risk_sanctions_is_high():
    hits = [am.AdverseHit(source="opensanctions", kind="sanction", title="X",
                          adverse=True, categories=("enforcement",))]
    assert am.score_risk(hits)["risk"] == "high"


def test_score_risk_serious_single_news_is_high():
    hits = [am.AdverseHit(source="gdelt", kind="news", title="t", adverse=True,
                          categories=("trafficking",))]
    assert am.score_risk(hits)["risk"] == "high"


def test_score_risk_levels():
    mild = [am.AdverseHit(source="gdelt", kind="news", title="t", adverse=True, categories=("fraud",))]
    assert am.score_risk(mild)["risk"] == "elevated"
    benign = [am.AdverseHit(source="gdelt", kind="news", title="t", adverse=False)]
    assert am.score_risk(benign)["risk"] == "low"
    assert am.score_risk([])["risk"] == "no_signal"
    three = [am.AdverseHit(source="gdelt", kind="news", title=str(i), adverse=True, categories=("fraud",))
             for i in range(3)]
    assert am.score_risk(three)["risk"] == "high"


# ---- end to end (injected fetch) ------------------------------------------

def test_screen_entity_combines_sources_and_routes_by_url():
    def fetch(url):
        if "gdeltproject" in url:
            return _gdelt_json("Recruiter convicted of trafficking migrant workers")
        if "opensanctions" in url:
            return _os_json(("Acme Manpower", ["debarment"]))
        return "{}"
    rep = am.screen_entity("Acme Manpower", country="PH", fetch=fetch, screened_at="2026-06-13")
    assert rep["risk"] == "high"
    assert rep["n_adverse"] == 1 and rep["n_sanctions"] == 1
    assert "trafficking" in rep["categories"]
    assert rep["entity"] == "Acme Manpower" and rep["screened_at"] == "2026-06-13"
    # adverse hits are surfaced first
    assert rep["hits"][0]["adverse"] is True


def test_screen_entity_no_signal_when_clean():
    fetch = lambda url: _gdelt_json() if "gdelt" in url else _os_json()
    rep = am.screen_entity("Spotless Recruitment", fetch=fetch)
    assert rep["risk"] == "no_signal" and rep["n_news"] == 0


def test_screen_entity_survives_fetch_error():
    def boom(url):
        raise ConnectionError("network down")
    rep = am.screen_entity("X", fetch=boom)
    assert rep["risk"] in ("no_signal", "low")  # errors degrade gracefully, no crash


# ---- optional Gemma refinement --------------------------------------------

def test_gemma_classifier_refines_adversity():
    # a headline the keyword classifier misses ("held workers' documents") but the model catches
    def fetch(url):
        return _gdelt_json("Firm held workers documents, says report") if "gdelt" in url else _os_json()
    model_fn = lambda prompt: '{"adverse": true, "category": "abuse"}'
    rep = am.screen_entity("Firm", fetch=fetch, classify=am.make_gemma_classifier(model_fn),
                           sources=("gdelt",))
    assert rep["n_adverse"] == 1 and "abuse" in rep["categories"]
