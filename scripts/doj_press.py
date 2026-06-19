#!/usr/bin/env python3
"""DOJ press-releases connector -> trafficking/labour prosecution documents (public domain).

The US DOJ press-release API (``justice.gov/api/v1/press_releases.json``, no key, 267k+
records across DOJ HQ + all 93 US Attorney offices) is the single best open feed of
*named* trafficking and forced-labour prosecutions with modus operandi. This connector
pulls a title-filtered subset (the API supports a ``title`` substring filter -- e.g.
``title=trafficking`` narrows to ~20k), cleans each release, and emits a structured,
RAG-ready document with the deterministic metadata we can extract reliably: office /
district, date, statutes cited (18 U.S.C. forced-labour/trafficking sections), and the
press-release number.

Deliberately NOT done here: pulling named defendant *entities* out of the prose -- that
is Gemma's extraction job downstream. This connector produces clean, cited source
documents (US public domain) for the RAG corpus + that extraction step; propose-only.

Usage:
    python scripts/doj_press.py --title "human trafficking" --max 50
    python scripts/doj_press.py --title "forced labor" --match "1589|1590|1351" --out reports/acquisition/doj.jsonl
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_BASE = "https://www.justice.gov/api/v1/press_releases.json"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# US Code citations, esp. trafficking/forced-labour: 18 U.S.C. 1589/1590/1591/1592/1351
_USC = re.compile(r"\b(\d{1,2})\s*U\.?\s?S\.?\s?C\.?\s*(?:§+|sections?|sec\.?)?\s*(\d{3,4}[a-z]?)", re.I)


def _strip_html(s: str) -> str:
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", s or ""))).strip()


def _ts_to_iso(ts) -> str:
    """DOJ ``date`` is a unix-timestamp string -> 'YYYY-MM-DD' (empty if unparseable)."""
    try:
        return datetime.fromtimestamp(int(str(ts).strip()), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return ""


# DOJ press releases describe charges in plain language (USC sections live in the
# indictment, not the release) -- so these offense terms are the reliable deterministic tag.
_OFFENSE_TERMS = (
    "forced labor", "involuntary servitude", "debt bondage", "peonage", "document servitude",
    "human trafficking", "labor trafficking", "sex trafficking", "trafficking in persons",
    "foreign labor contracting", "visa fraud", "alien smuggling", "migrant smuggling",
    "wire fraud", "mail fraud", "bank fraud", "money laundering", "racketeering",
    "identity theft", "extortion", "kidnapping", "conspiracy")


def statutes(text: str) -> list[str]:
    """Distinct US-Code citations found in the text, normalized as 'NN USC NNNN'."""
    out: list[str] = []
    for title, sec in _USC.findall(text or ""):
        cite = f"{title} USC {sec}"
        if cite not in out:
            out.append(cite)
    return out


def offenses(text: str) -> list[str]:
    """Charge/offense terms named in the text (the reliable plain-language signal)."""
    t = (text or "").lower()
    return [o for o in _OFFENSE_TERMS if o in t]


def parse_release(rec: dict) -> dict:
    """One API record -> a structured, RAG-ready document (US public domain)."""
    title = _strip_html(rec.get("title") or "")     # titles carry HTML entities (&#039; ...)
    text = _strip_html(rec.get("body", ""))
    blob = f"{title} {text}"
    return {
        "title": title,
        "date": _ts_to_iso(rec.get("date")),
        "url": rec.get("url", ""),
        "office": "; ".join(c.get("name", "") for c in (rec.get("component") or []) if c.get("name")),
        "pr_number": rec.get("number", ""),
        "offenses": offenses(blob),
        "statutes": statutes(blob),
        "teaser": _strip_html(rec.get("teaser", "")),
        "text": text,
        "uuid": rec.get("uuid", ""),
        "source": "DOJ press releases (justice.gov, US public domain)",
    }


def select(records: list[dict], match: str | None) -> list[dict]:
    """Keep records whose title+text matches a regex (client-side refine; all if None)."""
    if not match:
        return records
    rx = re.compile(match, re.I)
    return [r for r in records if rx.search(f"{r.get('title', '')} {r.get('text', '')}")]


# ---------------------------------------------------------------------------
# Fetch + paginate
# ---------------------------------------------------------------------------

def build_url(*, title: str | None, page: int, pagesize: int) -> str:
    params = {"pagesize": pagesize, "page": page, "sort": "date", "direction": "DESC"}
    if title:
        params["title"] = title
    return _BASE + "?" + urllib.parse.urlencode(params)


def _urllib_fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:  # noqa: S310 - https gov API
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_releases(*, title: str | None = None, max_records: int = 100, pagesize: int = 50,
                   fetch=_urllib_fetch) -> list[dict]:
    """Paginate the API (newest first) and return up to ``max_records`` parsed documents."""
    out: list[dict] = []
    page = 0
    while len(out) < max_records:
        payload = fetch(build_url(title=title, page=page, pagesize=min(pagesize, max_records)))
        results = payload.get("results") or []
        if not results:
            break
        for rec in results:
            out.append(parse_release(rec))
            if len(out) >= max_records:
                break
        page += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", help="server-side title substring filter (e.g. 'human trafficking')")
    ap.add_argument("--match", help="client-side regex over title+body (e.g. '1589|forced labor')")
    ap.add_argument("--max", type=int, default=100, help="max records (default 100)")
    ap.add_argument("--out", help="propose-only documents JSONL (under reports/)")
    args = ap.parse_args(argv)

    docs = select(fetch_releases(title=args.title, max_records=args.max), args.match)
    n_off = sum(1 for d in docs if d["offenses"])
    print(f"DOJ: {len(docs)} releases (title={args.title!r} match={args.match!r}); "
          f"{n_off} name an offense", file=sys.stderr)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in docs), encoding="utf-8")
        print(f"wrote {out} -- PROPOSE-ONLY")
    else:
        for d in docs[:12]:
            print(f"  [{d['date']}] {d['title'][:58]}")
            print(f"      {d['office'][:46]} | offenses={d['offenses']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
