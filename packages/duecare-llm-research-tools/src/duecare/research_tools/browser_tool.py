"""Real browser automation via Playwright.

This is the genuine "agentic browsing" surface: a real headless Chromium
controlled by Gemma 4 via tool calls. Lets us hit search engines like
brave.com / duckduckgo.com / ecosia.org through their actual web UIs
(no API keys required), navigate result links, extract main content,
take screenshots for multimodal Gemma input, and follow multi-page
research trails.

Primitives (each returns a ResearchResult):

  navigate(url)             open a URL in the headless browser
  search_brave(query)       brave.com/search?q=...  (no key needed)
  search_ddg(query)         duckduckgo.com/?q=...  (no key needed)
  search_ecosia(query)      ecosia.org/search?q=... (no key needed)
  click(selector)           click an element + return the new page state
  fill(selector, value)     fill a form field
  extract_text(selector?)   extract text content (whole page or scoped)
  get_links()               return all <a href> on the current page
  screenshot()              return a base64 PNG of the viewport

The BrowserSession is process-singleton -- one Chromium instance shared
across all tool calls in the same notebook session. Closing it requires
calling shutdown() explicitly.

PII filter is applied to URLs + form values before any navigation.
"""
from __future__ import annotations

import base64
import os
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

from duecare.research_tools.pii_filter import PIIFilter, PIIRejectionError
from duecare.research_tools.protocol import ResearchResult


@dataclass
class _BrowserState:
    playwright: Any = None
    browser: Any = None
    context: Any = None
    page: Any = None
    last_url: str = ""


_STATE = _BrowserState()


def _ensure_browser(timeout: float = 60.0) -> bool:
    """Lazy-launch Playwright + Chromium. Returns True on success."""
    if _STATE.page is not None:
        return True
    try:
        from playwright.sync_api import sync_playwright   # type: ignore
    except ImportError:
        return False
    try:
        _STATE.playwright = sync_playwright().start()
        _STATE.browser = _STATE.playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        _STATE.context = _STATE.browser.new_context(
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        _STATE.page = _STATE.context.new_page()
        _STATE.page.set_default_timeout(int(timeout * 1000))
        return True
    except Exception:
        return False


def shutdown() -> None:
    """Close the shared Playwright browser. Idempotent."""
    try:
        if _STATE.context:
            _STATE.context.close()
        if _STATE.browser:
            _STATE.browser.close()
        if _STATE.playwright:
            _STATE.playwright.stop()
    except Exception:
        pass
    _STATE.playwright = None
    _STATE.browser = None
    _STATE.context = None
    _STATE.page = None
    _STATE.last_url = ""


# ===========================================================================
# BrowserTool -- exposes browser primitives as ResearchTool methods
# ===========================================================================
class BrowserTool:
    """Headless Chromium controlled by Gemma 4. No API keys required for
    the major search engines (brave / ddg / ecosia) -- they're hit
    through their actual web UIs."""

    name: str = "browser"
    description: str = (
        "Real browser automation via headless Playwright + Chromium. "
        "Use to search the web through search engines' actual UIs "
        "(brave.com, duckduckgo.com, ecosia.org), navigate result "
        "pages, click links, extract content. No API keys required.")

    def __init__(self, pii_filter: Optional[PIIFilter] = None,
                 page_timeout: float = 30.0,
                 wait_after_nav: float = 1.5) -> None:
        self.pii = pii_filter or PIIFilter()
        self.page_timeout = page_timeout
        self.wait_after_nav = wait_after_nav

    @property
    def available(self) -> bool:
        try:
            import playwright   # noqa: F401
            return True
        except ImportError:
            return False

    def query(self, **kwargs: Any) -> ResearchResult:
        """Generic dispatch. kwargs must include `endpoint` matching one
        of the public methods (navigate, search_brave, etc.)."""
        endpoint = kwargs.pop("endpoint", "navigate")
        method = getattr(self, endpoint, None)
        if method is None or endpoint.startswith("_"):
            return ResearchResult(
                tool_name=self.name, query=kwargs, success=False,
                error=f"unknown endpoint: {endpoint}")
        return method(**kwargs)

    # -- bring-up checks -----------------------------------------------------
    def _bringup(self, args: dict) -> Optional[ResearchResult]:
        if not self.available:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=("playwright not installed. Install with: "
                        "pip install playwright && playwright install chromium"))
        if not _ensure_browser(timeout=self.page_timeout):
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=("playwright launch failed -- "
                        "ensure Chromium is installed: "
                        "playwright install chromium --with-deps"))
        return None

    # -- navigation ----------------------------------------------------------
    def navigate(self, url: str) -> ResearchResult:
        args = {"url": url}
        try:
            self.pii.validate({"url": url})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}")
        if not url.startswith(("http://", "https://")):
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error="URL must start with http(s)")
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            _STATE.page.goto(url, wait_until="domcontentloaded",
                             timeout=int(self.page_timeout * 1000))
            time.sleep(self.wait_after_nav)
            _STATE.last_url = _STATE.page.url
            title = _STATE.page.title() or ""
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"navigate failed: {type(e).__name__}: {e}")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{"url": _STATE.last_url, "title": title}],
            summary=f"navigated to {_STATE.last_url} -- {title[:80]}",
        )

    # -- search engines via their web UIs (no API keys) ---------------------
    def search_brave(self, query: str, max_results: int = 8) -> ResearchResult:
        return self._search_via_engine(
            engine="brave", query=query, max_results=max_results,
            url_template="https://search.brave.com/search?q={q}",
            result_link_selector="a[href][data-handler='url']",
            title_selector=".snippet-title, .title",
            snippet_selector=".snippet-content, .snippet-description")

    def search_ddg(self, query: str, max_results: int = 8) -> ResearchResult:
        return self._search_via_engine(
            engine="ddg", query=query, max_results=max_results,
            url_template="https://duckduckgo.com/html/?q={q}",
            result_link_selector="a.result__a",
            title_selector="a.result__a",
            snippet_selector="a.result__snippet")

    def search_ecosia(self, query: str, max_results: int = 8) -> ResearchResult:
        return self._search_via_engine(
            engine="ecosia", query=query, max_results=max_results,
            url_template="https://www.ecosia.org/search?q={q}",
            result_link_selector=".result-title a, .result__title a",
            title_selector=".result-title, .result__title",
            snippet_selector=".result-snippet, .result__snippet")

    def _search_via_engine(self, engine: str, query: str, max_results: int,
                            url_template: str, result_link_selector: str,
                            title_selector: str,
                            snippet_selector: str) -> ResearchResult:
        args = {"engine": engine, "query": query, "max_results": max_results}
        try:
            self.pii.validate({"query": query})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected: {e}",
                summary="(blocked locally; query contained PII)")
        bringup = self._bringup(args)
        if bringup:
            return bringup
        url = url_template.format(q=urllib.parse.quote(query))
        try:
            _STATE.page.goto(url, wait_until="domcontentloaded",
                             timeout=int(self.page_timeout * 1000))
            time.sleep(self.wait_after_nav)
            _STATE.last_url = _STATE.page.url
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"{engine} navigation failed: "
                       f"{type(e).__name__}: {e}")
        # Best-effort extraction. Each engine's selectors vary; we try
        # the primary selector and fall back to a generic anchor scan.
        items = []
        try:
            anchors = _STATE.page.query_selector_all(result_link_selector)
            for a in anchors[:max_results * 2]:
                try:
                    href = a.get_attribute("href") or ""
                    title = (a.inner_text() or "").strip()
                except Exception:
                    continue
                if not href.startswith(("http://", "https://")):
                    continue
                items.append({
                    "title":   title[:240],
                    "url":     href,
                    "snippet": "",
                    "source":  engine,
                })
                if len(items) >= max_results:
                    break
        except Exception:
            pass
        # Generic fallback if specific selectors returned nothing
        if not items:
            try:
                anchors = _STATE.page.query_selector_all("a[href]")
                seen = set()
                for a in anchors:
                    try:
                        href = a.get_attribute("href") or ""
                        title = (a.inner_text() or "").strip()
                    except Exception:
                        continue
                    if not href.startswith(("http://", "https://")):
                        continue
                    if any(x in href for x in (engine, "duckduckgo.com",
                                                "brave.com", "ecosia.org")):
                        continue   # skip same-engine links (nav, ads)
                    if href in seen or not title:
                        continue
                    seen.add(href)
                    items.append({"title": title[:240], "url": href,
                                  "snippet": "", "source": engine})
                    if len(items) >= max_results:
                        break
            except Exception:
                pass
        return ResearchResult(
            tool_name=self.name, query=args, success=True, items=items,
            summary=f"{engine} (browser): {len(items)} result(s) for {query!r}")

    # -- interact with the current page -------------------------------------
    def click(self, selector: str,
              wait_after: float = 1.5) -> ResearchResult:
        args = {"selector": selector}
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            _STATE.page.click(selector,
                              timeout=int(self.page_timeout * 1000))
            time.sleep(wait_after)
            _STATE.last_url = _STATE.page.url
            title = _STATE.page.title() or ""
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"click failed: {type(e).__name__}: {e}")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{"url": _STATE.last_url, "title": title}],
            summary=f"clicked {selector!r}; now at {_STATE.last_url}")

    def fill(self, selector: str, value: str) -> ResearchResult:
        args = {"selector": selector, "value_len": len(value)}
        try:
            self.pii.validate({"value": value})
        except PIIRejectionError as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"pii_rejected (form value): {e}")
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            _STATE.page.fill(selector, value,
                              timeout=int(self.page_timeout * 1000))
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"fill failed: {type(e).__name__}: {e}")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            summary=f"filled {selector!r}")

    def extract_text(self, selector: Optional[str] = None,
                      max_chars: int = 8000) -> ResearchResult:
        args = {"selector": selector, "max_chars": max_chars}
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            if selector:
                el = _STATE.page.query_selector(selector)
                text = el.inner_text() if el else ""
            else:
                text = _STATE.page.inner_text("body")
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"extract failed: {type(e).__name__}: {e}")
        text = re.sub(r"\n\s*\n", "\n\n", text or "")
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars] + "\n\n[... TRUNCATED ...]"
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{"url": _STATE.last_url, "text": text,
                    "char_count": len(text), "truncated": truncated}],
            summary=f"extracted {len(text)} chars from {selector or 'body'}")

    def get_links(self, max_links: int = 50) -> ResearchResult:
        args = {"max_links": max_links}
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            anchors = _STATE.page.query_selector_all("a[href]")
            links = []
            seen = set()
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    text = (a.inner_text() or "").strip()
                except Exception:
                    continue
                if not href.startswith(("http://", "https://")):
                    continue
                if href in seen:
                    continue
                seen.add(href)
                links.append({"url": href, "text": text[:160]})
                if len(links) >= max_links:
                    break
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"get_links failed: {type(e).__name__}: {e}")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=links,
            summary=f"{len(links)} link(s) on {_STATE.last_url}")

    def screenshot(self) -> ResearchResult:
        """Returns the current page as a base64-encoded PNG."""
        args: dict = {}
        bringup = self._bringup(args)
        if bringup:
            return bringup
        try:
            png = _STATE.page.screenshot(full_page=False, type="png")
        except Exception as e:
            return ResearchResult(
                tool_name=self.name, query=args, success=False,
                error=f"screenshot failed: {type(e).__name__}: {e}")
        b64 = base64.b64encode(png).decode("ascii")
        return ResearchResult(
            tool_name=self.name, query=args, success=True,
            items=[{"url": _STATE.last_url,
                    "image_data_uri": f"data:image/png;base64,{b64}",
                    "byte_count": len(png)}],
            summary=f"screenshot of {_STATE.last_url} ({len(png)} bytes)")
