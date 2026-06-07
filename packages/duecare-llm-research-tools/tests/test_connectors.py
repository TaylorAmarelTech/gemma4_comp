"""Tests for source connectors (offline, injected JSON fetch)."""
from __future__ import annotations

from duecare.research_tools.connectors import gdelt_candidates, reliefweb_documents

GDELT_JSON = {"articles": [
    {"url": "https://news.example/a", "title": "Traffickers convicted", "language": "English"},
    {"url": "https://news.example/b", "title": "Recruitment fee abuse", "language": "English"},
    {"url": "https://news.example/a", "title": "dup"},   # duplicate url -> dropped
]}
RW_JSON = {"data": [
    {"id": 101, "fields": {"title": "Migrant worker report", "url": "https://reliefweb.int/r/101",
                            "body": "A detailed report on forced labour and recruitment fees in the corridor.",
                            "primary_country": {"name": "Philippines"}}},
    {"id": 102, "fields": {"title": "No body", "url": "https://reliefweb.int/r/102"}},  # no body -> dropped
]}


def test_gdelt_candidates():
    cands = gdelt_candidates("q", fetch_json=lambda u: GDELT_JSON)
    urls = [c["url"] for c in cands]
    assert urls == ["https://news.example/a", "https://news.example/b"]   # deduped
    assert all(c["source_tier"] == "news" for c in cands)
    assert all("text" not in c for c in cands)                            # url-only -> acquire fetches


def test_reliefweb_documents():
    docs = reliefweb_documents("q", fetch_json=lambda u: RW_JSON)
    assert len(docs) == 1                                                 # second has no body
    d = docs[0]
    assert d["source_tier"] == "ngo_report" and d["text"].startswith("A detailed report")
    assert d["jurisdictions"] == ["Philippines"] and d["url"].endswith("/101")


def test_connectors_empty_response():
    assert gdelt_candidates("q", fetch_json=lambda u: {}) == []
    assert reliefweb_documents("q", fetch_json=lambda u: {}) == []
