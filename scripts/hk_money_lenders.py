#!/usr/bin/env python3
"""Hong Kong licensed money-lenders collector (Companies Registry PDF).

The HK Companies Registry publishes the OFFICIAL list of existing money-lender
licensees as a downloadable PDF -- the same source the public Kaggle scraper
``migrantworkerdatahub/hong-kong-money-lenders`` targets. That kernel routed the
PDF through PDF->image->vision because it assumed a complex layout; in fact the
text layer extracts cleanly with one licensee per line, so this collector parses
it DETERMINISTICALLY (no model, no tokens) -- faster, free, and reproducible.

Real on-the-wire row shape (text layer, columns collapsed to spaces):

    <MLR_No> <Licence_No> <English Name> [<Chinese Name>] <Expiry D-Mon-YY> [R]
    6323 56/2026 001 Credit Limited 001 ...        8-Nov-26
    6665 1880/2025 101 Finance Group Limited       13-Jan-27      (no Chinese name)
    5399 0867/2025 28 Loan Company Limited ...      16-Apr-26 R    (R = renewal in progress)

Money lenders are a load-bearing trafficking vector: debt-bondage recruitment
fees are frequently laundered through licensed lenders, so a current roster of
who is licensed (and who is NOT) is exactly the screening signal DueCare needs.

Design mirrors hk_eaa_collector: the PDF download is injectable, so the parser
and the entity mapping are tested offline against the real row format with no
network. Propose-only -- writes to reports/entity_kb/.

Usage:
    python scripts/hk_money_lenders.py --pdf-url        # download + parse the live PDF
    python scripts/hk_money_lenders.py --pdf path.pdf   # parse a local copy
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import re
import sys
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "duecare-recruitment-screen/1.0 (+defensive anti-trafficking review; respects robots.txt)"

#: official Companies Registry list of EXISTING money-lender licensees (alpha order)
ML_PDF = "https://www.cr.gov.hk/en/statistics/docs/ml_licensees1.pdf"

_CJK = re.compile(r"[㐀-鿿豈-﫿]")
#: a data row: MLR no, licence no (n/yyyy), name blob, expiry date, optional R remark
_ROW = re.compile(
    r"^\s*(\d{3,6})\s+(\d{1,4}/\d{4})\s+(.+?)\s+(\d{1,2}-[A-Za-z]{3}-\d{2,4})\s*(R)?\s*$"
)
_AS_AT = re.compile(r"as at\s+(\d{1,2}\s+\w+\s+\d{4})", re.I)


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_hkml", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_as_at(text: str) -> str:
    """Pull the 'as at <date>' snapshot date from the PDF header (''=not found)."""
    m = _AS_AT.search(text or "")
    return m.group(1) if m else ""


def _split_en_cn(blob: str) -> tuple[str, str]:
    """Split a collapsed 'English Name [Chinese Name]' blob at the first CJK char.

    When a Chinese name is present, a trailing run of digits left on the English
    side is the Latin prefix of the Chinese column (e.g. '001 ...信貸') and is
    trimmed; English company names that legitimately contain numbers keep them
    because those do not sit at the very end before a Chinese name.
    """
    m = _CJK.search(blob)
    if not m:
        return blob.strip(), ""
    en, cn = blob[:m.start()].strip(), blob[m.start():].strip()
    if cn:
        en = re.sub(r"\s+\d+$", "", en).strip()
    return en, cn


def parse_ml_pdf(text: str) -> list[dict]:
    """Parse the money-lender list PDF text into licensee records.

    Returns one dict per licensee with name (English), name_local (Chinese),
    license_no, mlr_no, license_expiry, and the renewal-in-progress flag. Header,
    footer, page-number and column-title lines never match ``_ROW`` and are
    skipped, so the parse is robust to the surrounding bilingual boilerplate.
    """
    as_at = parse_as_at(text)
    recs: list[dict] = []
    for raw in (text or "").splitlines():
        m = _ROW.match(raw)
        if not m:
            continue
        mlr_no, lic_no, blob, expiry, remark = m.groups()
        en, cn = _split_en_cn(blob)
        if len(en) < 2:
            continue
        recs.append({
            "name": en, "name_local": cn, "jurisdiction": "HK",
            "license_no": lic_no, "mlr_no": mlr_no, "license_expiry": expiry,
            "status": "valid", "status_as_of": as_at,
            "renewal_in_progress": bool(remark),
            "source": "HK Companies Registry - List of Existing Money Lenders Licensees (PDF)",
            "source_tier": "official",
        })
    return recs


def download_pdf(url: str = ML_PDF, *, fetch=None) -> bytes:
    """Download the PDF (``fetch(url)->bytes`` injectable for tests)."""
    if fetch is not None:
        return fetch(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (https gov URL)
        return r.read(8_000_000)


def pdf_text(pdf_bytes: bytes) -> str:
    """Extract the text layer from the PDF bytes (requires pypdf)."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - env guard
        raise ImportError("pypdf required: pip install pypdf") from exc
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((pg.extract_text() or "") for pg in reader.pages)


def records_to_entities(records: list[dict]) -> list[dict]:
    """Map money-lender licensee records to ``lender`` entity dicts (HK)."""
    out = []
    for r in records:
        name = r.get("name", "")
        if not name:
            continue
        notes = f"Money Lender's Licence No. {r.get('license_no','')}".strip()
        if r.get("license_expiry"):
            notes += f"; expires {r['license_expiry']}"
        if r.get("renewal_in_progress"):
            notes += "; renewal in progress"
        if r.get("name_local"):
            notes += f"; {r['name_local']}"
        out.append({
            "entity_type": "lender", "name": name, "jurisdiction": "HK",
            "status": r.get("status", "valid"),
            "license_no": r.get("license_no", ""),
            "source": r.get("source", "HK Companies Registry money-lender list"),
            "source_tier": r.get("source_tier", "official"),
            "notes": notes,
        })
    return out


def collect(*, fetch=None, pdf_path: str | None = None) -> list[dict]:
    """Download (or read) the PDF and return licensee records."""
    data = Path(pdf_path).read_bytes() if pdf_path else download_pdf(fetch=fetch)
    return parse_ml_pdf(pdf_text(data))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf-url", action="store_true", help="download + parse the live CR PDF")
    ap.add_argument("--pdf", help="parse a local ml_licensees1.pdf")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "entity_kb" / "hk_money_lenders.jsonl"))
    args = ap.parse_args(argv)
    if not (args.pdf or args.pdf_url):
        ap.error("provide --pdf-url or --pdf")

    try:
        records = collect(pdf_path=args.pdf)
    except Exception as exc:  # noqa: BLE001
        print(f"PDF route failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    entities = records_to_entities(records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ekb = _sibling("entity_kb")
    ekb.save_entities(out, ekb.merge_entities([ekb.record_from_dict(e) for e in entities]))
    print(f"HK money lenders: {len(entities)} licensees -> {out}", file=sys.stderr)
    for e in entities[:5]:
        print(f"  - {e['name'][:42]} | {e['license_no']}", file=sys.stderr)
    return 0 if entities else 1


if __name__ == "__main__":
    raise SystemExit(main())
