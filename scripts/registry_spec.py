#!/usr/bin/env python3
"""Config-driven registry resolver -- turn a YAML spec into entity records.

This is the engine that lets the long tail of catalogued data-endpoints be
onboarded as CONFIG instead of code. A spec names a URL, a format, and a
``fields`` map; the engine fetches, dispatches to the right ``registry_parsers``
parser, and stamps canonical entity dicts (the same shape the hand-written
resolvers emit, so they flow straight into entity_kb + entity_screen).

Spec shape (configs/duecare/research_monitor/registry_specs.yaml):

    - id: bd_oep_cfg
      url: https://www.oep.gov.bd/agencies
      format: html_table            # json | csv | xlsx | pdf
      entity_type: recruitment_agency
      jurisdiction: BD
      fields: {name: "Agent Name", license_no: "License No", status: "License Status"}
      row_filter: {field: license_no, pattern: "^RL"}   # optional
      default_status: licensed                          # optional
      note_fields: [license_validity]                   # optional -> appended to notes
      source: "BD OEP/BMET licensed recruiting-agency register"

The three hand-written resolvers bd_oep / bd_mra / cn_mara are reproduced as
specs in the shipped YAML, which is exactly how the engine is validated: config
must reproduce their live counts (2,834 / 904 / 167). The fetcher is injectable
so parsing is tested offline.

Usage:
    python scripts/registry_spec.py --list
    python scripts/registry_spec.py --id bd_oep_cfg
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import re
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

_ROOT = Path(__file__).resolve().parents[1]
_SPECS = _ROOT / "configs" / "duecare" / "research_monitor" / "registry_specs.yaml"
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

_TEXT_FORMATS = {"html_table", "csv", "json"}
_BYTE_FORMATS = {"xlsx", "pdf", "pdf_table"}


def _rp():
    spec = importlib.util.spec_from_file_location(
        "dc_registry_parsers", str(_ROOT / "scripts" / "registry_parsers.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_specs(path: Path = _SPECS) -> dict[str, dict]:
    """id -> spec for every entry in the registry-specs YAML ({} if absent)."""
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return {}
    if not Path(path).exists():
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {str(s["id"]): s for s in (data.get("specs") or []) if s.get("id")}


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages)


def parse_spec(spec: dict, content: Any) -> list[dict]:
    """Dispatch a spec + already-fetched content to the right parser -> records.

    ``content`` is text for html_table/csv/json, bytes for xlsx, bytes-or-text
    for pdf, or an already-parsed object for json (tests pass content directly).
    """
    rp = _rp()
    fmt = spec.get("format")
    fields = spec.get("fields", {})
    kw = {"row_filter": spec.get("row_filter"), "name_field": spec.get("name_field", "name")}
    if fmt == "html_table":
        return rp.parse_html_table(content, fields, **kw)
    if fmt == "csv":
        return rp.parse_csv(content, fields, **kw)
    if fmt == "xlsx":
        return rp.parse_xlsx(content, fields, **kw)
    if fmt == "json":
        data = json.loads(content) if isinstance(content, (str, bytes)) else content
        return rp.parse_json(data, fields, list_path=spec.get("list_path"), **kw)
    if fmt == "pdf":
        text = _pdf_text(content) if isinstance(content, (bytes, bytearray)) else content
        return rp.parse_pdf_lines(text, spec["row_regex"], spec["groups"])
    if fmt == "pdf_table":
        return rp.parse_pdf_table(content, fields, flavor=spec.get("pdf_flavor", "lattice"),
                                  pages=spec.get("pdf_pages", "all"), **kw)
    raise ValueError(f"unknown format: {fmt!r}")


def to_entities(records: list[dict], spec: dict) -> list[dict]:
    """Stamp canonical entity dicts from parsed records + spec metadata."""
    et = spec.get("entity_type", "company")
    jz = spec.get("jurisdiction", "")
    src = spec.get("source") or spec.get("id", "registry")
    default_status = spec.get("default_status", "")
    note_fields = spec.get("note_fields", [])
    out = []
    for r in records:
        name = str(r.get("name", "")).strip()
        if not name:
            continue
        notes = []
        if r.get("license_no"):
            notes.append(f"License {r['license_no']}")
        for nf in note_fields:
            if r.get(nf):
                notes.append(f"{nf}: {r[nf]}")
        out.append({
            "entity_type": et, "name": name, "jurisdiction": jz,
            "status": str(r.get("status", "")).strip() or default_status,
            "address": str(r.get("address", "")).strip(),
            "license_no": str(r.get("license_no", "")).strip(),
            "source": src, "source_tier": "official",
            "notes": "; ".join(notes),
        })
    return out


_DATE_RES = (
    (re.compile(r"(20\d{2})[-_/.](\d{1,2})[-_/.](\d{1,2})"), (1, 2, 3)),   # YYYY-MM-DD
    (re.compile(r"(\d{1,2})[-_/.](\d{1,2})[-_/.](20\d{2})"), (3, 2, 1)),   # DD.MM.YYYY
    (re.compile(r"(20\d{2})(\d{2})(\d{2})"), (1, 2, 3)),                   # YYYYMMDD
)


_QUARTER_RE = re.compile(r"(20\d{2})[qQ]([1-4])")


def _date_key(text: str) -> tuple[int, int, int]:
    """Best-effort (y, m, d) date pulled from a string, for picking the latest file.

    Recognises full dates (YYYY-MM-DD / DD.MM.YYYY / YYYYMMDD) and, failing that, a
    ``YYYYqN`` quarter token (mapped to ~the quarter's last month) so quarterly
    datasets like CA TFWP sort newest-first.
    """
    for rx, (yi, mi, di) in _DATE_RES:
        m = rx.search(text)
        if m:
            return (int(m.group(yi)), int(m.group(mi)), int(m.group(di)))
    mq = _QUARTER_RE.search(text)
    if mq:
        return (int(mq.group(1)), int(mq.group(2)) * 3, 0)
    return (0, 0, 0)


def discover_url(disc: dict, *, fetch) -> str:
    """Resolve a dynamic data URL by scraping a landing page.

    ``disc`` = {page, link_pattern, pick: latest|first|last, format: html|ckan}.
    Fetches the page, collects links matching ``link_pattern`` (HTML hrefs/URLs,
    or a CKAN package_show's resource URLs), and returns one -- the latest by a
    date embedded in the URL (default), or the first/last match. Lets a spec point
    at a stable landing page when the data file URL is date-stamped or multi-file.
    """
    page = disc["page"]
    content = fetch(page, False)
    pat = re.compile(disc.get("link_pattern", r"\.csv"), re.I)
    pairs: list[tuple[str, str]] = []   # (url, date-source string = url + name)
    if disc.get("format") in ("ckan", "json"):
        data = json.loads(content) if isinstance(content, (str, bytes)) else content
        resources = []
        if isinstance(data, dict):
            resources = (data.get("result", {}) or {}).get("resources") or data.get("resources") or []
        for r in resources:
            if not isinstance(r, dict):
                continue
            u, nm = r.get("url", ""), r.get("name", "")
            if u and pat.search(f"{u} {nm}"):
                pairs.append((u, f"{u} {nm}"))
    else:
        raw = re.findall(r'href="([^"]+)"', content) + re.findall(r'https?://[^\s"\'<>]+', content)
        for u in raw:
            if pat.search(u):
                au = urljoin(page, u)
                pairs.append((au, au))
    seen: set[str] = set()
    pairs = [(u, d) for u, d in pairs if u and not (u in seen or seen.add(u))]
    if not pairs:
        raise ValueError(f"discover: no link matching {disc.get('link_pattern')!r} on {page}")
    pick = disc.get("pick", "latest")
    if pick == "first":
        return pairs[0][0]
    if pick == "last":
        return pairs[-1][0]
    return max(pairs, key=lambda p: _date_key(p[1]))[0]


def _urllib_fetch(url: str, binary: bool):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=90) as r:  # noqa: S310
        raw = r.read(16_000_000)
    return raw if binary else raw.decode("utf-8", "ignore")


def _curl_fetch(url: str, binary: bool):
    """TLS-impersonation fetch (curl_cffi) for WAF-protected gov portals.

    Many open-data sites (e.g. tourism.gov.mv) 403 a plain urllib request but
    serve a browser TLS fingerprint fine. Requires the optional curl_cffi extra.
    """
    from curl_cffi import requests as _creq
    r = _creq.get(url, impersonate="chrome", timeout=90)
    r.raise_for_status()
    return r.content if binary else r.text


def _default_fetch(url: str, binary: bool):
    """Fetch via urllib, falling back to curl_cffi (browser TLS) on any failure."""
    try:
        return _urllib_fetch(url, binary)
    except Exception:  # noqa: BLE001 -- retry blocked/transient errors with impersonation
        return _curl_fetch(url, binary)


def _paginate(spec: dict, fetch, binary: bool) -> list[dict]:
    """Offset-paginate a JSON API. ``paginate`` block:

        {size_param: limit, offset_param: offset, size: 5000, max_records: 60000}

    Works for CKAN (``limit``/``offset``) and Socrata (``$limit``/``$offset``).
    Stops when a page returns fewer than ``size`` records or ``max_records`` is hit.
    """
    pg = spec["paginate"]
    size = int(pg.get("size", 1000))
    sp, op = pg.get("size_param", "limit"), pg.get("offset_param", "offset")
    max_records = int(pg.get("max_records", 100_000))
    base = spec["url"]
    sep = "&" if "?" in base else "?"
    out: list[dict] = []
    off = 0
    while off < max_records:
        url = f"{base}{sep}{sp}={size}&{op}={off}"
        recs = parse_spec(spec, fetch(url, binary))
        if not recs:
            break
        out.extend(recs)
        if len(recs) < size:
            break
        off += size
    return out


def _browser_fetch(url: str, binary: bool, warmup: str | None, headed: bool = False):
    spec = importlib.util.spec_from_file_location(
        "dc_browser_scrape_for_spec", str(_ROOT / "scripts" / "browser_scrape.py"))
    bs = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bs
    spec.loader.exec_module(bs)
    return bs.browser_fetch(url, warmup_url=warmup, binary=binary, headed=headed,
                            challenge_wait_s=10.0 if headed else 4.0)


def _spec_fetch(spec: dict):
    """Pick the default fetcher for a spec by ``fetch_via``:

    * ``browser``  -> headless Playwright/Edge (JS-rendered SPAs, header WAFs)
    * ``agentic``  -> HEADED real browser with a longer challenge wait (the
      interactive tier, far likelier to clear a Cloudflare managed challenge)
    * (omitted)    -> urllib, auto-falling back to curl_cffi
    """
    via = spec.get("fetch_via")
    if via in ("browser", "agentic"):
        warm = spec.get("warmup_url") or (spec.get("discover") or {}).get("page")
        headed = via == "agentic"
        return lambda url, binary: _browser_fetch(url, binary, warm, headed=headed)
    return _default_fetch


def resolve(spec: dict, *, fetch=None) -> list[dict]:
    """Fetch + parse + stamp a spec into entity dicts. ``fetch(url, binary)`` injectable."""
    fetch = fetch or _spec_fetch(spec)
    if spec.get("discover"):
        spec = {**spec, "url": discover_url(spec["discover"], fetch=fetch)}
    binary = spec.get("format") in _BYTE_FORMATS
    if spec.get("paginate"):
        records = _paginate(spec, fetch, binary)
    else:
        records = parse_spec(spec, fetch(spec["url"], binary))
    return to_entities(records, spec)


def resolve_id(spec_id: str, *, fetch=None, specs: dict | None = None) -> list[dict]:
    """Resolve a single spec by id (raises KeyError if unknown)."""
    specs = specs if specs is not None else load_specs()
    return resolve(specs[spec_id], fetch=fetch)


def validate_spec(spec: dict) -> list[str]:
    """Return a list of problems with a spec ([] = valid)."""
    problems = []
    for req in ("id", "format", "entity_type"):
        if not spec.get(req):
            problems.append(f"missing {req}")
    if not spec.get("url") and not (spec.get("discover") or {}).get("page"):
        problems.append("missing url or discover.page")
    if spec.get("format") not in (_TEXT_FORMATS | _BYTE_FORMATS):
        problems.append(f"bad format {spec.get('format')!r}")
    if spec.get("format") == "pdf":
        if not spec.get("row_regex") or not spec.get("groups"):
            problems.append("pdf needs row_regex + groups")
    elif not spec.get("fields"):
        problems.append("missing fields")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list spec ids")
    ap.add_argument("--validate", action="store_true", help="validate all specs")
    ap.add_argument("--id", help="resolve one spec live")
    ap.add_argument("--out", help="write entities jsonl to this path")
    args = ap.parse_args(argv)
    specs = load_specs()

    if args.list or args.validate:
        for sid, spec in specs.items():
            problems = validate_spec(spec) if args.validate else []
            tag = "OK" if not problems else "BAD: " + "; ".join(problems)
            print(f"  [{spec.get('format','?'):10}] {sid:22} {spec.get('jurisdiction',''):3} {tag}")
        print(f"\n{len(specs)} specs")
        return 0

    if args.id:
        ents = resolve_id(args.id, specs=specs)
        print(f"{args.id}: {len(ents)} entities", file=sys.stderr)
        if args.out:
            ekb_spec = importlib.util.spec_from_file_location(
                "dc_entity_kb_for_spec", str(_ROOT / "scripts" / "entity_kb.py"))
            ekb = importlib.util.module_from_spec(ekb_spec)
            sys.modules[ekb_spec.name] = ekb
            ekb_spec.loader.exec_module(ekb)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in ents]))
            print(f"  -> {out}", file=sys.stderr)
        for e in ents[:5]:
            print(f"  {e['name'][:44]:44} {e['jurisdiction']:3} {e['status'][:16]}", file=sys.stderr)
        return 0 if ents else 1

    ap.error("provide --list, --validate, or --id")


if __name__ == "__main__":
    raise SystemExit(main())
