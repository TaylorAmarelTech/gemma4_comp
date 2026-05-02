"""Fast API-backed web search backends (BYOK -- bring-your-own-key).

For users who want lower latency than browser scraping or DuckDuckGo
HTML (1-3 sec) and are willing to paste an API key for one of these
services. Keys are NEVER read from env at construction time --
they're passed per-call from the request body so the UI can surface a
BYOK panel where users paste keys at runtime (stored in their browser
localStorage, sent on each /api/chat request).

Backends:
  TavilySearchTool    LLM-agent native; free 1k/mo, no card
  BraveSearchTool     Brave Web Search API; free 2k/mo (CC required)
  SerperSearchTool    Google wrapper via Serper; paid (~$50/100k)

For no-key search, use BrowserTool (Playwright; hits brave.com /
duckduckgo.com / ecosia.org via real browser UIs) or WebSearchTool
(DuckDuckGo HTML scrape).

EVERY backend MUST run the PIIFilter before sending the query out and
record an audit log entry (sha256 of query, NOT plaintext) to a
process-local in-memory ring buffer + a JSONL file at
$DUECARE_SEARCH_AUDIT (default /kaggle/working/duecare_search_audit.jsonl).
The audit records: timestamp, backend, query_sha256, result_count,
pii_blocked (bool). Plaintext queries are NOT recorded.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any, Optional

from duecare.research_tools.pii_filter import PIIFilter, PIIRejectionError
from duecare.research_tools.protocol import ResearchResult


_AUDIT_BUFFER: deque = deque(maxlen=500)
_AUDIT_FILE = os.environ.get(
    "DUECARE_SEARCH_AUDIT",
    "/kaggle/working/duecare_search_audit.jsonl")


def _audit(backend: str, query: str, result_count: int,
           pii_blocked: bool, error: str = "") -> None:
    """Append one audit entry. NEVER stores the plaintext query."""
    rec = {
        "ts":           time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend":      backend,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "query_len":    len(query),
        "result_count": result_count,
        "pii_blocked":  pii_blocked,
        "error":        error[:200] if error else "",
    }
    _AUDIT_BUFFER.append(rec)
    try:
        Path(_AUDIT_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass   # Audit best-effort; never crash the search itself


def get_recent_audit(limit: int = 50) -> list:
    return list(_AUDIT_BUFFER)[-limit:]


def _http_post_json(url: str, body: dict, headers: dict,
                    timeout: float = 15.0) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    h = {**headers, "Content-Type": "application/json",
         "Content-Length": str(len(data))}
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"ERR: {type(e).__name__}: {e}"


def _http_get_json(url: str, headers: dict,
                   timeout: float = 15.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"ERR: {type(e).__name__}: {e}"


# ===========================================================================
# 1. Tavily -- purpose-built for LLM agents, generous free tier
# ===========================================================================
class TavilySearchTool:
    """Tavily Search API. Free tier: 1000 searches/month, no card.

    Tavily's "answer" mode synthesizes results into a single response,
    which removes a Gemma-summarize roundtrip.
    """

    name: str = "tavily_search"
    description: str = (
        "Fast web search via Tavily (LLM-agent optimized). Returns "
        "ranked results + an optional pre-synthesized answer. PII-filtered.")

    def __init__(self, api_key: Optional[str] = None,
                 pii_filter: Optional[PIIFilter] = None,
                 max_results: int = 5,
                 search_depth: str = "basic",   # "basic" | "advanced"
                 include_answer: bool = True,
                 timeout: float = 15.0) -> None:
        # api_key is OPTIONAL at construction. The expected pattern is
        # to pass it per-call (BYOK from request body) via search(api_key=...).
        self.api_key = api_key or ""
        self.pii = pii_filter or PIIFilter()
        self.max_results = max_results
        self.search_depth = search_depth
        self.include_answer = include_answer
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.search(**kwargs)

    def search(self, query: str, max_results: Optional[int] = None,
               api_key: Optional[str] = None) -> ResearchResult:
        # Per-call api_key (BYOK) overrides the constructor default
        key = api_key or self.api_key
        max_results = max_results or self.max_results
        args = {"query": query, "max_results": max_results}
        if not key:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error="no Tavily API key (paste one in the BYOK panel)")
        try:
            self.pii.validate({"query": query})
        except PIIRejectionError as e:
            _audit(self.name, query, 0, pii_blocked=True, error=str(e))
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}",
                summary="(blocked locally; query contained PII)")

        body = {
            "api_key":        key,
            "query":          query,
            "search_depth":   self.search_depth,
            "max_results":    max_results,
            "include_answer": self.include_answer,
        }
        code, resp = _http_post_json(
            "https://api.tavily.com/search", body, headers={},
            timeout=self.timeout)
        if code != 200:
            _audit(self.name, query, 0, pii_blocked=False,
                   error=f"http {code}")
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"tavily http {code}: {resp[:200]!r}")
        try:
            payload = json.loads(resp)
        except json.JSONDecodeError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"tavily JSON parse: {e}")

        items = []
        for r in payload.get("results", []):
            items.append({
                "title":   r.get("title", "")[:240],
                "url":     r.get("url", ""),
                "snippet": (r.get("content") or "")[:480],
                "score":   r.get("score", 0.0),
                "source":  "tavily",
            })
        _audit(self.name, query, len(items), pii_blocked=False)
        summary = payload.get("answer", "") or \
                  f"Tavily: {len(items)} results for {query!r}"
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=items, summary=summary,
            raw=payload if isinstance(payload, dict) else {},
        )


# ===========================================================================
# 2. Brave Search -- generous free tier (2000/mo), needs CC for signup
# ===========================================================================
class BraveSearchTool:
    """Brave Search API. Free tier: 2000 queries/month."""

    name: str = "brave_search"
    description: str = (
        "Fast web search via Brave Search. Returns ranked results "
        "with title + URL + description. PII-filtered.")

    def __init__(self, api_key: Optional[str] = None,
                 pii_filter: Optional[PIIFilter] = None,
                 max_results: int = 8, timeout: float = 15.0) -> None:
        self.api_key = api_key or ""
        self.pii = pii_filter or PIIFilter()
        self.max_results = max_results
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.search(**kwargs)

    def search(self, query: str, max_results: Optional[int] = None,
               api_key: Optional[str] = None) -> ResearchResult:
        key = api_key or self.api_key
        max_results = max_results or self.max_results
        args = {"query": query, "max_results": max_results}
        if not key:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error="no Brave Search API key (paste one in the BYOK panel)")
        try:
            self.pii.validate({"query": query})
        except PIIRejectionError as e:
            _audit(self.name, query, 0, pii_blocked=True, error=str(e))
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}")

        encoded = urllib.parse.urlencode(
            {"q": query, "count": min(max_results, 20)})
        url = f"https://api.search.brave.com/res/v1/web/search?{encoded}"
        code, resp = _http_get_json(
            url, headers={"X-Subscription-Token": key,
                          "Accept": "application/json"},
            timeout=self.timeout)
        if code != 200:
            _audit(self.name, query, 0, pii_blocked=False,
                   error=f"http {code}")
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"brave http {code}: {resp[:200]!r}")
        try:
            payload = json.loads(resp)
        except json.JSONDecodeError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"brave JSON parse: {e}")

        items = []
        web = (payload.get("web") or {}).get("results") or []
        for r in web[:max_results]:
            items.append({
                "title":   (r.get("title") or "")[:240],
                "url":     r.get("url", ""),
                "snippet": (r.get("description") or "")[:480],
                "source":  "brave",
            })
        _audit(self.name, query, len(items), pii_blocked=False)
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=items,
            summary=f"Brave: {len(items)} results for {query!r}",
            raw=payload if isinstance(payload, dict) else {},
        )


# ===========================================================================
# 3. Serper -- Google search wrapper, paid (~$50/100k)
# ===========================================================================
class SerperSearchTool:
    """Serper API (https://serper.dev) — Google search wrapper."""

    name: str = "serper_search"
    description: str = (
        "Fast Google web search via Serper. Returns organic + knowledge "
        "panels + answer box. PII-filtered.")

    def __init__(self, api_key: Optional[str] = None,
                 pii_filter: Optional[PIIFilter] = None,
                 max_results: int = 8, timeout: float = 15.0) -> None:
        self.api_key = api_key or ""
        self.pii = pii_filter or PIIFilter()
        self.max_results = max_results
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.search(**kwargs)

    def search(self, query: str, max_results: Optional[int] = None,
               api_key: Optional[str] = None) -> ResearchResult:
        key = api_key or self.api_key
        max_results = max_results or self.max_results
        args = {"query": query, "max_results": max_results}
        if not key:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error="no Serper API key (paste one in the BYOK panel)")
        try:
            self.pii.validate({"query": query})
        except PIIRejectionError as e:
            _audit(self.name, query, 0, pii_blocked=True, error=str(e))
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}")

        body = {"q": query, "num": min(max_results, 20)}
        code, resp = _http_post_json(
            "https://google.serper.dev/search", body,
            headers={"X-API-KEY": key},
            timeout=self.timeout)
        if code != 200:
            _audit(self.name, query, 0, pii_blocked=False,
                   error=f"http {code}")
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"serper http {code}: {resp[:200]!r}")
        try:
            payload = json.loads(resp)
        except json.JSONDecodeError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"serper JSON parse: {e}")

        items = []
        for r in (payload.get("organic") or [])[:max_results]:
            items.append({
                "title":   (r.get("title") or "")[:240],
                "url":     r.get("link", ""),
                "snippet": (r.get("snippet") or "")[:480],
                "source":  "serper",
            })
        _audit(self.name, query, len(items), pii_blocked=False)
        # Serper sometimes provides an "answer box" -- surface it
        ab = payload.get("answerBox") or {}
        summary = (ab.get("answer") or ab.get("snippet")
                   or f"Serper: {len(items)} results for {query!r}")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=items, summary=summary,
            raw=payload if isinstance(payload, dict) else {},
        )


# ===========================================================================
# BYOK dispatcher -- per-call api_key from the request body
# ===========================================================================
class FastWebSearchTool:
    """BYOK web-search dispatcher. The user pastes API keys into the
    notebook UI's BYOK panel; those keys are stored in their browser
    localStorage and sent on each /api/chat request as a `byok_keys`
    dict. This class accepts that dict per call and routes to the
    appropriate backend.

    Routing precedence (first match wins per call):
        byok_keys["tavily"]      -> TavilySearchTool
        byok_keys["brave"]       -> BraveSearchTool
        byok_keys["serper"]      -> SerperSearchTool
        otherwise                -> BrowserTool (Playwright real browser
                                    via brave.com / ddg / ecosia, no key)
                                    OR WebSearchTool (DuckDuckGo HTML)
                                    if Playwright unavailable

    Construction takes NO keys -- they're per-call.
    """

    name: str = "fast_web_search"
    description: str = (
        "BYOK web-search dispatcher. Picks Tavily/Brave/Serper if the "
        "user has pasted that key, else falls back to BrowserTool "
        "(real headless browser, no key). PII-filtered.")

    def __init__(self, pii_filter: Optional[PIIFilter] = None,
                 max_results: int = 5,
                 prefer_browser_fallback: bool = True) -> None:
        self.pii = pii_filter or PIIFilter()
        self.max_results = max_results
        self.prefer_browser_fallback = prefer_browser_fallback

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.search(**kwargs)

    def search(self, query: str,
               byok_keys: Optional[dict] = None,
               max_results: Optional[int] = None,
               engine_hint: Optional[str] = None) -> ResearchResult:
        """Run a search. byok_keys is a dict like
        {'tavily': '<key>', 'brave': '<key>', 'serper': '<key>'} --
        any subset; passing nothing routes through the no-key fallbacks.

        engine_hint can force a specific engine for the no-key path:
        'brave' / 'ddg' / 'ecosia' (browser engines)."""
        max_results = max_results or self.max_results
        keys = byok_keys or {}

        # 1. BYOK API-backed (if user supplied a key)
        if keys.get("tavily"):
            return TavilySearchTool(
                pii_filter=self.pii, max_results=max_results
            ).search(query=query, api_key=keys["tavily"])
        if keys.get("brave"):
            return BraveSearchTool(
                pii_filter=self.pii, max_results=max_results
            ).search(query=query, api_key=keys["brave"])
        if keys.get("serper"):
            return SerperSearchTool(
                pii_filter=self.pii, max_results=max_results
            ).search(query=query, api_key=keys["serper"])

        # 2. No-key fallback: prefer the real browser (Playwright)
        if self.prefer_browser_fallback:
            try:
                from duecare.research_tools.browser_tool import BrowserTool
                bt = BrowserTool(pii_filter=self.pii)
                if bt.available:
                    engine = engine_hint or "brave"
                    if engine == "brave":
                        return bt.search_brave(query=query,
                                                max_results=max_results)
                    elif engine == "ddg":
                        return bt.search_ddg(query=query,
                                              max_results=max_results)
                    elif engine == "ecosia":
                        return bt.search_ecosia(query=query,
                                                 max_results=max_results)
            except ImportError:
                pass

        # 3. Last resort: DuckDuckGo HTML scrape (always available)
        from duecare.research_tools.web_tools import WebSearchTool
        return WebSearchTool(
            pii_filter=self.pii, max_results=max_results
        ).search(query=query, max_results=max_results)

    @staticmethod
    def describe_backend(byok_keys: Optional[dict] = None) -> dict:
        """Diagnostic: what backend would be picked for these keys?"""
        keys = byok_keys or {}
        if keys.get("tavily"):
            return {"backend": "tavily", "kind": "byok-api",
                    "note": "Tavily API (free 1k/mo, LLM-optimized)"}
        if keys.get("brave"):
            return {"backend": "brave_api", "kind": "byok-api",
                    "note": "Brave Search API (free 2k/mo)"}
        if keys.get("serper"):
            return {"backend": "serper", "kind": "byok-api",
                    "note": "Serper / Google (paid)"}
        # No keys -- check if browser is available
        try:
            from duecare.research_tools.browser_tool import BrowserTool
            if BrowserTool().available:
                return {"backend": "browser_brave", "kind": "no-key",
                        "note": ("real headless browser (Playwright) "
                                  "via brave.com -- no API key needed")}
        except ImportError:
            pass
        return {"backend": "duckduckgo_html", "kind": "no-key",
                "note": "DuckDuckGo HTML scrape (slowest fallback)"}
