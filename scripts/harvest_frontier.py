"""Harvest document URLs into the SQLite frontier queue -- built for millions.

Streams a deep, resumable, polite walk of the spider's sitemap/robots seeds
(sitemap_probe_queue + source_domain_frontier) into reports/acquisition/
frontier.db (table ``frontier``). Incremental + deduped + resumable (walked
sitemaps are recorded), so it can run for hours, be killed, and resume. The
frontier lives in its OWN db so it never contends with a running acquire on
corpus.db. The acquire step then drains ``frontier`` (status='pending').

Env knobs:
  HARVEST_DB           frontier sqlite (default reports/acquisition/frontier.db)
  HARVEST_MAX          max document URLs to discover (default 2_000_000)
  HARVEST_MAX_FETCHES  max sitemap fetches (default 50_000)
  HARVEST_DEPTH        sitemap-index recursion depth (default 8)
  HARVEST_MIN_INTERVAL per-host seconds between sitemap fetches (default 0.5)
  HARVEST_FLUSH        buffered URLs before a store flush (default 2000)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.monitor import default_fetch  # noqa: E402
from duecare.research_tools.politeness import PoliteFetcher, RateLimiter  # noqa: E402
from duecare.research_tools.sitemap import default_doc_filter, walk_sitemaps  # noqa: E402
from duecare.research_tools.store import AcquisitionStore  # noqa: E402

_BASE = ROOT / "configs/duecare/benchmarks/research_spider"
PROBE = Path(os.environ.get("HARVEST_PROBE", _BASE / "sitemap_probe_queue.jsonl"))
DOMAINS = Path(os.environ.get("HARVEST_DOMAINS", _BASE / "source_domain_frontier.jsonl"))
DB = Path(os.environ.get("HARVEST_DB", ROOT / "reports/acquisition/frontier.db"))
MAX = int(os.environ.get("HARVEST_MAX", "2000000"))
MAX_FETCHES = int(os.environ.get("HARVEST_MAX_FETCHES", "50000"))
DEPTH = int(os.environ.get("HARVEST_DEPTH", "8"))
MIN_INTERVAL = float(os.environ.get("HARVEST_MIN_INTERVAL", "0.5"))
FLUSH = int(os.environ.get("HARVEST_FLUSH", "2000"))


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def build_seeds() -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []
    for d in load_jsonl(PROBE):
        u = d.get("url")
        if u and u not in seen:
            seen.add(u)
            seeds.append(u)
    for d in load_jsonl(DOMAINS):
        for u in [d.get("robots_url"), *(d.get("sitemap_candidates") or [])]:
            if u and u not in seen:
                seen.add(u)
                seeds.append(u)
    return seeds


def main() -> None:
    _utf8()
    DB.parent.mkdir(parents=True, exist_ok=True)
    store = AcquisitionStore(DB)
    seeds = build_seeds()
    limiter = RateLimiter(MIN_INTERVAL) if MIN_INTERVAL > 0 else None
    fetch = PoliteFetcher(lambda url: default_fetch(url, timeout=20), limiter=limiter)
    t0 = time.time()
    start = store.frontier_count()
    print(f"[harvest] seeds={len(seeds)} db={DB} max={MAX} start_frontier={start}", flush=True)

    buf: list[dict] = []
    state = {"docs": 0, "added": 0, "sitemaps": 0}

    def flush() -> None:
        if buf:
            state["added"] += store.add_frontier_bulk(buf)
            store.commit()
            buf.clear()

    def on_doc(u: str) -> None:
        buf.append({"url": u, "host": urllib.parse.urlparse(u).netloc.lower(),
                    "source_tier": "harvested"})
        state["docs"] += 1
        if len(buf) >= FLUSH:
            flush()
            print(f"[harvest] docs_seen={state['docs']} new_frontier={state['added']} "
                  f"sitemaps={state['sitemaps']} elapsed={time.time() - t0:.0f}s", flush=True)

    def on_sitemap(u: str) -> None:
        store.mark_sitemap(u)
        state["sitemaps"] += 1
        if state["sitemaps"] % 500 == 0:
            store.commit()
            print(f"[harvest] sitemaps_walked={state['sitemaps']} "
                  f"new_frontier={state['added']} elapsed={time.time() - t0:.0f}s", flush=True)

    stats = walk_sitemaps(
        seeds, on_doc=on_doc, fetch=fetch,
        is_sitemap_seen=store.sitemap_seen, on_sitemap=on_sitemap,
        max_depth=DEPTH, max_docs=MAX, max_fetches=MAX_FETCHES,
        url_filter=default_doc_filter)
    flush()
    store.commit()
    total = store.frontier_count()
    print(f"[harvest] DONE walk={stats} new_added={state['added']} "
          f"frontier_total={total} pending={store.frontier_count(status='pending')} "
          f"elapsed={time.time() - t0:.0f}s", flush=True)
    store.close()


if __name__ == "__main__":
    main()
