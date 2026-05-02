"""Download + OCR the image-type entries in the curated list, extract
entities from the OCR text, and merge into the entities_v2 index.

Uses EasyOCR (pure-Python torch wheel) so no Tesseract install needed.
Caches OCR results per file so it's re-runnable.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "data" / "drive_manifest.json"
CURATED = REPO / "data" / "drive_curated_file_ids.json"
IMG_CACHE = REPO / "data" / "drive_image_cache"
OCR_CACHE = REPO / "data" / "drive_image_ocr_cache"
OCR_ENTITIES_OUT = REPO / "data" / "drive_image_ocr_entities.json"
OCR_REPORT = REPO / "data" / "drive_image_ocr_report.md"

# Reuse the same extraction patterns as the waterfall (quick copies)
GEO_TOKENS = {"SAR", "UAE", "USA", "UK", "HK", "PH", "PRC", "EU",
               "Taiwan", "Singapore", "Philippines"}
RX_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RX_PHONE_PH = re.compile(r"(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)")
RX_PHONE_HK = re.compile(r"(?<!\d)[2-9]\d{7}(?!\d)")
RX_PHONE_INTL = re.compile(r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
RX_AMOUNT = re.compile(
    r"(?:PHP|USD|EUR|HKD|AED|SAR|QAR|MYR|SGD|INR|NPR|BDT|\$)"
    r"\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?", re.IGNORECASE)
RX_PASSPORT = re.compile(r"\b([A-Z]{1,2}\d{6,9})\b")
ORG_SUFFIXES = ["CORPORATION", "CORP", "INC", "LIMITED", "LTD", "LLC",
                 "AGENCY", "CONSULTANTS", "COMPANY", "CO",
                 "EMPLOYMENT", "RECRUITMENT", "MANPOWER",
                 "LENDING", "CREDIT", "FINANCE"]
RX_ORG = re.compile(
    r"\b((?:[A-Z][A-Z0-9'&\-]{1,20}\s+){1,6}(?:"
    + "|".join(re.escape(s) for s in ORG_SUFFIXES) + r"))\b")
RX_PH_BANK = re.compile(
    r"\b(?:BDO|BPI|METROBANK|UCPB|PNB|LANDBANK|DBP|CHINABANK|RCBC|"
    r"UNIONBANK|EASTWEST|PSBANK)\b[\s:#.]*([0-9][\-0-9\s]{6,28})",
    re.IGNORECASE)
GOV = ["POEA","POLO","PCG","DOLE","DMW","OWWA","NBI","DFA","SEC","BSP",
       "BP2MI","IOM","ILO","AMLC","FATF","NLRC"]


def extract_ents(txt: str) -> dict:
    out = defaultdict(set)
    if not txt:
        return out
    for m in RX_EMAIL.finditer(txt):
        v = m.group(0).lower()
        if ".." not in v:
            out["email"].add(v)
    for m in RX_PHONE_PH.finditer(txt):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 11 and d.startswith("09"):
            out["phone"].add("+63" + d[1:])
    for m in RX_PHONE_HK.finditer(txt):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 8 and d[0] in "235689":
            out["phone"].add("+852" + d)
    for m in RX_PHONE_INTL.finditer(txt):
        d = re.sub(r"\D", "", m.group(0))
        if 9 <= len(d) <= 14:
            out["phone"].add("+" + d)
    for m in RX_PH_BANK.finditer(txt):
        num = re.sub(r"\s", "", m.group(1))
        if len(num) >= 8:
            bank = m.group(0).split()[0].upper()
            out["financial_account"].add(f"{bank}:{num}")
    for m in RX_AMOUNT.finditer(txt):
        amt = re.sub(r"\s+", " ", m.group(0)).strip()
        if len(re.sub(r"\D", "", amt)) >= 3:
            out["amount"].add(amt)
    for m in RX_PASSPORT.finditer(txt):
        out["id_number"].add(m.group(1))
    for m in RX_ORG.finditer(txt):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        if (6 <= len(name) <= 80 and len(name.split()) >= 2
                and name.upper() not in GEO_TOKENS):
            out["org"].add(name)
    for tok in GOV:
        if re.search(r"\b" + tok + r"\b", txt):
            out["gov_ref"].add(tok)
    return {k: sorted(v) for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--min-score", type=int, default=20)
    ap.add_argument("--languages", default="en",
                    help="EasyOCR languages (comma-separated), e.g. 'en,tl'")
    ap.add_argument("--api-key",
                    default=os.environ.get(
                        "GOOGLE_DRIVE_API_KEY",
                        "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA"))
    args = ap.parse_args()

    IMG_CACHE.mkdir(parents=True, exist_ok=True)
    OCR_CACHE.mkdir(parents=True, exist_ok=True)

    try:
        import requests as _rq
    except Exception as e:
        print(f"requests missing: {e}"); return 1
    try:
        import easyocr
    except ImportError:
        print("pip install easyocr"); return 1

    # Load curated file list, keep only image mimes
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    img_mimes = ("image/jpeg", "image/png", "image/webp",
                  "image/tiff", "image/gif")
    picks = [e for e in curated
             if e.get("mime") in img_mimes
             and e.get("score", 0) >= args.min_score]
    picks = sorted(picks, key=lambda e: -e.get("score", 0))[:args.max]
    print(f"[ocr] {len(picks)} image files to OCR "
          f"(cap={args.max}, min_score={args.min_score})")

    print(f"[ocr] loading EasyOCR (languages={args.languages})")
    langs = [x.strip() for x in args.languages.split(",") if x.strip()]
    reader = easyocr.Reader(langs, gpu=False, verbose=False)
    print(f"[ocr] reader loaded")

    entity_index: dict = defaultdict(lambda: defaultdict(
        lambda: {"file_ids": set(), "bundles": set()}))
    file_entities: dict = {}
    t0 = time.time()
    errs = 0
    for i, e in enumerate(picks, 1):
        fid = e["id"]
        bundle = e.get("bundle") or "unknown"
        name = e.get("name") or fid
        safe = re.sub(r"[^\w.\-]", "_", name)[:80]
        img_path = IMG_CACHE / f"{fid}__{safe}"
        ocr_path = OCR_CACHE / f"{fid}.txt"

        # Use cached OCR if present
        if ocr_path.exists() and ocr_path.stat().st_size > 0:
            try:
                txt = ocr_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = ""
        else:
            # Download image if not cached
            if not img_path.exists() or img_path.stat().st_size == 0:
                url = (f"https://www.googleapis.com/drive/v3/files/{fid}"
                       f"?alt=media&key={args.api_key}")
                try:
                    r = _rq.get(url, timeout=60)
                    if r.status_code != 200:
                        if i <= 5 or errs < 3:
                            print(f"  [{i}] DL HTTP {r.status_code}: "
                                  f"{name[:50]}")
                        errs += 1
                        continue
                    img_path.write_bytes(r.content)
                except Exception as ex:
                    if i <= 5 or errs < 3:
                        print(f"  [{i}] DL {type(ex).__name__}: {ex}")
                    errs += 1
                    continue
            # OCR it
            try:
                result = reader.readtext(str(img_path), detail=0)
                txt = chr(10).join(result) if isinstance(result, list) else str(result)
            except Exception as ex:
                if i <= 5 or errs < 3:
                    print(f"  [{i}] OCR {type(ex).__name__}: {ex}")
                errs += 1
                continue
            try:
                ocr_path.write_text(txt, encoding="utf-8")
            except Exception:
                pass

        if not txt.strip():
            continue
        ents = extract_ents(txt)
        file_entities[fid] = {
            "bundle": bundle, "name": name,
            "entities": ents, "text_chars": len(txt),
        }
        for etype, vals in ents.items():
            for v in vals:
                entity_index[etype][v]["file_ids"].add(fid)
                entity_index[etype][v]["bundles"].add(bundle)
        if i % 10 == 0:
            elapsed = time.time() - t0
            print(f"[ocr] {i}/{len(picks)} processed, errs={errs}, "
                  f"elapsed={elapsed:.0f}s, "
                  f"entities={sum(len(v) for v in entity_index.values())}")

    elapsed = time.time() - t0
    print(f"[ocr] done: processed {len(file_entities)} files in "
          f"{elapsed:.0f}s, errs={errs}")

    # Save entity index
    out = {
        etype: [{
            "value": val, "n_bundles": len(m["bundles"]),
            "n_files": len(m["file_ids"]),
            "bundles": sorted(m["bundles"])[:20],
            "file_ids": sorted(m["file_ids"])[:20],
        } for val, m in sorted(
            vals.items(),
            key=lambda kv: (-len(kv[1]["bundles"]),
                              -len(kv[1]["file_ids"])),
        )]
        for etype, vals in entity_index.items()
    }
    OCR_ENTITIES_OUT.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[ocr] wrote {OCR_ENTITIES_OUT}")

    # Report
    md = [
        "# OCR-derived image entity report",
        "",
        f"- Images OCR'd: {len(file_entities)} (target {len(picks)})",
        f"- Errors: {errs}",
        f"- Distinct entities extracted: "
        f"{sum(len(v) for v in entity_index.values())}",
        "",
    ]
    for etype in ("person", "org", "email", "phone",
                   "financial_account", "id_number", "amount", "gov_ref"):
        vals = entity_index.get(etype, {})
        top = sorted(vals.items(),
                      key=lambda kv: (-len(kv[1]["bundles"]),
                                        -len(kv[1]["file_ids"])))[:15]
        cross = [(v, m) for v, m in top if len(m["bundles"]) >= 2]
        if not cross:
            continue
        md.append(f"## {etype} -- {len(cross)} cross-bundle (image-OCR)")
        md.append("")
        md.append("| bundles | files | value |")
        md.append("|---:|---:|---|")
        for v, m in cross:
            md.append(f"| {len(m['bundles'])} | {len(m['file_ids'])} | "
                      f"`{v[:70]}` |")
        md.append("")
    OCR_REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[ocr] wrote {OCR_REPORT}")
    print(f"\n=== IMAGE-OCR SUMMARY ===")
    print(f"  images processed : {len(file_entities)}")
    print(f"  errors           : {errs}")
    print(f"  entities found   : {sum(len(v) for v in entity_index.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
