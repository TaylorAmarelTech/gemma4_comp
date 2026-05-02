"""Open-source, no-key web research tools.

All three implement the ResearchTool protocol and pass through PIIFilter
before any network call.

  WebSearchTool  -- DuckDuckGo HTML scrape (no API key)
  WebFetchTool   -- httpx + trafilatura (clean Markdown from any URL)
  WikipediaTool  -- free structured Wikipedia REST API

Designed to be the backends an agentic loop calls when Gemma 4 decides
it needs web context. None of the three require a paid key, none lock
the project into a third-party SaaS.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Optional

from duecare.research_tools.pii_filter import PIIFilter, PIIRejectionError
from duecare.research_tools.protocol import ResearchResult


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
    "Duecare/0.1 (+https://github.com/TaylorAmarelTech/gemma4_comp)"
)


def _http_get(url: str, timeout: float = 20.0,
              headers: Optional[dict] = None) -> tuple[int, str]:
    """Stdlib HTTP GET. Returns (status_code, body_text)."""
    h = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError:
                text = body.decode("utf-8", errors="replace")
            return r.getcode(), text
    except Exception as e:
        return 0, f"ERR: {type(e).__name__}: {e}"


# ===========================================================================
# 1. WebSearchTool -- DuckDuckGo HTML scrape (no key)
# ===========================================================================
class WebSearchTool:
    """General web search via DuckDuckGo HTML endpoint.

    No API key required. DDG's HTML endpoint at
    https://html.duckduckgo.com/html/ returns raw HTML we parse for
    titles + URLs + snippets. Rate limits: empirically ~1 req/sec
    sustainable; treat 5+ req/sec as too aggressive.

    Always run query through PIIFilter before sending to DDG so we
    don't leak victim names, passport numbers, etc., to a third-party
    search engine.
    """

    name: str = "web_search"
    description: str = (
        "General web search via DuckDuckGo. Use for finding URLs to "
        "fetch with web_fetch. Returns title + URL + snippet for top "
        "results. PII-filtered.")

    def __init__(self, pii_filter: Optional[PIIFilter] = None,
                 max_results: int = 8, timeout: float = 20.0) -> None:
        self.pii = pii_filter or PIIFilter()
        self.max_results = max_results
        self.timeout = timeout

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.search(**kwargs)

    def search(self, query: str, max_results: Optional[int] = None,
               region: str = "wt-wt") -> ResearchResult:
        max_results = max_results or self.max_results
        args = {"query": query, "max_results": max_results, "region": region}
        try:
            self.pii.validate({"query": query})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}",
                summary="(blocked locally; query contained PII)")

        encoded = urllib.parse.urlencode({"q": query, "kl": region})
        url = f"https://html.duckduckgo.com/html/?{encoded}"
        code, body = _http_get(url, timeout=self.timeout,
                                headers={"Referer": "https://duckduckgo.com/"})
        if code != 200:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"DDG returned http {code}: {body[:200]!r}")

        # Parse DDG HTML results: each result is a <div class="result">
        # with <a class="result__a" href="..."> + <a class="result__snippet">
        results = []
        # Result block: between class="result" and class="result__check"
        # Use a forgiving regex pattern
        block_re = re.compile(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
            r'(.*?)'
            r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE)
        for m in block_re.finditer(body):
            href = m.group(1)
            title_html = m.group(2)
            snippet_html = m.group(4)
            # DDG wraps result URLs in /l/?uddg=<encoded>
            actual_url = href
            if "uddg=" in href:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                if "uddg" in qs:
                    actual_url = urllib.parse.unquote(qs["uddg"][0])
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
            # Normalize whitespace
            title = re.sub(r"\s+", " ", title)
            snippet = re.sub(r"\s+", " ", snippet)
            if not title or not actual_url.startswith(("http://", "https://")):
                continue
            results.append({
                "title":   title[:240],
                "url":     actual_url,
                "snippet": snippet[:480],
                "source":  "duckduckgo",
            })
            if len(results) >= max_results:
                break

        return ResearchResult(
            tool_name=self.name, query=args,
            success=True, items=results,
            summary=f"DuckDuckGo: {len(results)} result(s) for {query!r}",
            raw={"raw_html_bytes": len(body)},
        )


# ===========================================================================
# 2. WebFetchTool -- httpx + trafilatura (clean Markdown from any URL)
# ===========================================================================
class WebFetchTool:
    """Fetch a single URL and extract its main content as Markdown.

    Uses trafilatura when available (best content extraction),
    falls back to a basic stdlib HTML-to-text strip when not. No key.

    This is the workhorse: WebSearchTool finds URLs, WebFetchTool
    pulls the actual content for Gemma to read.
    """

    name: str = "web_fetch"
    description: str = (
        "Fetch a URL and extract its main content as Markdown. Use "
        "AFTER web_search has produced a URL worth reading. Returns "
        "title, extracted_text, and metadata. PII-filtered (URL only "
        "since it's outbound).")

    def __init__(self, pii_filter: Optional[PIIFilter] = None,
                 timeout: float = 30.0,
                 max_chars: int = 8000) -> None:
        self.pii = pii_filter or PIIFilter()
        self.timeout = timeout
        self.max_chars = max_chars

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.fetch(**kwargs)

    def fetch(self, url: str, max_chars: Optional[int] = None) -> ResearchResult:
        max_chars = max_chars or self.max_chars
        args = {"url": url, "max_chars": max_chars}
        # PII filter the URL itself (it shouldn't contain victim info)
        try:
            self.pii.validate({"url": url})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}")

        if not url.startswith(("http://", "https://")):
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"url must start with http(s); got {url!r}")

        code, body = _http_get(url, timeout=self.timeout)
        if code != 200:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"http {code}: {body[:200]!r}")

        # Try trafilatura first
        title = ""
        text = ""
        try:
            import trafilatura   # type: ignore
            extracted = trafilatura.extract(
                body, output_format="markdown",
                include_links=False, include_tables=True,
                favor_precision=True)
            if extracted:
                text = extracted
            metadata = trafilatura.extract_metadata(body)
            if metadata and metadata.title:
                title = metadata.title
        except Exception:
            pass

        # Fallback: basic HTML strip
        if not text:
            text = _basic_html_to_text(body)
        if not title:
            tm = re.search(r"<title[^>]*>(.*?)</title>", body,
                           re.IGNORECASE | re.DOTALL)
            if tm:
                title = re.sub(r"\s+", " ", tm.group(1)).strip()[:240]

        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars] + "\n\n[... TRUNCATED ...]"

        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{
                "url":       url,
                "title":     title,
                "text":      text,
                "char_count": len(text),
                "truncated": truncated,
            }],
            summary=f"fetched {url} -- {len(text)} chars"
                     + (" (truncated)" if truncated else ""),
            raw={"http_status": code, "raw_html_bytes": len(body)},
        )


def _basic_html_to_text(html: str) -> str:
    """Stdlib-only HTML to plain text (when trafilatura unavailable)."""
    # Strip script + style blocks
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html,
                  flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html,
                  flags=re.IGNORECASE | re.DOTALL)
    # Convert block-level closers to newlines
    html = re.sub(r"</(p|div|li|h[1-6]|tr|br)\s*[^>]*>", "\n", html,
                  flags=re.IGNORECASE)
    # Drop all other tags
    html = re.sub(r"<[^>]+>", " ", html)
    # HTML entities (a few common ones)
    html = html.replace("&amp;", "&").replace("&lt;", "<")
    html = html.replace("&gt;", ">").replace("&nbsp;", " ")
    html = html.replace("&#39;", "'").replace("&quot;", '"')
    # Collapse whitespace
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n\s*\n", "\n\n", html)
    return html.strip()


# ===========================================================================
# 3. WikipediaTool -- free Wikipedia REST API (no key)
# ===========================================================================
class WikipediaTool:
    """Wikipedia article lookup via the free REST API.

    Best for stable references: ILO conventions, statute names,
    historical court cases, treaty texts. Not great for current events
    (Wikipedia lag) -- use web_search + web_fetch for that.
    """

    name: str = "wikipedia"
    description: str = (
        "Look up a Wikipedia article by title. Best for stable legal/"
        "historical references (ILO conventions, statutes, treaties, "
        "named cases). Returns title, summary, full extract URL.")

    def __init__(self, pii_filter: Optional[PIIFilter] = None,
                 lang: str = "en", timeout: float = 15.0) -> None:
        self.pii = pii_filter or PIIFilter()
        self.lang = lang
        self.timeout = timeout

    def query(self, **kwargs: Any) -> ResearchResult:
        return self.lookup(**kwargs)

    def lookup(self, title: str, max_chars: int = 4000) -> ResearchResult:
        args = {"title": title, "max_chars": max_chars}
        try:
            self.pii.validate({"title": title})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}")

        # Wikipedia REST API: /page/summary/{title}
        encoded = urllib.parse.quote(title.replace(" ", "_"))
        api_url = (f"https://{self.lang}.wikipedia.org/api/rest_v1/"
                   f"page/summary/{encoded}")
        code, body = _http_get(api_url, timeout=self.timeout)
        if code == 404:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"wikipedia: no article titled {title!r}",
                summary="article not found")
        if code != 200:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"wikipedia http {code}: {body[:200]!r}")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"wikipedia returned invalid JSON: {body[:200]!r}")

        # Optionally fetch the longer extract too
        extract = data.get("extract", "")
        if len(extract) < 500:
            # Fetch a longer extract via the REST API extract endpoint
            extract_url = (f"https://{self.lang}.wikipedia.org/w/api.php"
                           f"?action=query&prop=extracts&explaintext=true"
                           f"&titles={encoded}&format=json")
            code2, body2 = _http_get(extract_url, timeout=self.timeout)
            if code2 == 200:
                try:
                    j = json.loads(body2)
                    pages = (j.get("query") or {}).get("pages") or {}
                    for _, page in pages.items():
                        if "extract" in page:
                            extract = page["extract"]
                            break
                except Exception:
                    pass
        if len(extract) > max_chars:
            extract = extract[:max_chars] + "\n\n[... TRUNCATED ...]"

        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{
                "title":       data.get("title", title),
                "description": data.get("description", ""),
                "extract":     extract,
                "url":         (data.get("content_urls", {})
                                .get("desktop", {}).get("page", "")),
                "lang":        self.lang,
            }],
            summary=f"Wikipedia: {data.get('title', title)} "
                     f"({len(extract)} chars)",
            raw=data,
        )
