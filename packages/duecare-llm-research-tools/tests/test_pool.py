"""Tests for bounded concurrent fetching."""
from __future__ import annotations

import threading

from duecare.research_tools.monitor import FetchResult
from duecare.research_tools.pool import fetch_many


def test_fetch_many_returns_all_keyed_by_url():
    def fetch_one(u):
        return FetchResult(ok=True, status=200, text=f"body:{u}")
    res = fetch_many(["a", "b", "c"], fetch_one, max_workers=4)
    assert set(res) == {"a", "b", "c"}
    assert res["b"].text == "body:b"


def test_fetch_many_captures_exceptions():
    def fetch_one(u):
        if u == "bad":
            raise RuntimeError("boom")
        return FetchResult(ok=True, status=200, text=u)
    res = fetch_many(["ok", "bad"], fetch_one, max_workers=2)
    assert res["ok"].ok is True
    assert res["bad"].ok is False and "RuntimeError" in (res["bad"].error or "")


def test_fetch_many_dedups_urls():
    calls = []
    lock = threading.Lock()

    def fetch_one(u):
        with lock:
            calls.append(u)
        return FetchResult(ok=True, status=200, text=u)
    res = fetch_many(["x", "x", "y"], fetch_one, max_workers=2)
    assert set(res) == {"x", "y"}
    assert sorted(calls) == ["x", "y"]            # x fetched once


def test_fetch_many_is_actually_concurrent():
    # a 3-party barrier only clears if >= 3 fetches run at the same time;
    # a sequential implementation would dead-stall and raise BrokenBarrierError.
    barrier = threading.Barrier(3, timeout=5)

    def fetch_one(u):
        barrier.wait()
        return FetchResult(ok=True, status=200, text=u)
    res = fetch_many(["a", "b", "c"], fetch_one, max_workers=3)
    assert len(res) == 3 and all(r.ok for r in res.values())


def test_fetch_many_empty():
    assert fetch_many([], lambda u: FetchResult(ok=True)) == {}
