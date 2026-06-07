"""Bounded concurrent fetching for the acquisition pipeline -- the Scrapy-style
throughput win our sequential fetch lacked.

Fetches many URLs in parallel with a thread pool. Per-host politeness is
preserved because the injected ``fetch_one`` wraps a THREAD-SAFE RateLimiter +
robots check (politeness.py): different hosts run concurrently while each host
stays rate-limited. Fetching is I/O-bound, so threads (not processes) are the
right tool -- no asyncio rewrite, no torch, no extra dependency.

One bad URL never sinks the batch (exceptions become failed FetchResults). The
result is keyed by URL so the caller (acquire) reads it as a cache and keeps its
serial extract/chunk/dedup/store path unchanged.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .monitor import FetchResult


def fetch_many(
    urls: list[str],
    fetch_one: Callable[[str], FetchResult],
    *,
    max_workers: int = 8,
) -> dict[str, FetchResult]:
    """Fetch ``urls`` concurrently via ``fetch_one(url) -> FetchResult``. Returns
    ``{url: FetchResult}`` (deduped, exceptions captured as failed results)."""
    ordered = list(dict.fromkeys(u for u in urls if u))   # dedup, preserve order
    out: dict[str, FetchResult] = {}
    if not ordered:
        return out
    workers = max(1, min(max_workers, len(ordered)))

    def _safe(u: str) -> tuple[str, FetchResult]:
        try:
            return u, fetch_one(u)
        except Exception as e:  # noqa: BLE001 -- never let one URL sink the batch
            return u, FetchResult(ok=False, status=0,
                                  error=f"{type(e).__name__}: {str(e)[:120]}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for u, res in ex.map(_safe, ordered):
            out[u] = res
    return out
