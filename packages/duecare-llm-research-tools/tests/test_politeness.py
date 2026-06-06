"""Tests for crawl politeness (robots + rate limiting), offline/deterministic."""
from __future__ import annotations

from duecare.research_tools.monitor import FetchResult
from duecare.research_tools.politeness import PoliteFetcher, RateLimiter, RobotsCache

ROBOTS = "User-agent: *\nDisallow: /private\nAllow: /\n"


def test_robots_disallow_and_allow():
    rc = RobotsCache(lambda u: ROBOTS)
    assert rc.allowed("https://e.org/public/doc") is True
    assert rc.allowed("https://e.org/private/secret") is False


def test_robots_fails_open_when_unavailable():
    def boom(u):
        raise RuntimeError("no robots")
    rc = RobotsCache(boom)
    assert rc.allowed("https://e.org/anything") is True   # missing robots -> allow


class _Clock:
    def __init__(self, times):
        self.times = list(times)
        self.i = 0

    def __call__(self):
        v = self.times[min(self.i, len(self.times) - 1)]
        self.i += 1
        return v


def test_rate_limiter_waits_per_host():
    slept = []
    # clock values consumed per wait() call (it calls clock twice)
    clock = _Clock([0.0, 0.0,    # call 1: now, set-last
                    0.3, 1.0])   # call 2: now=0.3 (delta 0.3 < 1.0 -> sleep 0.7), set-last
    rl = RateLimiter(1.0, clock=clock, sleep=slept.append)
    assert rl.wait("https://e.org/a") == 0.0            # first hit: no wait
    assert round(rl.wait("https://e.org/a"), 3) == 0.7  # second hit same host: waits remainder
    assert slept == [0.7]


def test_rate_limiter_independent_hosts():
    slept = []
    rl = RateLimiter(1.0, clock=_Clock([0.0, 0.0, 0.1, 0.1]), sleep=slept.append)
    rl.wait("https://a.org/x")
    rl.wait("https://b.org/y")        # different host -> no wait despite tiny gap
    assert slept == []


def test_polite_fetcher_blocks_disallowed_without_fetching():
    calls = []

    def inner(url, *a, **k):
        calls.append(url)
        return FetchResult(ok=True, status=200, text="ok")
    rc = RobotsCache(lambda u: ROBOTS)
    pf = PoliteFetcher(inner, robots=rc)
    blocked = pf("https://e.org/private/x")
    assert not blocked.ok and blocked.error == "robots-disallow" and calls == []
    ok = pf("https://e.org/public/x")
    assert ok.ok and calls == ["https://e.org/public/x"]
