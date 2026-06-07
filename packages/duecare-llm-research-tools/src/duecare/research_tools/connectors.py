"""Source connectors -- diverse, machine-accessible sources beyond gov sitemaps.

Each connector returns acquire-ready CANDIDATE dicts. Two shapes, both consumed by
the same ``acquire()`` pipeline:
  * url-only (``{id, url, title, ...}``)  -> acquire fetches + extracts (e.g. GDELT
    news discovery).
  * text-carrying (``{..., "text": body}``) -> acquire skips the fetch (e.g.
    ReliefWeb reports, which return the body directly).

The HTTP-JSON fetch is injected (defaults to the bot-grade ``monitor.default_fetch``),
so connectors are deterministic and testable offline. Start with the two no-key
REST APIs; the keyed ones (OpenAlex/CORE/CourtListener) follow the same shape.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.parse
from typing import Callable

from .monitor import default_fetch

# Per-source courtesy throttle. GDELT throttles repeat / datacenter callers (HTTP
# 429); its DOC API asks for a few seconds between calls. _throttle enforces a
# minimum interval per key across the process (thread-safe + slot-reserved), so
# paginated or scheduled pulls space themselves instead of getting rate-limited.
GDELT_MIN_INTERVAL = float(os.environ.get("GDELT_MIN_INTERVAL", "5.0"))
_LAST_CALL: dict[str, float] = {}
_THROTTLE_LOCK = threading.Lock()


def _throttle(key: str, min_interval: float) -> float:
    """Sleep so calls keyed by ``key`` are >= ``min_interval`` seconds apart.
    Returns the slept seconds."""
    if min_interval <= 0:
        return 0.0
    with _THROTTLE_LOCK:
        now = time.monotonic()
        last = _LAST_CALL.get(key, 0.0)
        wait = max(0.0, min_interval - (now - last))
        _LAST_CALL[key] = now + wait          # reserve the slot
    if wait > 0:
        time.sleep(wait)
    return wait


def _h(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:12].upper()


def default_fetch_json(url: str, *, timeout: float = 25.0, retries: int = 3,
                       backoff_base: float = 5.0) -> dict:
    """GET ``url`` and parse JSON (bot-grade fetch) with escalating backoff on
    rate-limit (429/503 -- GDELT throttles repeat callers). ``{}`` on any other
    failure, so a dead/changed endpoint degrades gracefully to zero candidates."""
    for attempt in range(retries + 1):
        res = default_fetch(url, timeout=timeout)
        if res.ok:
            try:
                return json.loads(res.text)
            except Exception:  # noqa: BLE001 -- non-JSON / truncated
                return {}
        if res.status in (429, 503) and attempt < retries:
            time.sleep(min(30.0, backoff_base * (attempt + 1)))   # 5s, 10s, 15s
            continue
        return {}
    return {}


# default trafficking/forced-labour query (provider-neutral)
DEFAULT_QUERY = ('"human trafficking" OR "forced labour" OR "forced labor" OR '
                 '"migrant worker" OR "debt bondage" OR "recruitment fee"')


def gdelt_candidates(query: str = DEFAULT_QUERY, *,
                     fetch_json: Callable[[str], dict] = default_fetch_json,
                     timespan_days: int = 30, max_records: int = 75,
                     signals: list[str] | None = None) -> list[dict]:
    """GDELT DOC 2.0 article search -> url+title candidates (acquire fetches them).
    No key. Best emerging-trend signal (global news, 65 languages)."""
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
           + urllib.parse.quote(query)
           + f"&mode=artlist&format=json&maxrecords={int(max_records)}"
           + f"&timespan={int(timespan_days)}d&sort=datedesc")
    _throttle("gdelt", GDELT_MIN_INTERVAL)   # courtesy spacing between GDELT calls
    data = fetch_json(url) or {}
    out: list[dict] = []
    seen: set[str] = set()
    for a in data.get("articles", []):
        u = a.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append({"id": "GDELT-" + _h(u), "url": u, "title": a.get("title"),
                    "source_tier": "news", "signals": list(signals or []),
                    "language": a.get("language"), "published": a.get("seendate")})
    return out


def reliefweb_documents(query: str = DEFAULT_QUERY, *,
                        fetch_json: Callable[[str], dict] = default_fetch_json,
                        limit: int = 50, signals: list[str] | None = None) -> list[dict]:
    """ReliefWeb reports -> url+title+TEXT documents (acquire ingests directly; the
    API returns the report body). No key. Aggregates 4,000+ NGO/UN sources."""
    params = [("appname", "duecare"), ("query[value]", query),
              ("query[operator]", "AND"), ("limit", str(int(limit))),
              ("sort[]", "date:desc"),
              ("fields[include][]", "title"), ("fields[include][]", "body"),
              ("fields[include][]", "url"), ("fields[include][]", "date.original"),
              ("fields[include][]", "primary_country.name")]
    url = "https://api.reliefweb.int/v1/reports?" + urllib.parse.urlencode(params)
    data = fetch_json(url) or {}
    out: list[dict] = []
    for d in data.get("data", []):
        f = d.get("fields", {}) or {}
        body = f.get("body") or ""
        if not body:
            continue
        u = f.get("url") or ""
        jur = (f.get("primary_country") or {}).get("name")
        out.append({"id": "RW-" + str(d.get("id") or _h(u)), "url": u,
                    "title": f.get("title"), "text": body,
                    "source_tier": "ngo_report", "signals": list(signals or []),
                    "jurisdictions": [jur] if jur else []})
    return out


CONNECTORS: dict[str, Callable[..., list[dict]]] = {
    "gdelt": gdelt_candidates,
    "reliefweb": reliefweb_documents,
}
