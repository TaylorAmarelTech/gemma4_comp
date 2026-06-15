#!/usr/bin/env python3
"""China MARA distant-water-fishing enterprise compliance collector (deterministic HTML).

The Ministry of Agriculture and Rural Affairs (MARA) Fisheries Bureau publishes
an annual public notice of the compliance-assessment results for every nationally
licensed distant-water-fishing (DWF) enterprise. Sea-based forced labour on
distant-water fleets is among the most severe trafficking vectors, and a Chinese
DWF enterprise's published compliance SCORE is a direct, official risk signal:
the lower the score, the worse the compliance record.

The notice is a single server-rendered HTML table -- columns:

    序号 (rank) | 企业名称 (enterprise name) | 得分 (compliance score)

-- so it parses DETERMINISTICALLY (no browser, no tokens). The 2024 edition lists
167 enterprises scored 89-117, ranked best-to-worst-compliance. The enterprise
names are Chinese (kept as-is); the score + rank go into notes.

The URL is per-edition (annual), so it is overridable; the download is injectable
so the parser is tested offline. Propose-only.

Usage:
    python scripts/cn_mara_dwf.py                 # download + parse the live notice
    python scripts/cn_mara_dwf.py --html path.html
"""
from __future__ import annotations

import argparse
import html as _html
import importlib.util
import re
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = ("Mozilla/5.0 (compatible; duecare-recruitment-screen/1.0; "
              "+defensive anti-trafficking review; respects robots.txt)")

#: 2024 DWF enterprise compliance-assessment results (latest verified edition)
MARA_URL = "https://www.moa.gov.cn/govpublic/YYJ/202504/t20250417_6473317.htm"

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_cnmara", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _text(fragment: str) -> str:
    """Strip tags, unescape entities, drop nbsp, collapse whitespace."""
    t = _html.unescape(re.sub(r"<[^>]+>", "", fragment or "")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse_mara_html(page: str) -> list[dict]:
    """Parse the MARA DWF notice HTML into enterprise compliance records.

    A data row is any ``<tr>`` whose first cell is a rank number and whose last
    cell is a numeric score; the header row (序号/企业名称/得分) and any chrome
    rows are skipped automatically.
    """
    recs: list[dict] = []
    for tr in _ROW.findall(page or ""):
        cells = [_text(c) for c in _CELL.findall(tr)]
        cells = [c for c in cells if c != ""]
        if len(cells) < 3:
            continue
        rank, name, score = cells[0], cells[1], cells[-1]
        if not rank.isdigit() or not re.fullmatch(r"\d{1,3}(?:\.\d+)?", score):
            continue
        if len(name) < 2:
            continue
        recs.append({
            "rank": int(rank), "name": name, "score": float(score),
            "jurisdiction": "CN", "status": "licensed",
            "source": "CN MARA distant-water-fishing enterprise compliance assessment",
            "source_tier": "official",
        })
    return recs


def download_html(url: str = MARA_URL, *, fetch=None) -> str:
    """Download the notice (``fetch(url)->str`` injectable for tests)."""
    if fetch is not None:
        return fetch(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (https gov URL)
        raw = r.read(8_000_000)
    enc = "utf-8"
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:2000])
    if m:
        enc = m.group(1).decode("ascii", "ignore") or "utf-8"
    return raw.decode(enc, "ignore")


def collect(*, fetch=None, html_path: str | None = None) -> list[dict]:
    """Download (or read) the notice and return enterprise records."""
    page = Path(html_path).read_text(encoding="utf-8", errors="ignore") if html_path \
        else download_html(fetch=fetch)
    return parse_mara_html(page)


def records_to_entities(records: list[dict]) -> list[dict]:
    """Map MARA records to DWF-enterprise entity dicts (CN). entity_type=company."""
    total = len(records)
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        notes = (f"DWF compliance score {r.get('score', 0):g} "
                 f"(MARA assessment, rank {r.get('rank','')}/{total}; lower score = higher risk)")
        out.append({
            "entity_type": "company", "name": name, "jurisdiction": "CN",
            "status": r.get("status", "licensed"),
            "sector": "distant_water_fishing",
            "source": r.get("source", "CN MARA DWF compliance assessment"),
            "source_tier": r.get("source_tier", "official"),
            "notes": notes,
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", help="parse a local copy of the notice page")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "cn_mara_dwf.jsonl"))
    args = ap.parse_args(argv)

    try:
        records = collect(html_path=args.html)
    except Exception as exc:  # noqa: BLE001
        print(f"MARA fetch/parse failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    if records:
        worst = min(records, key=lambda r: r["score"])
        print(f"CN MARA: {len(entities)} DWF enterprises -> {out}", file=sys.stderr)
        print(f"  score range {min(r['score'] for r in records)}-{max(r['score'] for r in records)}; "
              f"worst-compliance rank {worst['rank']} (score {worst['score']})", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
