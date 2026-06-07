"""Sitemap / robots harvester -- expand the acquisition frontier from a seed of
sitemap-index, sitemap, and robots.txt URLs into a large list of document URLs.

This is how the 10k-doc program reaches beyond a hand-curated candidate list:
known-good gov/NGO domains publish sitemaps listing thousands of document URLs.

Parsing is regex ``<loc>`` extraction (NOT an XML parser) -- so there is no
entity resolution and therefore no XXE / billion-laughs risk from an untrusted
public sitemap. The network fetch is injected, so harvesting is deterministic
and testable offline.
"""
from __future__ import annotations

import re
from collections import deque
from typing import Callable

from .monitor import FetchResult, default_fetch

_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.I | re.S)
_ROBOTS_SITEMAP = re.compile(r"(?im)^\s*sitemap:\s*(\S+)\s*$")


def parse_locs(xml_text: str) -> list[str]:
    """All ``<loc>`` values from a sitemap or sitemap-index XML body."""
    return [m.group(1).strip() for m in _LOC.finditer(xml_text or "")]


def robots_sitemaps(robots_text: str) -> list[str]:
    """``Sitemap:`` directives from a robots.txt body."""
    return [m.group(1).strip() for m in _ROBOTS_SITEMAP.finditer(robots_text or "")]


def is_sitemap_url(u: str) -> bool:
    """True if a URL looks like a (possibly nested) sitemap rather than a page."""
    ul = (u or "").lower()
    return ul.endswith(".xml") or ul.endswith(".xml.gz") or "sitemap" in ul


# Shared document-URL filter: drop non-content (tags/feeds/assets/error pages)
# and locale homepages / translated pages (keep the English canonical). One
# source of truth for every harvester.
_DENY = ("/tag/", "/tags/", "/category/", "/categories/", "/author/", "/wp-json",
         "/feed", "/comments", "/login", "/search", "/privacy", "/cookie", "/terms",
         "/sitemap", "/rss", "/contact", "error-40", "/404", "/403", "javascript:",
         "mailto:", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
         ".woff", ".zip", ".mp4", ".mp3")
_LOCALE = {"es", "fr", "it", "tr", "ar", "zh", "ru", "de", "pt", "en", "ja", "ko",
           "id", "th", "vi", "hi", "fa", "ur", "my", "km", "ne", "tl", "bn", "pl", "nl"}


def default_doc_filter(url: str) -> bool:
    """Keep substantive English-canonical document URLs; drop nav/assets/errors
    and locale homepages or translated duplicates."""
    import urllib.parse
    ul = (url or "").lower()
    if not ul.startswith("http") or any(d in ul for d in _DENY):
        return False
    path = urllib.parse.urlparse(url).path.strip("/")
    if not path:
        return False
    segs = path.split("/")
    if segs[0] in _LOCALE:
        return False
    return True


def walk_sitemaps(
    seeds: list[str],
    *,
    on_doc: Callable[[str], None],
    fetch: Callable[[str], FetchResult] = default_fetch,
    is_sitemap_seen: Callable[[str], bool] | None = None,
    on_sitemap: Callable[[str], None] | None = None,
    max_depth: int = 6,
    max_docs: int = 10_000_000,
    max_fetches: int = 200_000,
    url_filter: Callable[[str], bool] | None = None,
) -> dict:
    """STREAMING BFS over a sitemap/robots seed forest -- calls ``on_doc(url)``
    for each discovered document URL instead of accumulating them, so memory is
    bounded by the sitemap queue (not the doc count) and it scales to millions.

    A ``robots.txt`` seed contributes its ``Sitemap:`` directives; a sitemap-index
    recurses up to ``max_depth``; any other ``<loc>`` is a document URL (kept only
    if ``url_filter`` passes). Resumable across runs via ``is_sitemap_seen(url)``
    (skip already-walked sitemaps) + ``on_sitemap(url)`` (record a walked one).
    Bounded by ``max_docs`` / ``max_fetches``."""
    queue: deque[tuple[str, int]] = deque((u, 0) for u in seeds)
    seen: set[str] = set()
    fetched = errors = docs = 0

    while queue and docs < max_docs and fetched < max_fetches:
        u, depth = queue.popleft()
        if u in seen:
            continue
        seen.add(u)
        if is_sitemap_seen is not None and is_sitemap_seen(u):
            continue
        res = fetch(u)
        fetched += 1
        if not res.ok:
            errors += 1
            continue   # do NOT mark seen -> a 429/503 sitemap is retried on resume
        if on_sitemap is not None:
            on_sitemap(u)
        if u.lower().rstrip("/").endswith("robots.txt"):
            for sm in robots_sitemaps(res.text):
                if sm not in seen:
                    queue.append((sm, depth))
            continue
        for loc in parse_locs(res.text):
            if is_sitemap_url(loc):
                if depth < max_depth and loc not in seen:
                    queue.append((loc, depth + 1))
            elif not (url_filter and not url_filter(loc)):
                on_doc(loc)
                docs += 1
                if docs >= max_docs:
                    break
    return {"fetched": fetched, "errors": errors, "docs": docs,
            "sitemaps_queued": len(queue)}


def harvest(
    seeds: list[str],
    *,
    fetch: Callable[[str], FetchResult] = default_fetch,
    max_depth: int = 2,
    max_docs: int = 5000,
    max_fetches: int = 1500,
    url_filter: Callable[[str], bool] | None = None,
) -> tuple[list[str], dict]:
    """Collect a deduped list of document URLs (small/in-memory convenience over
    ``walk_sitemaps``). For million-scale use ``walk_sitemaps`` with a store sink."""
    out: list[str] = []
    seen_docs: set[str] = set()

    def _sink(u: str) -> None:
        if u not in seen_docs:
            seen_docs.add(u)
            out.append(u)

    stats = walk_sitemaps(
        seeds, on_doc=_sink, fetch=fetch, max_depth=max_depth,
        max_docs=max_docs, max_fetches=max_fetches, url_filter=url_filter)
    stats["docs"] = len(out)
    return out, stats
