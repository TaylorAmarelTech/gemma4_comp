"""Crawl politeness for acquisition at scale: per-host robots.txt ``Disallow``
honoring + per-host rate limiting.

Both are injectable (robots-text fetch, clock, sleep) so they're deterministic
and testable offline. Politeness is also self-interest: it's how a fleet that
crawls thousands of pages avoids being blocked. ``PoliteFetcher`` wraps any
``url -> FetchResult`` fetch and short-circuits disallowed URLs without a request.
"""
from __future__ import annotations

import time
import urllib.parse
from typing import Callable
from urllib.robotparser import RobotFileParser

from .monitor import FetchResult


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url or "").netloc.lower()


class RobotsCache:
    """Per-host robots.txt cache. ``fetch_robots(robots_url) -> str`` is injected
    (so it's testable and reuses our bot-grade fetch). Fails OPEN: a missing or
    unparseable robots.txt allows the URL (public pages, conservative crawler)."""

    def __init__(self, fetch_robots: Callable[[str], str], *, user_agent: str = "*") -> None:
        self._fetch = fetch_robots
        self._ua = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def _parser_for(self, url: str) -> RobotFileParser:
        parts = urllib.parse.urlparse(url)
        host = parts.netloc.lower()
        if host in self._cache:
            return self._cache[host]
        rp = RobotFileParser()
        try:
            txt = self._fetch(f"{parts.scheme or 'https'}://{host}/robots.txt")
            rp.parse((txt or "").splitlines())
        except Exception:  # noqa: BLE001 -- no robots -> allow all
            rp.parse([])
        self._cache[host] = rp
        return rp

    def allowed(self, url: str) -> bool:
        try:
            return self._parser_for(url).can_fetch(self._ua, url)
        except Exception:  # noqa: BLE001 -- fail open on parser quirks
            return True


class RateLimiter:
    """Per-host minimum interval between requests (token-bucket-lite). Clock and
    sleep are injectable for tests (no real waiting)."""

    def __init__(self, min_interval: float = 1.0, *,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.min_interval = max(0.0, min_interval)
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> float:
        """Sleep just long enough that this host isn't hit faster than
        ``min_interval``. Returns the slept seconds (0 if no wait)."""
        host = host_of(url)
        slept = 0.0
        last = self._last.get(host)
        now = self._clock()
        if last is not None and self.min_interval > 0:
            delta = now - last
            if delta < self.min_interval:
                slept = self.min_interval - delta
                self._sleep(slept)
        self._last[host] = self._clock()
        return slept


class PoliteFetcher:
    """Wrap a ``url -> FetchResult`` fetch with robots + rate limiting."""

    def __init__(self, inner_fetch: Callable[..., FetchResult], *,
                 robots: RobotsCache | None = None,
                 limiter: RateLimiter | None = None) -> None:
        self._inner = inner_fetch
        self._robots = robots
        self._limiter = limiter

    def __call__(self, url: str, *args, **kwargs) -> FetchResult:
        if self._robots is not None and not self._robots.allowed(url):
            return FetchResult(ok=False, status=0, error="robots-disallow")
        if self._limiter is not None:
            self._limiter.wait(url)
        return self._inner(url, *args, **kwargs)
