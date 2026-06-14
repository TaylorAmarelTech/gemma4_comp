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


# ---- bulk corpus screen ---------------------------------------------------

def test_corpus_screen_matches_distinctive_name_no_generic_fp():
    rows = [
        {"name": "Goldfield Mariners Manpower Inc", "status": "delisted"},
        {"name": "ABC International Manpower Services", "status": "cancelled"},  # distinctive only "abc" (too short)
        {"name": "Manpower Recruitment Agency Inc", "status": "valid"},          # all-generic -> skipped
    ]
    articles = [
        {"title": "DMW charges Goldfield Mariners over illegal recruitment scam",
         "url": "u1", "domain": "inquirer.net"},
        {"title": "Weather update for Manila", "url": "u2", "domain": "x.test"},
    ]
    res = am.corpus_screen(rows, fetch=None, articles=articles)
    names = {m["name"] for m in res["matches"]}
    assert "Goldfield Mariners Manpower Inc" in names         # distinctive phrase matched
    assert "ABC International Manpower Services" not in names  # single short token -> no FP
    assert "Manpower Recruitment Agency Inc" not in names     # all-generic -> skipped
    m = next(m for m in res["matches"] if m["name"].startswith("Goldfield"))
    assert "illegal_recruitment" in m["allegation_categories"]
    assert m["registry_status"] == "delisted" and m["article_url"] == "u1"
    assert res["n_names"] == 3 and res["n_articles"] == 2 and res["n_matches"] == 1


def test_gdelt_corpus_pulls_and_dedups():
    def fetch(url):  # every query returns an overlapping article -> dedup by url
        return json.dumps({"articles": [
            {"title": "shared", "url": "https://same", "domain": "d"},
            {"title": "uniq", "url": f"https://{len(url)}", "domain": "d"}]})
    arts = am._gdelt_corpus(fetch, queries=("q1", "q2", "q3"), pace=0)
    urls = {a["url"] for a in arts}
    assert "https://same" in urls and len(arts) == len(urls)  # no dup urls


def test_distinctive_tokens_drops_generic_industry_words():
    assert am._distinctive_tokens("Goldfield Mariners Manpower Inc") == ["goldfield", "mariners"]
    assert am._distinctive_tokens("International Manpower Recruitment Agency Inc") == []


def test_googlenews_corpus_parses_rss_and_dedups():
    xml = ('<rss><channel>'
           '<item><title>DMW shuts Goldfield Mariners - Inquirer</title>'
           '<link>https://g/x1</link><pubDate>Mon, 09 Jun 2026 10:00:00 GMT</pubDate>'
           '<source url="https://inquirer.net">Inquirer</source></item>'
           '<item><title>Weather update</title><link>https://g/x2</link>'
           '<pubDate>Tue, 10 Jun 2026 09:00:00 GMT</pubDate></item>'
           '</channel></rss>')
    arts = am._googlenews_corpus(lambda url: xml, queries=("q1", "q2"), pace=0)  # dedup across queries
    urls = {a["url"] for a in arts}
    assert urls == {"https://g/x1", "https://g/x2"}
    a1 = next(a for a in arts if a["url"] == "https://g/x1")
    assert "Goldfield Mariners" in a1["title"] and a1["domain"] == "https://inquirer.net"


def test_name_in_article_word_boundary_and_stoplist():
    assert am._name_in_article(["goldfield", "mariners"], "dmw shuts goldfield mariners agency")
    assert am._name_in_article(["sunrisex"], "sunrisex agency raided")          # specific single brand
    assert not am._name_in_article(["nation"], "an international firm")          # word boundary: nation != interNATIONal
    assert not am._name_in_article(["manila"], "manila airport arrest")         # common token rejected
    assert not am._name_in_article(["abc"], "abc corp news")                    # too short


def test_build_corpus_merges_sources_dedup():
    gn = '<rss><channel><item><title>t</title><link>https://shared</link></item></channel></rss>'
    gd = json.dumps({"articles": [{"title": "g", "url": "https://shared", "domain": "d"},
                                  {"title": "g2", "url": "https://gd2", "domain": "d"}]})
    def fetch(url):
        return gn if "news.google.com" in url else gd
    arts = am._build_corpus(fetch, sources=("googlenews", "gdelt"), pace=0)
    urls = {a["url"] for a in arts}
    assert urls == {"https://shared", "https://gd2"}  # shared url deduped, googlenews wins


def test_googlenews_entity_requires_name_in_title():
    def fetch(url):
        return ('<rss><channel>'
                '<item><title>DMW cancels license of Goldfield Mariners for exploitation - GMA</title>'
                '<link>https://g/a1</link><source url="https://gma.test">GMA</source></item>'
                '<item><title>Unrelated maritime news</title><link>https://g/a2</link></item>'
                '</channel></rss>')
    hits = am._googlenews_entity("Goldfield Mariners Manpower Inc", fetch)
    assert len(hits) == 1  # only the title containing the distinctive phrase
    assert hits[0].source == "googlenews" and hits[0].adverse  # "cancels license ... exploitation"
    # too-generic name (no 2-token distinctive phrase) -> not queried
    assert am._googlenews_entity("Manpower Services Inc", fetch) == []


def test_verify_matches_uses_model_to_filter_precision():
    matches = [
        {"name": "Goldfield Mariners", "article_title": "DMW charges Goldfield Mariners over scam"},
        {"name": "Saudi Placement", "article_title": "PH lifts deployment ban to Saudi Arabia"},
    ]
    # model says yes to the real one, no to the place-name collision
    def model_fn(prompt):
        return ('{"about_entity": true, "why": "named"}' if "Goldfield" in prompt
                else '{"about_entity": false, "why": "just the country Saudi"}')
    out = am.verify_matches(matches, model_fn)
    by_name = {m["name"]: m for m in out}
    assert by_name["Goldfield Mariners"]["verified"] is True
    assert by_name["Saudi Placement"]["verified"] is False


def test_verify_matches_survives_model_error():
    def boom(prompt):
        raise RuntimeError("model down")
    out = am.verify_matches([{"name": "X", "article_title": "t"}], boom)
    assert out[0]["verified"] is None and "verify_error" in out[0]["verify_why"]


# ---- optional Gemma refinement --------------------------------------------

def test_gemma_classifier_refines_adversity():
    # a headline the keyword classifier misses ("held workers' documents") but the model catches
    def fetch(url):
        return _gdelt_json("Firm held workers documents, says report") if "gdelt" in url else _os_json()
    model_fn = lambda prompt: '{"adverse": true, "category": "abuse"}'
    rep = am.screen_entity("Firm", fetch=fetch, classify=am.make_gemma_classifier(model_fn),
                           sources=("gdelt",))
    assert rep["n_adverse"] == 1 and "abuse" in rep["categories"]
