"""Tests for the sitemap / robots harvester (offline, injected fake fetch)."""
from __future__ import annotations

from duecare.research_tools.monitor import FetchResult
from duecare.research_tools.sitemap import (
    harvest, is_sitemap_url, parse_locs, robots_sitemaps, walk_sitemaps,
)

ROBOTS = "User-agent: *\nDisallow: /private\nSitemap: https://ex.org/sitemap_index.xml\n"
INDEX = ("<?xml version='1.0'?><sitemapindex><sitemap><loc>https://ex.org/sm1.xml</loc>"
         "</sitemap><sitemap><loc>https://ex.org/sm2.xml</loc></sitemap></sitemapindex>")
SM1 = ("<urlset><url><loc>https://ex.org/doc/a</loc></url>"
       "<url><loc>https://ex.org/doc/b</loc></url></urlset>")
SM2 = "<urlset><url><loc>https://ex.org/report/c.pdf</loc></url></urlset>"

PAGES = {
    "https://ex.org/robots.txt": ROBOTS,
    "https://ex.org/sitemap_index.xml": INDEX,
    "https://ex.org/sm1.xml": SM1,
    "https://ex.org/sm2.xml": SM2,
}


def _fetch(url):
    if url in PAGES:
        return FetchResult(ok=True, status=200, text=PAGES[url])
    return FetchResult(ok=False, status=404, error="HTTP 404")


def test_parse_locs_and_robots():
    assert parse_locs(SM1) == ["https://ex.org/doc/a", "https://ex.org/doc/b"]
    assert robots_sitemaps(ROBOTS) == ["https://ex.org/sitemap_index.xml"]


def test_is_sitemap_url():
    assert is_sitemap_url("https://ex.org/sitemap_index.xml")
    assert is_sitemap_url("https://ex.org/foo/sitemap")
    assert not is_sitemap_url("https://ex.org/doc/a")


def test_harvest_from_index_recurses_to_docs():
    docs, stats = harvest(["https://ex.org/sitemap_index.xml"], fetch=_fetch)
    assert set(docs) == {"https://ex.org/doc/a", "https://ex.org/doc/b", "https://ex.org/report/c.pdf"}
    assert stats["docs"] == 3 and stats["errors"] == 0


def test_harvest_from_robots():
    docs, _ = harvest(["https://ex.org/robots.txt"], fetch=_fetch)
    assert "https://ex.org/doc/a" in docs and "https://ex.org/report/c.pdf" in docs


def test_max_docs_cap():
    docs, _ = harvest(["https://ex.org/sitemap_index.xml"], fetch=_fetch, max_docs=2)
    assert len(docs) == 2


def test_url_filter_applied():
    docs, _ = harvest(["https://ex.org/sitemap_index.xml"], fetch=_fetch,
                      url_filter=lambda u: u.endswith(".pdf"))
    assert docs == ["https://ex.org/report/c.pdf"]


def test_max_depth_blocks_recursion():
    # depth 0 fetches the index (a sitemap), but children are at depth 1 > max_depth=0
    docs, _ = harvest(["https://ex.org/sitemap_index.xml"], fetch=_fetch, max_depth=0)
    assert docs == []


def test_walk_sitemaps_streams_and_resumes():
    # streaming sink instead of accumulation
    got = []
    stats = walk_sitemaps(["https://ex.org/sitemap_index.xml"], on_doc=got.append, fetch=_fetch)
    assert set(got) == {"https://ex.org/doc/a", "https://ex.org/doc/b", "https://ex.org/report/c.pdf"}
    assert stats["docs"] == 3

    # resume: pretend sm1 was already walked -> its docs are skipped
    walked = {"https://ex.org/sm1.xml"}
    got2 = []
    walk_sitemaps(["https://ex.org/sitemap_index.xml"], on_doc=got2.append, fetch=_fetch,
                  is_sitemap_seen=lambda u: u in walked, on_sitemap=walked.add)
    assert "https://ex.org/doc/a" not in got2          # sm1 skipped
    assert "https://ex.org/report/c.pdf" in got2       # sm2 still walked
