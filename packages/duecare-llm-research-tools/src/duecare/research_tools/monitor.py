"""Public Information Research Monitor (internal name: *sentinel*) -- Component 5
of the Duecare north-star buildout (``docs/full_component_buildout_plan.md`` s.7).

Continuously track PUBLIC changes in laws, regulations, agency pages, complaint
forms, hotline/contact pages, scam patterns, and NGO guidance, then PROPOSE
update packs for human (curator) review.

Hard invariants (plan "Should not own" + the north-star data-boundary invariant):
  * NEVER mutates production knowledge packs / RAG / contacts. It only writes a
    state file, a ``proposed_updates.json`` queue, and a report; a human curator
    reviews and applies. ``test_monitor`` enforces this (no-auto-mutation test).
  * Only PUBLIC URLs are fetched -- no private case intake.
  * Fetched text is PII-scrubbed before it lands in a proposal summary.

Deterministic + testable: :func:`check_sources` takes an injected ``fetch``
callable and the prior state, so tests run fully offline with a mock fetch (no
network, no clock).

CLI::

    python -m duecare.research_tools.monitor check \
        --sources configs/duecare/research_monitor/sources.yaml \
        --state   reports/research_monitor/state.json \
        --out     reports/research_monitor/proposed_updates.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel

SourceKind = Literal["law", "agency", "complaint_form", "contact", "guidance", "scam_watch"]
ChangeKind = Literal["new", "changed", "unchanged", "unreachable"]


class MonitorSource(BaseModel):
    """One public page to watch."""
    id: str
    url: str
    kind: SourceKind
    label: str
    jurisdiction: str | None = None
    corridor: str | None = None


class FetchResult(BaseModel):
    ok: bool
    status: int = 0
    text: str = ""
    error: str | None = None


class ChangeFinding(BaseModel):
    source_id: str
    url: str
    kind: SourceKind
    change: ChangeKind
    prior_hash: str | None = None
    new_hash: str | None = None
    status: int = 0
    note: str = ""


class ProposedUpdate(BaseModel):
    """A curator-review item. NEVER auto-applied (``needs_review`` always True)."""
    source_id: str
    url: str
    kind: SourceKind
    change: ChangeKind
    summary: str
    prior_hash: str | None = None
    new_hash: str | None = None
    needs_review: bool = True


class MonitorReport(BaseModel):
    n_sources: int
    n_new: int
    n_changed: int
    n_unchanged: int
    n_unreachable: int
    findings: list[ChangeFinding]
    proposals: list[ProposedUpdate]


# --- content hashing (normalize so trivial chrome diffs don't false-flag) ----
_WS = re.compile(r"\s+")
# Per-request / per-build chrome stripped before hashing so a page is not
# reported "changed" when only volatile boilerplate differs. Each pattern
# targets a clearly-non-content shape (tokens, ids, asset hashes, machine
# timestamps); real prose/table content is left intact so genuine updates are
# still detected. Tuned 2026-06-13 to cut SPA / gov-portal false positives
# (CSP nonces, session ids, Nuxt/Next build hashes, Cloudflare ray ids, UUIDs,
# framework hydration markers, machine timestamps).
_VOLATILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # CSRF / nonce / auth tokens (quoted or bare) -- the biggest driver on
    # server-rendered form pages (e.g. a licensed-agency inquiry form).
    re.compile(r"(?:csrf[-_]?token|csrfmiddlewaretoken|authenticity_token|nonce|"
               r"_token|request[-_]?id|x[-_]request[-_]id)"
               r"\s*[=:]\s*[\"']?[A-Za-z0-9_\-./+=]{3,}[\"']?", re.I),
    # session ids
    re.compile(r"\b(?:jsessionid|phpsessid|asp\.net_sessionid|sessionid|session_id|sid)"
               r"=[A-Za-z0-9._\-]+", re.I),
    # cache-buster / asset-version query params (?v= ?_= ?ts= ...)
    re.compile(r"[?&](?:v|ver|version|_|t|ts|cb|cache|rev|hash|cachebuster)"
               r"=[A-Za-z0-9._\-]+", re.I),
    # SPA build/asset fingerprints (Nuxt /_nuxt, Next /_next, hashed bundles)
    re.compile(r"/_(?:nuxt|next)/[A-Za-z0-9_\-./]+", re.I),
    re.compile(r"\b[A-Za-z0-9_]+[.\-][0-9a-f]{8,}"
               r"\.(?:js|mjs|css|woff2?|png|jpe?g|svg|webp)\b", re.I),
    re.compile(r"buildid\s*[=:]\s*[\"']?[A-Za-z0-9\-]+[\"']?", re.I),
    # Cloudflare / WAF challenge + ray ids
    re.compile(r"(?:cf[-_]?ray|ray\s*id)\s*[=:]\s*[A-Za-z0-9\-]+", re.I),
    re.compile(r"cf_clearance=[A-Za-z0-9._\-]+", re.I),
    # UUIDs (build / trace / request ids)
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    # Vue scoped-css + framework hydration markers
    re.compile(r"data-v-[0-9a-f]{6,}", re.I),
    re.compile(r"data-(?:n-head|reactid|react-checksum|hydrate)\s*=\s*[\"'][^\"']*[\"']", re.I),
    # machine timestamps: ISO datetime (T or space separated), HTTP-date,
    # relative "x ago". A date-only "as of 2026-06-13" is intentionally NOT
    # stripped -- that one often signals a real data refresh.
    re.compile(r"\b\d{4}-\d{2}-\d{2}[ T][\d:]{4,}(?:\.\d+)?(?:[+-]\d{2}:?\d{2}|z)?", re.I),
    re.compile(r"\b(?:mon|tue|wed|thu|fri|sat|sun),?\s+\d{1,2}\s+"
               r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}"
               r"(?:[\d:\s]*(?:gmt|utc))?", re.I),
    re.compile(r"\b\d+\s+(?:sec|second|min|minute|hour|hr|day|week|month|year)s?\s+ago\b", re.I),
)


def normalize(text: str) -> str:
    out = text or ""
    for _pat in _VOLATILE_PATTERNS:
        out = _pat.sub("", out)
    return _WS.sub(" ", out).strip().lower()


def content_hash(text: str) -> str:
    """Stable sha256 over normalized content -- the change-detection signal."""
    return hashlib.sha256(normalize(text).encode("utf-8", "ignore")).hexdigest()


# --- PII scrub for proposal summaries (public pages can still name people) ---
_PII = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}")


def scrub(text: str) -> str:
    return _PII.sub("[redacted]", text or "")


def _summary(src: MonitorSource, change: ChangeKind, text: str) -> str:
    head = scrub(_WS.sub(" ", text or "").strip())[:240]
    return f"[{change}] {src.kind}:{src.label} ({src.url}) -- {head}"


def check_sources(
    sources: list[MonitorSource],
    fetch: Callable[[str], FetchResult],
    prior_state: dict[str, str],
) -> tuple[list[ChangeFinding], dict[str, str], list[ProposedUpdate]]:
    """Fetch each source, hash content, classify against ``prior_state``.

    PURE given ``fetch`` + ``prior_state`` (no network, no clock) so it is fully
    testable offline. Returns ``(findings, new_state, proposals)``. Proposals
    exclude ``unchanged`` and always carry ``needs_review=True``. Writes nothing.
    """
    findings: list[ChangeFinding] = []
    new_state = dict(prior_state)
    proposals: list[ProposedUpdate] = []
    for src in sources:
        res = fetch(src.url)
        prior = prior_state.get(src.id)
        if not res.ok:
            findings.append(ChangeFinding(
                source_id=src.id, url=src.url, kind=src.kind, change="unreachable",
                prior_hash=prior, status=res.status, note=res.error or f"HTTP {res.status}"))
            proposals.append(ProposedUpdate(
                source_id=src.id, url=src.url, kind=src.kind, change="unreachable",
                prior_hash=prior, summary=_summary(src, "unreachable", res.error or f"HTTP {res.status}")))
            continue
        h = content_hash(res.text)
        new_state[src.id] = h
        change: ChangeKind = "new" if prior is None else ("changed" if prior != h else "unchanged")
        findings.append(ChangeFinding(
            source_id=src.id, url=src.url, kind=src.kind, change=change,
            prior_hash=prior, new_hash=h, status=res.status))
        if change != "unchanged":
            proposals.append(ProposedUpdate(
                source_id=src.id, url=src.url, kind=src.kind, change=change,
                prior_hash=prior, new_hash=h, summary=_summary(src, change, res.text)))
    return findings, new_state, proposals


def build_report(findings: list[ChangeFinding], proposals: list[ProposedUpdate]) -> MonitorReport:
    c = Counter(f.change for f in findings)
    return MonitorReport(
        n_sources=len(findings), n_new=c["new"], n_changed=c["changed"],
        n_unchanged=c["unchanged"], n_unreachable=c["unreachable"],
        findings=findings, proposals=proposals)


# Optional bot-grade fetch backend. Government/NGO WAFs (Cloudflare/Akamai) drop a
# stdlib-urllib request by its TLS/JA3 fingerprint -- a UA string alone does NOT
# fix it (that is why the first run's 403s persisted). `curl_cffi` impersonates a
# real Chrome TLS fingerprint and defeats it (survey:
# reports/_scratch/build_operate_tooling_survey.md). OPTIONAL: stdlib urllib stays
# the zero-dep fallback so the monitor still runs without curl_cffi installed.
try:
    from curl_cffi import requests as _curl_requests  # type: ignore
    _HAVE_CURL = True
except Exception:  # noqa: BLE001
    _HAVE_CURL = False

_BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 DuecareResearchMonitor/0.1"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Charset detection avoids mojibake (smart quotes / dashes becoming U+FFFD) when a
# server mislabels or omits its charset. Optional -- stdlib utf-8/replace is the
# zero-dep fallback so the monitor still runs without charset_normalizer.
try:
    from charset_normalizer import from_bytes as _cn_from_bytes  # type: ignore
    _HAVE_CN = True
except Exception:  # noqa: BLE001
    _HAVE_CN = False


def _decode_bytes(content: bytes) -> str:
    """Decode HTTP body bytes to text, detecting the charset when possible."""
    if not content:
        return ""
    if _HAVE_CN:
        try:
            best = _cn_from_bytes(content).best()
            if best is not None:
                return str(best)
        except Exception:  # noqa: BLE001 -- fall back, never crash a fetch
            pass
    return content.decode("utf-8", "replace")


def _curl_fetch(url: str, timeout: float) -> FetchResult:
    """curl_cffi fetch with a real Chrome TLS fingerprint (defeats WAF 403s)."""
    try:
        r = _curl_requests.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        ok = 200 <= int(r.status_code) < 300
        return FetchResult(ok=ok, status=int(r.status_code),
                           text=_decode_bytes(r.content)[:2_000_000] if ok else "",
                           error=None if ok else f"HTTP {r.status_code}")
    except Exception as e:  # noqa: BLE001 -- transport failure: signal fallback
        return FetchResult(ok=False, status=0, error=f"{type(e).__name__}: {str(e)[:120]}")


def _urllib_fetch(url: str, timeout: float, _redirects: int = 4) -> FetchResult:
    """Stdlib fallback: browser UA + explicit redirect follow + one retry."""
    req = urllib.request.Request(url, headers=dict(_BROWSER_HEADERS))
    for attempt in (1, 2):  # one retry for slow government sites
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 -- public URLs only
                text = _decode_bytes(r.read(2_000_000))  # 2 MB cap, charset-detected
                return FetchResult(ok=True, status=getattr(r, "status", 200), text=text)
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location") if e.headers else None
            if e.code in (301, 302, 303, 307, 308) and loc and _redirects > 0:
                return _urllib_fetch(urllib.parse.urljoin(url, loc), timeout, _redirects - 1)
            return FetchResult(ok=False, status=int(e.code), error=f"HTTP {e.code}")
        except (TimeoutError, urllib.error.URLError) as e:
            if attempt == 1:
                continue  # retry once
            return FetchResult(ok=False, status=0, error=f"{type(e).__name__}: {str(e)[:120]}")
        except Exception as e:  # noqa: BLE001 -- report, never crash the run
            return FetchResult(ok=False, status=0, error=f"{type(e).__name__}: {str(e)[:120]}")
    return FetchResult(ok=False, status=0, error="retry exhausted")


def default_fetch(url: str, *, timeout: float = 25.0) -> FetchResult:
    """Fetch a PUBLIC url. Prefers curl_cffi (browser TLS fingerprint, defeats WAF
    403s) when installed; falls back to stdlib urllib on a transport failure. A
    real HTTP status from curl (403/404/200) is trusted as a true finding.
    Injected mock in tests; never raises."""
    if _HAVE_CURL:
        res = _curl_fetch(url, timeout)
        if res.ok or res.status:  # got a real HTTP status -> trust it
            return res
    return _urllib_fetch(url, timeout)


def load_sources(path: Path) -> list[MonitorSource]:
    """Load the source registry from YAML (preferred) or JSON."""
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
    except ModuleNotFoundError:
        data = json.loads(raw)
    items = data.get("sources", data) if isinstance(data, dict) else data
    return [MonitorSource(**d) for d in items]


def main(argv: list[str] | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(
        prog="research-monitor",
        description="Public Information Research Monitor -- propose-only freshness checker.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("check", help="Fetch sources, flag changed/404, emit review proposals.")
    pc.add_argument("--sources", type=Path, required=True)
    pc.add_argument("--state", type=Path, required=True)
    pc.add_argument("--out", type=Path, required=True)
    pc.add_argument("--offline", action="store_true",
                    help="skip network (smoke run: every source reported unreachable)")
    a = ap.parse_args(argv)

    if a.cmd == "check":
        sources = load_sources(a.sources)
        prior = json.loads(a.state.read_text(encoding="utf-8")) if a.state.exists() else {}
        fetch = ((lambda _u: FetchResult(ok=False, status=0, error="offline"))
                 if a.offline else default_fetch)
        findings, new_state, proposals = check_sources(sources, fetch, prior)
        report = build_report(findings, proposals)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps([p.model_dump() for p in proposals], indent=2), encoding="utf-8")
        a.state.parent.mkdir(parents=True, exist_ok=True)
        a.state.write_text(json.dumps(new_state, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[research-monitor] sources={report.n_sources} new={report.n_new} "
              f"changed={report.n_changed} unchanged={report.n_unchanged} "
              f"unreachable={report.n_unreachable} | {len(proposals)} proposal(s) -> {a.out} "
              f"(propose-only; no packs were modified)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
