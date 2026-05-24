"""Search backend registry.

Each backend exposes ``name`` + ``is_available()`` + ``search(query, top_n)``.
Output shape is fixed:

    {"results": [{"rank": int, "title": str, "url": str, "snippet": str}, ...],
     "source": str, "elapsed_ms": int}
"""
from __future__ import annotations

import json as _json
import os
import time
from typing import Any, Callable, Optional, Protocol

from .._safe_text import smart_excerpt as _smart_excerpt


class SearchBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def search(self, query: str, top_n: int = 5) -> dict: ...


class SearXNGBackend:
    """Self-hosted SearXNG meta-search.

    Config via ``DUECARE_SEARXNG_URL`` env var or constructor arg.
    Calls ``{url}/search?format=json&q={query}``.
    """

    name = "searxng"

    def __init__(self, url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.url = (url or os.environ.get("DUECARE_SEARXNG_URL", "")).rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.url)

    def search(self, query: str, top_n: int = 5) -> dict:
        t0 = time.time()
        if not self.url:
            raise RuntimeError("SearXNG not configured (set DUECARE_SEARXNG_URL)")
        body = self._fetch(query)
        results = []
        for i, r in enumerate((body.get("results") or [])[:top_n], start=1):
            results.append({
                "rank": i,
                "title": (r.get("title") or "").strip(),
                "url": (r.get("url") or "").strip(),
                # Sentence-boundary truncation so the result preview
                # reads as a complete clause, not a mid-word slice.
                # External web content isn't scrubbed (it's the web,
                # not our kernel staging), so we use smart_excerpt
                # rather than fact_excerpt here.
                "snippet": _smart_excerpt(
                    (r.get("content") or r.get("snippet") or "").strip(),
                    400,
                ),
            })
        return {
            "results": results,
            "source": self.name,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }

    def _fetch(self, query: str) -> dict:
        import urllib.parse as _parse
        safe_q = _parse.quote_plus(query)
        endpoint = f"{self.url}/search?format=json&q={safe_q}"
        try:
            import httpx as _httpx
            with _httpx.Client(timeout=self.timeout, follow_redirects=True) as cli:
                r = cli.get(endpoint, headers={"Accept": "application/json"})
                r.raise_for_status()
                return r.json()
        except ImportError:
            import urllib.request as _req
            with _req.urlopen(endpoint, timeout=self.timeout) as resp:
                return _json.loads(resp.read().decode("utf-8", errors="replace"))


class LegacyCallableBackend:
    """Wraps app.state.online_search_call so existing Tavily/Brave/DDG wiring
    stays callable through the new harness.
    """

    def __init__(self, callable_: Callable, name: str = "legacy") -> None:
        self._call = callable_
        self.name = name

    def is_available(self) -> bool:
        return self._call is not None

    def search(self, query: str, top_n: int = 5) -> dict:
        t0 = time.time()
        out = self._call(query, top_n=top_n) or {}
        if not out.get("source"):
            out["source"] = self.name
        if "elapsed_ms" not in out:
            out["elapsed_ms"] = int((time.time() - t0) * 1000)
        return out


DEFAULT_PREFERENCE = ("searxng", "legacy")


def build_registry(app: Any) -> dict[str, SearchBackend]:
    reg: dict[str, SearchBackend] = {}
    reg["searxng"] = SearXNGBackend()
    legacy = getattr(app.state, "online_search_call", None)
    reg["legacy"] = LegacyCallableBackend(legacy)
    return reg


def pick_backend(
    app: Any,
    preferred: Optional[str] = None,
    preference: tuple[str, ...] = DEFAULT_PREFERENCE,
) -> Optional[SearchBackend]:
    reg = build_registry(app)
    candidates: list[str]
    if preferred and preferred in reg:
        candidates = [preferred] + [n for n in preference if n != preferred]
    else:
        candidates = list(preference)
    for name in candidates:
        b = reg.get(name)
        if b is not None and b.is_available():
            return b
    for b in reg.values():
        if b.is_available():
            return b
    return None
