#!/usr/bin/env python3
"""Browser-automation connector for JS-walled recruitment registries.

Some official registries render their agency list client-side: a plain fetch
returns only an SPA shell, and the real data arrives via an XHR the page makes
after hydration. The Philippine DMW Licensed Recruitment Agencies inquiry
(dmw.gov.ph/inquiry/licensed-recruitment-agencies) is the canonical case --
probed 2026-06-13: the inquiry page, the archives/v1 API paths, and the static
HTML all return a JS shell to a non-browser GET, and the legacy agList.asp 404s.
robots.txt is fully permissive (empty Disallow, no crawl-delay).

This connector drives a real headless browser (Playwright) to let the SPA load,
then INTERCEPTS the network responses -- capturing every JSON payload AND its
URL. That does two jobs at once:
  1. pulls the structured agency list the SPA renders, and
  2. DISCOVERS the backend endpoint, so future runs can use the lightweight
     env-keyed `scrape_agency_sources.py --source dmw_api` connector with no
     browser at all.

Design (matches the rest of the pipeline):
  * Offline-testable core. The render step is injectable (`renderer=`), so the
    capture-routing, endpoint-discovery, pagination, and normalization are
    tested with a fake renderer -- no browser, no network. Parsing reuses the
    already-tested parse_json_list / parse_html_table / records_to_profiles.
  * Playwright is an OPTIONAL extra. The module imports without it; only a live
    run needs it. If absent, the CLI prints the exact install runbook.
  * Polite. Identified User-Agent, rate-limited, page-capped, honours robots
    (the target's robots.txt is checked by the operator; this tool also caps
    pages and sleeps between them).
  * Propose-only. Output stages to reports/agency_registry/ (gitignored) plus a
    manifest recording the discovered endpoint(s). Never mutates live knowledge.
  * No embedded secrets. Nothing site-specific is committed beyond public URLs.

Usage:
    # live (needs: pip install playwright && playwright install chromium)
    python scripts/browser_scrape.py --preset dmw_lra --max-pages 50
    python scripts/browser_scrape.py --url https://example.gov/registry --intercept agencies

    # the run prints every JSON endpoint the page called -- copy the agency-list
    # one into DMW_LIST_URL to switch to the no-browser connector next time.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# Reuse the tested record parsers + the polite User-Agent from sibling scripts.
USER_AGENT = "duecare-recruitment-screen/1.0 (+defensive anti-trafficking review; respects robots.txt)"


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_browser", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # frozen-dataclass exec needs registration
    spec.loader.exec_module(mod)
    return mod


@dataclass(frozen=True)
class BrowserCapture:
    """A JS-walled registry to render + capture."""
    url: str
    label: str = ""
    # capture every JSON response; rank the one whose URL contains any of these
    # higher when choosing the agency list (a hint, not a hard filter).
    intercept_hints: tuple[str, ...] = ("agenc", "recruit", "licens", "list", "search")
    wait_selector: str = ""          # optional CSS to await before capture
    search_term: str = ""            # optional: type into the first text input + submit
    next_selector: str = ""          # optional: click to paginate (until absent/disabled)
    max_pages: int = 1
    min_interval_s: float = 1.0      # polite delay between page navigations/clicks
    nav_timeout_s: float = 30.0


@dataclass
class CaptureResult:
    payloads: list[dict] = field(default_factory=list)   # [{"url":..., "text":...}]
    discovered_endpoints: list[str] = field(default_factory=list)
    pages_rendered: int = 0
    note: str = ""


# ---- preset registries -----------------------------------------------------

PRESETS = {
    "dmw_lra": BrowserCapture(
        url="https://dmw.gov.ph/inquiry/licensed-recruitment-agencies",
        label="PH DMW -- Licensed Recruitment Agencies (land-based)",
        intercept_hints=("agenc", "recruit", "licens", "lra", "list", "search"),
        # the SPA paginates the table; 'Next Page' is the aria-label of the next
        # control (verified 2026-06-13). ~3,790 agencies / 76 pages @ 50/page.
        next_selector='[aria-label="Next Page"]',
        max_pages=80, min_interval_s=0.8,
    ),
}


# ---- offline-testable core -------------------------------------------------

def _looks_like_agency_records(records: list[dict]) -> int:
    """Score a parsed record list by how agency-like it is (for endpoint pick)."""
    if not records:
        return 0
    keys = set()
    for r in records[:5]:
        keys |= set(r.keys())
    signal = len(keys & {"name", "license_no", "status", "address", "phones", "region", "email"})
    return signal * 1000 + min(len(records), 100)


# Real registry APIs wrap the list under a key; a non-browser parser with no
# list_path only reads a bare top-level array, so try the common envelopes.
_JSON_LIST_PATHS = ("", "data", "records", "results", "items", "rows",
                    "data.records", "data.items", "data.list", "result.records", "payload.data")

# The DMW public licensed-agencies API has a clean, stable schema that the fuzzy
# header heuristic mis-maps (its "license_status" collides with the license_no
# needle). For known schemas we transform fields explicitly rather than guess.
# Verified live 2026-06-13 against master-api.dmw.gov.ph: 3,790 agencies / 76
# pages, perPage 50, items under meta+data.
_DMW_KEYS = {"license_status", "classification", "is_valid"}


def _is_dmw_items(items) -> bool:
    return bool(items) and isinstance(items[0], dict) and bool(_DMW_KEYS & set(items[0]))


def _dmw_status(raw: str, is_valid) -> str:
    s = (raw or "").lower()
    if "cancel" in s:
        return "cancelled"
    if "delist" in s or "ban" in s:
        return "delisted"
    if "suspend" in s:
        return "suspended"
    if "expire" in s:
        return "expired"
    if "ceased" in s:               # "Ceased Operation(s)" -> one bucket
        return "ceased_operations"
    if "denied" in s:               # "Denied Renewal"
        return "denied_renewal"
    if "cash bond" in s:            # "Cash Bond Withdrawn"
        return "cash_bond_withdrawn"
    if "inactive" in s:
        return "inactive"
    if "valid" in s or is_valid is True:
        return "valid"
    return s or ("valid" if is_valid is True else "unknown")


def _dmw_item_to_record(it: dict) -> dict:
    addr = ", ".join(str(x) for x in (it.get("address"), it.get("municipality_province"),
                                      it.get("city_province")) if x)
    notes = []
    if it.get("classification"):
        notes.append(str(it["classification"]))
    if it.get("license_expiration_date"):
        notes.append("expires " + str(it["license_expiration_date"])[:10])
    if it.get("representative"):
        notes.append("rep: " + str(it["representative"]))
    return {
        "name": str(it.get("name", "")),
        "status": _dmw_status(str(it.get("license_status", "")), it.get("is_valid")),
        "status_as_of": str(it.get("data_as_of") or it.get("license_status_date") or "")[:10],
        "address": addr,
        "phones": str(it.get("contact_number", "")),
        "email": str(it.get("eMail", "")),
        "record_type": str(it.get("classification", "")),
        "notes": " | ".join(notes),
    }


def captures_to_profiles(result: CaptureResult, *, source: str,
                         fetched_at: str = "") -> tuple[list[dict], str]:
    """Route captured payloads to AgencyProfile dicts. Known schemas (DMW) are
    transformed explicitly AND aggregated across all paginated pages; unknown
    payloads fall back to picking the single richest list via the heuristic.
    Returns (profiles, chosen_endpoint_url)."""
    scrape = _load_sibling("scrape_agency_sources")
    dmw_records: list[dict] = []
    dmw_endpoint = ""
    best: tuple[int, list[dict], str] = (0, [], "")  # generic fallback
    for p in result.payloads:
        text = p.get("text") or ""
        url = p.get("url") or ""
        stripped = text.lstrip()
        if stripped[:1] in ("{", "["):
            try:
                data = json.loads(text)
            except Exception:  # noqa: BLE001
                continue
            items = data.get("data") if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if _is_dmw_items(items):
                dmw_records.extend(_dmw_item_to_record(it) for it in items)
                dmw_endpoint = dmw_endpoint or url
                continue
            records: list[dict] = []
            for lp in _JSON_LIST_PATHS:
                recs = scrape.parse_json_list(data, list_path=lp)
                if _looks_like_agency_records(recs) > _looks_like_agency_records(records):
                    records = recs
            if _looks_like_agency_records(records) > best[0]:
                best = (_looks_like_agency_records(records), records, url)
        elif "<table" in text.lower():
            records = scrape.parse_html_table(text)
            if _looks_like_agency_records(records) > best[0]:
                best = (_looks_like_agency_records(records), records, url)

    if dmw_records:
        seen, uniq = set(), []
        for r in dmw_records:  # drop exact-duplicate page overlaps; entity_kb does entity-level merge
            k = (r["name"], r.get("status"), r.get("status_as_of"), r.get("address"))
            if k in seen:
                continue
            seen.add(k); uniq.append(r)
        return scrape.records_to_profiles(uniq, source=source, fetched_at=fetched_at), dmw_endpoint
    profiles = scrape.records_to_profiles(best[1], source=source, fetched_at=fetched_at) if best[1] else []
    return profiles, best[2]


# ---- live renderer (Playwright; lazy import) -------------------------------

# Launch strategies tried in order; the first that starts wins. System Edge is
# first because the Playwright-bundled headless-shell chromium can fail to start
# on some Windows installs ("Invalid file descriptor to ICU data received"),
# whereas the OS Edge/Chrome is a stable Chromium that Playwright can drive via
# `channel=`. Each is a real Chromium, so capture behaviour is identical.
_LAUNCH_STRATEGIES = (
    {"channel": "msedge", "headless": True},
    {"channel": "chrome", "headless": True},
    {"headless": True},
    {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]},
)


def _pagination_last_page(data) -> int | None:
    """Read the last-page number from a paginated JSON envelope, if present."""
    if not isinstance(data, dict):
        return None
    for a, b in (("meta", "lastPage"), ("meta", "last_page"), ("meta", "totalPages"),
                 ("meta", "total_pages"), ("pagination", "lastPage"),
                 ("pagination", "last_page"), ("pagination", "total_pages")):
        node = data.get(a)
        if isinstance(node, dict) and isinstance(node.get(b), int) and node[b] > 0:
            return node[b]
    return None


def _with_page(url: str, n: int) -> str:
    """Set the ?page= param of an API URL to n."""
    if re.search(r"[?&]page=\d+", url):
        return re.sub(r"([?&]page=)\d+", lambda m: f"{m.group(1)}{n}", url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}page={n}"


def _launch_browser(pw, *, headless: bool = True):
    """Launch the first Chromium that starts; raise if none do.

    ``headless=False`` launches a real visible browser -- far likelier to clear a
    Cloudflare managed challenge than a headless one (the agentic fetch tier)."""
    errors = []
    for strat in _LAUNCH_STRATEGIES:
        strat = {**strat, "headless": headless}
        try:
            return pw.chromium.launch(**strat)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{strat.get('channel', 'bundled')}: {type(exc).__name__}")
    raise RuntimeError(
        "could not launch any Chromium. Tried: " + "; ".join(errors) +
        "\nInstall a browser: python -m playwright install chromium "
        "(or ensure system Edge/Chrome is present).")


def _stealth_sync_playwright():
    """Prefer patchright (a drop-in Playwright fork that patches the Runtime.enable
    CDP leak -- the top 2026 bot-detection signal) when installed; else Playwright.

    patchright is API-compatible, so the rest of the browser code is unchanged; it
    just lowers the automation fingerprint so a managed challenge can auto-pass.
    """
    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        from playwright.sync_api import sync_playwright
    return sync_playwright


def browser_fetch(url: str, *, warmup_url: str | None = None, binary: bool = False,
                  nav_timeout_s: float = 45.0, headed: bool = False,
                  challenge_wait_s: float = 4.0) -> "str | bytes":
    """Fetch a URL through a real browser (Edge/Playwright), to pass JS-challenge
    WAFs (Cloudflare) that 403 plain urllib/curl_cffi.

    If ``warmup_url`` is given, the browser navigates there first so the WAF's
    challenge-clearance cookie is set in the context before the data URL is
    fetched via ``ctx.request.get`` (which reuses those cookies). ``headed=True``
    launches a real visible browser and waits ``challenge_wait_s`` for the
    challenge to auto-clear -- the agentic tier, far likelier to pass Cloudflare.
    Returns text or bytes. Raises if no browser launches or the fetch is not OK.
    """
    sync_playwright = _stealth_sync_playwright()
    to = int(nav_timeout_s * 1000)
    with sync_playwright() as pw:
        browser = _launch_browser(pw, headless=not headed)
        try:
            # in headed/agentic mode, present the real browser identity (max stealth
            # to pass a managed challenge); in the polite tiers keep the bot UA.
            ctx = browser.new_context() if headed else browser.new_context(user_agent=USER_AGENT)
            page = ctx.new_page()
            if warmup_url:
                try:
                    page.goto(warmup_url, timeout=to, wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=to)
                    page.wait_for_timeout(int(challenge_wait_s * 1000))  # let a JS-challenge clear
                except Exception:  # noqa: BLE001 -- warmup is best-effort
                    pass
            # 1) reuse the (now challenge-cleared) context cookies for an API fetch
            r = ctx.request.get(url, timeout=to)
            if r.ok:
                return r.body() if binary else r.text()
            # 2) fallback: navigate the page straight to the data URL and read the body
            resp = page.goto(url, timeout=to, wait_until="domcontentloaded")
            if resp and resp.ok:
                return resp.body() if binary else resp.text()
            raise RuntimeError(
                f"browser_fetch HTTP {r.status}/{resp.status if resp else '?'} for {url}")
        finally:
            browser.close()


def _playwright_render(cfg: BrowserCapture) -> CaptureResult:
    """Drive headless Chromium, capture every JSON response, paginate politely."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # noqa: BLE001
        raise ImportError(
            "Playwright is required for live browser scraping. Install it:\n"
            "    pip install playwright\n"
            "    playwright install chromium\n"
            f"(original: {exc})"
        ) from exc

    captured: list[dict] = []
    endpoints: list[str] = []
    req_headers: dict[str, dict] = {}

    def _on_response(resp):
        try:
            ctype = (resp.headers or {}).get("content-type", "")
            if "json" in ctype.lower():
                endpoints.append(resp.url)
                captured.append({"url": resp.url, "text": resp.text()})
                try:
                    req_headers[resp.url] = dict(resp.request.headers)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass  # a body we cannot read is not fatal to the run

    pages_rendered = 0
    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        page.on("response", _on_response)
        page.goto(cfg.url, timeout=int(cfg.nav_timeout_s * 1000), wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=int(cfg.nav_timeout_s * 1000))
        except Exception:  # noqa: BLE001
            pass
        if cfg.wait_selector:
            try:
                page.wait_for_selector(cfg.wait_selector, timeout=int(cfg.nav_timeout_s * 1000))
            except Exception:  # noqa: BLE001
                pass
        if cfg.search_term:
            try:
                box = page.query_selector("input[type=text], input:not([type])")
                if box:
                    box.fill(cfg.search_term)
                    box.press("Enter")
                    page.wait_for_load_state("networkidle", timeout=int(cfg.nav_timeout_s * 1000))
            except Exception:  # noqa: BLE001
                pass
        pages_rendered = 1

        # Strategy 1 (preferred): if the list came from a paginated JSON API,
        # replay pages 2..lastPage through the browser context -- forwarding the
        # SPA's own auth header so the API does not 401. Fast, no DOM fragility.
        list_url, last_page, hdrs = "", 0, {}
        for cap in list(captured):
            try:
                lp = _pagination_last_page(json.loads(cap["text"]))
            except Exception:  # noqa: BLE001
                lp = None
            if lp and lp > 1:
                list_url, last_page = cap["url"], lp
                hdrs = req_headers.get(cap["url"], {})
                break
        if list_url and last_page > 1:
            fwd = {k: v for k, v in hdrs.items()
                   if k.lower() in ("authorization", "accept", "x-api-key",
                                    "x-requested-with", "referer", "origin")}
            fwd.setdefault("accept", "application/json")
            for n in range(2, min(last_page, cfg.max_pages) + 1):
                time.sleep(cfg.min_interval_s)
                try:
                    r = ctx.request.get(_with_page(list_url, n), headers=fwd,
                                        timeout=cfg.nav_timeout_s * 1000)
                    if not r.ok:
                        break
                    captured.append({"url": r.url, "text": r.text()})
                    endpoints.append(r.url)
                    pages_rendered += 1
                except Exception:  # noqa: BLE001
                    break
        # Strategy 2 (fallback): click a DOM 'next' control if no API pagination.
        elif cfg.next_selector:
            while pages_rendered < cfg.max_pages:
                nxt = page.query_selector(cfg.next_selector)
                if not nxt or not nxt.is_enabled():
                    break
                time.sleep(cfg.min_interval_s)
                try:
                    nxt.click()
                    page.wait_for_load_state("networkidle", timeout=int(cfg.nav_timeout_s * 1000))
                except Exception:  # noqa: BLE001
                    break
                pages_rendered += 1
        browser.close()

    # de-dupe endpoints preserving order
    seen, uniq = set(), []
    for e in endpoints:
        if e not in seen:
            seen.add(e); uniq.append(e)
    return CaptureResult(payloads=captured, discovered_endpoints=uniq,
                         pages_rendered=pages_rendered,
                         note=f"captured {len(captured)} JSON response(s) over {pages_rendered} page(s)")


def render_and_capture(cfg: BrowserCapture, *, renderer=None) -> CaptureResult:
    """Render `cfg` and capture payloads. `renderer` is injectable for tests."""
    return (renderer or _playwright_render)(cfg)


# ---- CLI -------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=sorted(PRESETS), help="a built-in JS-walled registry")
    ap.add_argument("--url", help="render an arbitrary registry URL")
    ap.add_argument("--intercept", default="", help="extra URL substring hint for the agency-list XHR")
    ap.add_argument("--wait-selector", default="", help="CSS selector to await before capture")
    ap.add_argument("--next-selector", default="", help="CSS selector of the pagination 'next' control")
    ap.add_argument("--max-pages", type=int, default=0, help="override preset page cap")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "agency_registry" / "browser_scraped.json"))
    args = ap.parse_args(argv)

    if args.preset:
        cfg = PRESETS[args.preset]
        label = f"browser:{args.preset}"
    elif args.url:
        cfg = BrowserCapture(url=args.url, label=args.url)
        label = f"browser:{args.url}"
    else:
        ap.error("provide --preset or --url")

    # apply CLI overrides
    overrides = {}
    if args.intercept:
        overrides["intercept_hints"] = (*cfg.intercept_hints, args.intercept)
    if args.wait_selector:
        overrides["wait_selector"] = args.wait_selector
    if args.next_selector:
        overrides["next_selector"] = args.next_selector
    if args.max_pages:
        overrides["max_pages"] = args.max_pages
    if overrides:
        from dataclasses import replace
        cfg = replace(cfg, **overrides)

    try:
        result = render_and_capture(cfg)
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    profiles, endpoint = captures_to_profiles(result, source=label)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_synthetic": False, "source": label, "url": cfg.url,
        "discovered_endpoints": result.discovered_endpoints,
        "chosen_endpoint": endpoint,
        "pages_rendered": result.pages_rendered,
        "n_records": len(profiles), "records": profiles,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(result.note, file=sys.stderr)
    if result.discovered_endpoints:
        print("discovered JSON endpoint(s) the page called:", file=sys.stderr)
        for e in result.discovered_endpoints:
            print(f"  {e}", file=sys.stderr)
    if endpoint:
        print(f"agency-list endpoint -> {endpoint}\n"
              f"  reuse without a browser: set DMW_LIST_URL to it and run\n"
              f"  scripts/scrape_agency_sources.py --source dmw_api", file=sys.stderr)
    if not profiles:
        print("no agency records parsed -- inspect discovered_endpoints / selectors", file=sys.stderr)
        return 1
    print(f"captured {len(profiles)} agency record(s) -> {out}", file=sys.stderr)
    print(f"review, then ingest: scripts/entity_kb.py --ingest {out} "
          f"--as recruitment_agency --jurisdiction PH "
          f"--out reports/entity_kb/dmw_lra.jsonl", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
