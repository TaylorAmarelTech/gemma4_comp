#!/usr/bin/env python3
"""Hong Kong EAA (Employment Agencies Administration) collector with robust waits.

The HK licensed-EA register (eaa.labour.gov.hk) is a heavily GATED SPA: the path
is search.html -> disclaimer-search.html -> statement-search.html -> search form
-> result.html (rows injected by JS only after the full gated flow). Direct
deep-links 404. This is exactly the case the operator's production Selenium
kernel solves with WebDriverWait/expected_conditions -- so this collector ports
that pattern to Playwright as a small ROBUST-WAITS engine: every navigation and
click waits for its target and retries on transient failure.

Two routes:
  * LIVE  -- drive the gated flow with robust waits + paginate result.html,
            parsing rows with the tested browser_scrape table parser. Current
            data, but SPA-fragile; best-effort.
  * PDF   -- the Labour Department's full list PDF
            (labour.gov.hk/eng/public/eaee/ea_list.pdf) is text-extractable
            (~5,000 agencies, "<NAME>  <District, Region>"). Reliable bulk
            baseline (a dated snapshot), no SPA.

Design: the browser PAGE is injectable, so the robust-waits retry logic, the
gated-flow orchestration, the PDF parser, and the entity mapping are tested
offline with a fake page + fixtures -- no browser, no network. Propose-only.

Usage:
    python scripts/hk_eaa_collector.py --pdf-url      # download + parse the list PDF
    python scripts/hk_eaa_collector.py --pdf path/to/ea_list.pdf
    python scripts/hk_eaa_collector.py --live --max-pages 50
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "duecare-recruitment-screen/1.0 (+defensive anti-trafficking review; respects robots.txt)"

EAA_BASE = "https://www.eaa.labour.gov.hk/en"
EAA_PDF = "https://www.labour.gov.hk/eng/public/eaee/ea_list.pdf"


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_hkeaa", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- robust-waits engine (port of WebDriverWait/expected_conditions) -------

class RobustWaits:
    """Wrap a browser page so every navigate/click WAITS for its target and
    RETRIES on transient failure (the production-Selenium robustness pattern).
    The page is injectable; `sleep` is injectable so tests run instantly."""

    def __init__(self, page, *, timeout_ms: int = 15000, retries: int = 2, sleep=None):
        self.page = page
        self.timeout = timeout_ms
        self.retries = retries
        self._sleep = sleep or time.sleep
        self.log: list[tuple] = []

    def goto(self, url: str) -> bool:
        for attempt in range(self.retries + 1):
            try:
                self.page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                self.log.append(("goto", url, "ok"))
                return True
            except Exception as exc:  # noqa: BLE001
                self.log.append(("goto", url, f"retry{attempt}:{type(exc).__name__}"))
                self._sleep(min(1.0 * (attempt + 1), 5.0))
        self.log.append(("goto", url, "failed"))
        return False

    def wait_for(self, selector: str, *, timeout_ms: int | None = None) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms or self.timeout)
            return True
        except Exception:  # noqa: BLE001
            return False

    def wait_click(self, targets, *, timeout_ms: int = 4000) -> bool:
        """Wait for + click the first of several candidate selectors; retry."""
        cands = [targets] if isinstance(targets, str) else list(targets)
        for attempt in range(self.retries + 1):
            for sel in cands:
                try:
                    self.page.wait_for_selector(sel, timeout=timeout_ms)
                    self.page.click(sel, timeout=timeout_ms)
                    self.log.append(("click", sel))
                    return True
                except Exception:  # noqa: BLE001
                    continue
            self._sleep(min(0.5 * (attempt + 1), 3.0))
        self.log.append(("click", "none", tuple(cands)))
        return False

    def content(self) -> str:
        try:
            return self.page.content()
        except Exception:  # noqa: BLE001
            return ""


# accept-button candidates seen on the HK gov disclaimer/statement gates
_ACCEPT = ("text=Accept", "text=I have read and agree", "text=I have read", "text=Agree",
           "text=I Agree", "text=Confirm", "text=Proceed", "text=Continue",
           "button:has-text('Accept')", "a:has-text('Accept')", "input[value*='Accept']")
_ROW_SELECTORS = "table tr, .result-item, .record, tbody tr, [class*=result] li"


def collect_hk_eaa_live(page, *, max_pages: int = 50, sleep=None) -> dict:
    """Drive the gated EAA flow with robust waits, paginate result.html, parse
    rows with the tested table parser. Returns {records, pages, log}."""
    scrape = _sibling("scrape_agency_sources")  # parse_html_table lives here
    rw = RobustWaits(page, sleep=sleep)
    rw.goto(f"{EAA_BASE}/search.html")
    # click through the disclaimer + statement gates (idempotent; best-effort)
    for _ in range(3):
        if not rw.wait_click(_ACCEPT, timeout_ms=3500):
            break
    rw.wait_click(("text=Search", "button:has-text('Search')", "input[type=submit]"), timeout_ms=3500)

    records, pages = [], 0
    seen_keys = set()
    for n in range(1, max_pages + 1):
        if not rw.goto(f"{EAA_BASE}/result.html?page-no={n}&row-per-page=20&sort-by=EN_NAME_ASC"):
            break
        rw.wait_for(_ROW_SELECTORS, timeout_ms=8000)
        page_recs = scrape.parse_html_table(rw.content())
        fresh = [r for r in page_recs if r.get("name") and r["name"] not in seen_keys]
        if not fresh:
            break  # no new rows -> reached the end
        for r in fresh:
            seen_keys.add(r["name"])
        records.extend(fresh)
        pages = n
    return {"records": records, "pages": pages, "log": rw.log}


# ---- PDF baseline parser (reliable bulk) ----------------------------------

_PDF_LINE = re.compile(r"^(.*\S)\s{2,}([A-Za-z'.\-/() ]+,\s*(?:Hong Kong|Kowloon|New Territories))\s*$")


def parse_pdf_list(text: str) -> list[dict]:
    """Parse the Labour Dept licensed-EA list PDF text into agency records.
    Each entry is '<AGENCY NAME>  <District, Region>'; all are licensed."""
    recs = []
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s or s.isdigit():  # blank / page-number lines
            continue
        m = _PDF_LINE.match(line)
        if not m:
            continue
        name, loc = m.group(1).strip(), m.group(2).strip()
        if len(name) < 2 or name.lower().startswith(("list of", "disclaimer", "the following")):
            continue
        recs.append({"name": name, "address": loc, "status": "valid", "jurisdiction": "HK",
                     "source": "HK Labour Dept licensed-EA list (PDF)", "source_tier": "official"})
    return recs


def _download_pdf(url: str = EAA_PDF) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(8_000_000)


def pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("pypdf required for the PDF route: pip install pypdf") from exc
    import io
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((pg.extract_text() or "") for pg in reader.pages)


# ---- entity mapping --------------------------------------------------------

def records_to_entities(records: list[dict]) -> list[dict]:
    """Map EAA agency records to recruitment_agency entity dicts (HK)."""
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        out.append({
            "entity_type": "recruitment_agency", "name": name, "jurisdiction": "HK",
            "status": r.get("status", "valid"),
            "address": r.get("address", "") or r.get("region", ""),
            "license_no": r.get("license_no", ""), "phones": r.get("phones", ""),
            "source": r.get("source", "HK EAA register"),
            "source_tier": r.get("source_tier", "official"),
        })
    return out


# ---- CLI -------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf-url", action="store_true", help="download + parse the Labour Dept list PDF")
    ap.add_argument("--pdf", help="parse a local ea_list.pdf")
    ap.add_argument("--live", action="store_true", help="drive the gated SPA with robust waits")
    ap.add_argument("--max-pages", type=int, default=50)
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "hk_eaa.jsonl"))
    args = ap.parse_args(argv)

    records, note = [], ""
    if args.pdf or args.pdf_url:
        try:
            data = Path(args.pdf).read_bytes() if args.pdf else _download_pdf()
            records = parse_pdf_list(pdf_text(data))
            note = f"PDF: {len(records)} agencies"
        except Exception as exc:  # noqa: BLE001
            print(f"PDF route failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    elif args.live:
        try:
            from playwright.sync_api import sync_playwright
            bs = _sibling("browser_scrape")
            with sync_playwright() as pw:
                browser = bs._launch_browser(pw)
                page = browser.new_context(user_agent=USER_AGENT).new_page()
                res = collect_hk_eaa_live(page, max_pages=args.max_pages)
                browser.close()
            records = res["records"]
            note = f"LIVE: {len(records)} agencies over {res['pages']} page(s)"
            print("robust-waits log tail:", res["log"][-6:], file=sys.stderr)
        except ImportError:
            print("Playwright required for --live. Use --pdf-url for the reliable baseline.", file=sys.stderr)
            return 2
    else:
        ap.error("provide --pdf-url, --pdf, or --live")

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    print(f"{note} -> {len(entities)} HK entities -> {out}", file=sys.stderr)
    for e in entities[:5]:
        print(f"  - {e['name'][:48]} | {e['address'][:30]}", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
