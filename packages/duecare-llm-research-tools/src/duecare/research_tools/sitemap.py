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

from typing import Callable

import re

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


def harvest(
    seeds: list[str],
    *,
    fetch: Callable[[str], FetchResult] = default_fetch,
    max_depth: int = 2,
    max_docs: int = 5000,
    max_fetches: int = 1500,
    url_filter: Callable[[str], bool] | None = None,
) -> tuple[list[str], dict]:
    """BFS from seed sitemap/robots URLs to a deduped list of document URLs.

    A ``robots.txt`` seed contributes its ``Sitemap:`` directives. A sitemap-index
    (``<loc>`` pointing at more ``.xml``) is recursed up to ``max_depth``. Any
    other ``<loc>`` is a document URL (optionally kept only if ``url_filter``
    returns True). Bounded by ``max_docs`` / ``max_fetches``. Deterministic given
    ``fetch``; pure (writes nothing)."""
    seen: set[str] = set()
    doc_urls: list[str] = []
    doc_set: set[str] = set()
    queue: list[tuple[str, int]] = [(u, 0) for u in seeds]
    fetched = errors = 0

    while queue and len(doc_urls) < max_docs and fetched < max_fetches:
        u, depth = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        res = fetch(u)
        fetched += 1
        if not res.ok:
            errors += 1
            continue
        if u.lower().rstrip("/").endswith("robots.txt"):
            for sm in robots_sitemaps(res.text):
                if sm not in seen:
                    queue.append((sm, depth))
            continue
        for loc in parse_locs(res.text):
            if is_sitemap_url(loc):
                if depth < max_depth and loc not in seen:
                    queue.append((loc, depth + 1))
            elif loc not in doc_set:
                if url_filter and not url_filter(loc):
                    continue
                doc_set.add(loc)
                doc_urls.append(loc)
                if len(doc_urls) >= max_docs:
                    break
    return doc_urls, {"fetched": fetched, "errors": errors,
                      "docs": len(doc_urls), "queue_remaining": len(queue)}
