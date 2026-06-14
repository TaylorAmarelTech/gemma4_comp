#!/usr/bin/env python3
"""Wayback-Machine source archival -- provenance for every scrape.

Adopted from the operator's advanced DMW scraper kernel, which submits each
source to `web.archive.org/save/<url>` at scrape time. Archiving the source the
moment you read it gives two things the project cares about:

  * REAL-NOT-FAKED provenance: the archived snapshot is a citable, immutable copy
    of exactly what the registry showed when a record was captured -- so a
    number in the writeup is checkable even after the live page changes.
  * Robustness: government SPAs migrate/404 (e.g. apps.dmw.gov.ph/laapi/la is now
    gone -> master-api.dmw.gov.ph); a Wayback snapshot survives the migration.

Two operations, both over the FREE keyless Wayback APIs:
  * save(url)   -> submit a fresh snapshot (web.archive.org/save/<url>)
  * latest(url) -> the most recent existing snapshot (archive.org/wayback/available)

`fetch` is injectable, so URL building + response parsing are tested offline.
Propose-only: appends an archive log under reports/harvest/.

Usage:
    python scripts/archive_source.py --url https://dmw.gov.ph/inquiry/licensed-recruitment-agencies
    python scripts/archive_source.py --latest --url https://www.eaa.labour.gov.hk/en
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "duecare-archive/1.0 (+defensive anti-trafficking provenance)"
WAYBACK_SAVE = "https://web.archive.org/save/"
WAYBACK_AVAILABLE = "https://archive.org/wayback/available"
ARCHIVE_TODAY_SUBMIT = "https://archive.ph/submit/"


def _http(url: str, *, timeout: float = 45.0, want_headers: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(2_000_000).decode("utf-8", "replace")
        if want_headers:
            return body, dict(r.headers), r.geturl()
        return body


def save(url: str, *, fetch=None) -> dict:
    """Submit `url` for a fresh Wayback snapshot. Returns {url, snapshot_url, status}.
    The snapshot URL is read from the Content-Location header or the final URL."""
    fetch = fetch or (lambda u: _http(WAYBACK_SAVE + u, want_headers=True))
    try:
        res = fetch(url)
        body, headers, final = res if isinstance(res, tuple) else (res, {}, "")
        loc = headers.get("Content-Location") or headers.get("content-location") or ""
        snap = ("https://web.archive.org" + loc) if loc.startswith("/web/") else (final or "")
        return {"url": url, "snapshot_url": snap, "status": "saved" if snap else "submitted"}
    except urllib.error.HTTPError as exc:
        return {"url": url, "snapshot_url": "", "status": f"http_{exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "snapshot_url": "", "status": f"error_{type(exc).__name__}"}


def latest(url: str, *, fetch=None) -> dict:
    """Look up the most recent existing Wayback snapshot of `url`."""
    fetch = fetch or (lambda u: _http(WAYBACK_AVAILABLE + "?" + urllib.parse.urlencode({"url": u})))
    try:
        data = json.loads(fetch(url))
        snap = (data.get("archived_snapshots", {}) or {}).get("closest", {}) or {}
        return {"url": url, "snapshot_url": snap.get("url", ""),
                "timestamp": snap.get("timestamp", ""),
                "available": bool(snap.get("available"))}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "snapshot_url": "", "timestamp": "", "available": False,
                "status": f"error_{type(exc).__name__}"}


def archive_today(url: str, *, fetch=None) -> dict:
    """Submit `url` to archive.today (archive.ph) -- a second, independent archive
    that captures a full-page snapshot (survives even if Wayback is blocked)."""
    sub = ARCHIVE_TODAY_SUBMIT + "?" + urllib.parse.urlencode({"url": url})
    fetch = fetch or (lambda u: _http(u, want_headers=True, timeout=25.0))
    try:
        res = fetch(sub)
        body, headers, final = res if isinstance(res, tuple) else (res, {}, "")
        loc = headers.get("Location") or headers.get("Refresh") or ""
        snap = ""
        if "archive." in loc:
            snap = loc.split("url=")[-1] if "url=" in loc else loc
        elif final and "archive." in final and "/submit" not in final:
            snap = final
        else:
            m = re.search(r"https?://archive\.(?:ph|today|li|is|md)/\w+", body or "")
            snap = m.group(0) if m else ""
        return {"archiver": "archive_today", "url": url, "snapshot_url": snap,
                "status": "saved" if snap else "submitted"}
    except urllib.error.HTTPError as exc:
        return {"archiver": "archive_today", "url": url, "snapshot_url": "", "status": f"http_{exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"archiver": "archive_today", "url": url, "snapshot_url": "", "status": f"error_{type(exc).__name__}"}


def archive_one(url: str, archiver: str = "wayback", *, fetch=None) -> dict:
    """Archive one url with the named service. Returns a result dict (never raises)."""
    if archiver in ("wayback", "web.archive.org", "archive.org"):
        r = save(url, fetch=fetch)
        r["archiver"] = "wayback"
        return r
    if archiver in ("archive_today", "archive.today", "archive.ph"):
        return archive_today(url, fetch=fetch)
    return {"archiver": archiver, "url": url, "snapshot_url": "", "status": "unknown_archiver"}


class ArchivingFetcher:
    """Wrap a base fetch so EVERY distinct outbound URL is also submitted to web
    archives (Wayback + archive.today) -- a complete, citable provenance trail of
    everything the system touched. Robust by design:
      * dedupes per run (a URL is archived once, however many times it's fetched);
      * SWALLOWS archive failures -- archival never breaks the scrape;
      * DEFERS archiving to flush() by default, so live requests are not slowed
        (set inline=True to archive as you go).
    `archive_fn(url, archiver)` is injectable for tests."""

    def __init__(self, base_fetch, *, archivers=("wayback",), inline: bool = False,
                 archive_fn=None, log_path: Path | None = None):
        self._base = base_fetch
        self.archivers = tuple(archivers)
        self.inline = inline
        self._archive = archive_fn or archive_one
        self.log_path = log_path
        self.urls: list[str] = []
        self._seen: set[str] = set()
        self.results: list[dict] = []

    def __call__(self, url: str):
        content = self._base(url)
        if url not in self._seen:
            self._seen.add(url)
            self.urls.append(url)
            if self.inline:
                self._archive_url(url)
        return content

    def _archive_url(self, url: str) -> None:
        for arch in self.archivers:
            try:
                self.results.append(self._archive(url, arch))
            except Exception as exc:  # noqa: BLE001 -- never let archival break a scrape
                self.results.append({"archiver": arch, "url": url, "snapshot_url": "",
                                     "status": f"error_{type(exc).__name__}"})

    def flush(self, *, archived_at: str = "") -> list[dict]:
        """Archive any not-yet-archived URLs and append the propose-only log."""
        if not self.inline:
            for url in self.urls:
                self._archive_url(url)
        for r in self.results:
            r.setdefault("at", archived_at)
        log = Path(self.log_path) if self.log_path else (_ROOT / "reports" / "harvest" / "outbound_archive.jsonl")
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            for r in self.results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return self.results


def archive_sources(urls: list[str], *, fetch=None, log_path: Path | None = None,
                    archived_at: str = "") -> list[dict]:
    """Snapshot each url; append a propose-only archive log. fetch injectable."""
    results = []
    for u in urls:
        r = save(u, fetch=fetch)
        r["archived_at"] = archived_at
        results.append(r)
    log = log_path or (_ROOT / "reports" / "harvest" / "archive_log.jsonl")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return results


# the canonical sources worth archiving each harvest (provenance anchors)
DEFAULT_SOURCES = (
    "https://dmw.gov.ph/inquiry/licensed-recruitment-agencies",
    "https://dmw.gov.ph/advisory",
    "https://www.eaa.labour.gov.hk/en",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", action="append", default=[], help="url to archive (repeatable)")
    ap.add_argument("--defaults", action="store_true", help="archive the canonical registry sources")
    ap.add_argument("--latest", action="store_true", help="look up the latest snapshot instead of saving")
    ap.add_argument("--at", default="", help="archived_at stamp")
    args = ap.parse_args(argv)

    urls = list(args.url) + (list(DEFAULT_SOURCES) if args.defaults else [])
    if not urls:
        ap.error("provide --url or --defaults")

    if args.latest:
        for u in urls:
            r = latest(u)
            print(f"{u}\n  -> {r.get('snapshot_url') or '(no snapshot)'}  {r.get('timestamp','')}",
                  file=sys.stderr)
        return 0

    results = archive_sources(urls, archived_at=args.at)
    for r in results:
        print(f"[{r['status']:>10}] {r['url']}\n             {r['snapshot_url'] or '(pending)'}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
