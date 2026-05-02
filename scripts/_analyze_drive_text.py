"""Offline text/entity analysis of the curated Drive file list.

Downloads the text-bearing curated files (PDF, DOCX, Google Docs),
extracts text, runs regex-based entity extraction, and builds a
cross-bundle connection graph so we can prioritize documents that
share entities with other case files BEFORE sending to Kaggle.

Inputs:
    data/drive_curated_file_ids.json   (produced by _enumerate_drive_folders.py)

Outputs:
    data/drive_text_cache/             cached raw text per file
    data/drive_entities.json           entity -> [files, bundles]
    data/drive_cross_bundle.md         readable cross-bundle report
    data/drive_curated_connected.json  refined curated list sorted by
                                       connection density
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
CURATED_JSON = REPO_ROOT / "data" / "drive_curated_file_ids.json"
TEXT_CACHE = REPO_ROOT / "data" / "drive_text_cache"
ENTITIES_JSON = REPO_ROOT / "data" / "drive_entities.json"
CROSS_MD = REPO_ROOT / "data" / "drive_cross_bundle.md"
REFINED_JSON = REPO_ROOT / "data" / "drive_curated_connected.json"


# -----------------------------------------------------------------------------
#  Entity extraction patterns
# -----------------------------------------------------------------------------

RX_PHONE = re.compile(
    r"(?<!\d)(?:\+?(\d{1,3})[-.\s]?)?(?:\(?(\d{2,4})\)?[-.\s]?)?"
    r"(\d{3,4})[-.\s]?(\d{3,4})(?!\d)"
)
RX_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RX_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
RX_ACCOUNT = re.compile(
    r"(?:account(?:\s+(?:no|number|#))?|a[/.]?c|acct)[:\s#.]*"
    r"([0-9][\-0-9\s]{5,25})",
    re.IGNORECASE,
)
RX_PASSPORT = re.compile(r"\b([A-Z]{1,2}\d{6,9})\b")
RX_AMOUNT = re.compile(
    r"(?:PHP|USD|EUR|HKD|AED|SAR|QAR|MYR|SGD|INR|NPR|BDT|KWD|OMR|\$|P\s*)"
    r"\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

# Org / agency / employer patterns
ORG_SUFFIXES = [
    "CORPORATION", "CORP", "CORP.", "INCORPORATED", "INC", "INC.",
    "LIMITED", "LTD", "LTD.", "LLC", "L.L.C", "PTE",
    "AGENCY", "CONSULTANTS", "ENTERPRISES", "SERVICES",
    "COMPANY", "CO.", "PARTNERS", "GROUP", "HOLDINGS",
    "EMPLOYMENT", "RECRUITMENT", "MANPOWER", "PLACEMENT",
    "LENDING", "CREDIT", "FINANCE", "FOUNDATION", "SOCIETY",
]
# Match: 2-6 capitalized words ending in an org suffix.
RX_ORG = re.compile(
    r"\b((?:[A-Z][A-Z0-9'&.\-]{1,20}\s+){1,6}(?:"
    + "|".join(re.escape(s) for s in ORG_SUFFIXES)
    + r"))\b"
)
# Person name heuristic: honorific + capitalized words, OR
# LASTNAME comma FirstName (common in witness forms).
RX_PERSON_HONORIFIC = re.compile(
    r"\b(?:Mr|Ms|Mrs|Dr|Engr|Atty|Rev)\.?\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})"
)
RX_PERSON_LASTFIRST = re.compile(
    r"\b([A-Z]{2,}(?:[A-Z'\s\-]+)?),\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
)

# Government / regulator references (keep track of these separately)
GOV_TOKENS = [
    "POEA", "POLO", "PCG", "DOLE", "DMW", "OWWA", "NBI", "DFA",
    "SEC", "BSP", "MWO", "BP2MI", "IOM", "ILO",
]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _norm_phone(groups) -> str:
    joined = "".join(g for g in groups if g)
    digits = re.sub(r"\D", "", joined)
    if len(digits) < 8 or len(digits) > 15:
        return ""
    # Trim year-like / ID-like numbers
    if digits.startswith("19") or digits.startswith("20"):
        if len(digits) <= 10:
            return ""
    return digits


def extract_entities(text: str) -> dict:
    ents: dict = defaultdict(set)
    if not text:
        return ents

    for m in RX_EMAIL.finditer(text):
        ents["email"].add(m.group(0).lower())

    for m in RX_PHONE.finditer(text):
        p = _norm_phone(m.groups())
        if p:
            ents["phone"].add(p)

    for m in RX_IBAN.finditer(text):
        ents["financial_account"].add(m.group(0))

    for m in RX_ACCOUNT.finditer(text):
        num = re.sub(r"\s", "", m.group(1))
        if len(num) >= 6:
            ents["financial_account"].add(num)

    for m in RX_PASSPORT.finditer(text):
        ents["id_number"].add(m.group(1))

    for m in RX_AMOUNT.finditer(text):
        ents["amount"].add(_clean(m.group(0)))

    for m in RX_ORG.finditer(text):
        name = _clean(m.group(1))
        # Skip noise: need at least one lowercase char somewhere OR
        # at least 3 words. Drop if ALL-CAPS with < 3 words.
        parts = name.split()
        if len(parts) >= 2 and len(name) >= 6 and len(name) <= 80:
            ents["org"].add(name)

    for m in RX_PERSON_HONORIFIC.finditer(text):
        ents["person"].add(_clean(m.group(1)))
    for m in RX_PERSON_LASTFIRST.finditer(text):
        ents["person"].add(f"{_clean(m.group(1))}, {_clean(m.group(2))}")

    for tok in GOV_TOKENS:
        if re.search(r"\b" + tok + r"\b", text):
            ents["gov_ref"].add(tok)

    # Convert sets to sorted lists
    return {k: sorted(v) for k, v in ents.items()}


# -----------------------------------------------------------------------------
#  Downloaders
# -----------------------------------------------------------------------------

def _download_file_text(svc, file_id: str, mime: str) -> str:
    """Return extracted text for a file, or '' on failure.
    Uses the Drive API export for Google Docs (avoids bytes-to-PDF
    round-trip) and direct alt=media + pypdfium2 for PDFs."""
    import requests as _rq

    if "google-apps.document" in mime:
        # Export as plain text
        export_mime = "text/plain"
        try:
            raw = svc.files().export(
                fileId=file_id, mimeType=export_mime).execute()
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace")
            return str(raw)
        except Exception as e:
            print(f"    export FAIL: {type(e).__name__}: {e}")
            return ""

    if mime == "application/pdf":
        # alt=media download + pypdfium2 text extraction
        api_key = os.environ.get(
            "GOOGLE_DRIVE_API_KEY",
            "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA",
        )
        url = (f"https://www.googleapis.com/drive/v3/files/{file_id}"
               f"?alt=media&key={api_key}")
        try:
            r = _rq.get(url, timeout=60)
            if r.status_code != 200:
                return ""
            pdf_bytes = r.content
        except Exception as e:
            print(f"    PDF DL FAIL: {type(e).__name__}: {e}")
            return ""
        try:
            import pypdfium2 as _pdfium  # type: ignore[import-not-found]
            import io
            pdf = _pdfium.PdfDocument(io.BytesIO(pdf_bytes))
            parts: list = []
            for p in range(min(len(pdf), 40)):   # cap 40 pages
                page = pdf[p]
                tp = page.get_textpage()
                parts.append(tp.get_text_range())
                tp.close()
                page.close()
            pdf.close()
            return "\n".join(parts)
        except Exception as e:
            print(f"    PDF parse FAIL: {type(e).__name__}: {e}")
            return ""

    if mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        api_key = os.environ.get(
            "GOOGLE_DRIVE_API_KEY",
            "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA",
        )
        url = (f"https://www.googleapis.com/drive/v3/files/{file_id}"
               f"?alt=media&key={api_key}")
        try:
            import io, zipfile
            r = _rq.get(url, timeout=60)
            if r.status_code != 200:
                return ""
            z = zipfile.ZipFile(io.BytesIO(r.content))
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="replace")
            # Strip XML tags for a crude text pass
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception as e:
            print(f"    DOCX parse FAIL: {type(e).__name__}: {e}")
            return ""

    return ""


# -----------------------------------------------------------------------------
#  Main
# -----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=300,
                    help="Cap how many files to analyze (from top score).")
    ap.add_argument("--min-cross-bundle", type=int, default=2,
                    help="Entity must appear in >=N bundles to be a "
                         "'connector' (drives the refined list ranking).")
    ap.add_argument("--api-key",
                    default=os.environ.get(
                        "GOOGLE_DRIVE_API_KEY",
                        "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA"))
    args = ap.parse_args()

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("[analyze] pip install google-api-python-client")
        return 1

    svc = build("drive", "v3", developerKey=args.api_key,
                cache_discovery=False)
    curated = json.loads(CURATED_JSON.read_text(encoding="utf-8"))
    text_bearing_mimes = (
        "application/pdf",
        "application/vnd.google-apps.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    text_files = [
        e for e in curated if e.get("mime", "") in text_bearing_mimes
    ]
    text_files = sorted(text_files,
                        key=lambda e: -e.get("score", 0))[:args.max]
    print(f"[analyze] {len(text_files)} text-bearing files to analyze "
          f"(cap={args.max})")

    TEXT_CACHE.mkdir(parents=True, exist_ok=True)

    # entity_type -> entity_value -> {file_ids, bundles}
    index: dict = defaultdict(lambda: defaultdict(
        lambda: {"file_ids": set(), "bundles": set()}))
    file_entities: dict = {}  # file_id -> dict of entity_type -> list
    t0 = time.time()
    done = 0
    err = 0

    for i, e in enumerate(text_files, 1):
        fid = e["id"]
        bundle = e.get("bundle") or "unknown"
        mime = e.get("mime", "")
        name = e.get("name", "")[:60]
        cache_key = f"{bundle[:40].replace('/', '_')}__{fid}.txt"
        cache_path = TEXT_CACHE / cache_key

        if cache_path.exists() and cache_path.stat().st_size > 0:
            text = cache_path.read_text(encoding="utf-8", errors="replace")
        else:
            try:
                text = _download_file_text(svc, fid, mime)
            except Exception as ex:
                print(f"  [{i:>3}] ERR {type(ex).__name__}: {ex}")
                err += 1
                continue
            if not text:
                err += 1
                continue
            try:
                cache_path.write_text(text, encoding="utf-8")
            except Exception:
                pass

        ents = extract_entities(text)
        file_entities[fid] = {
            "bundle": bundle, "name": e.get("name", ""),
            "mime": mime,
            "entities": ents,
            "text_chars": len(text),
        }
        for etype, vals in ents.items():
            for v in vals:
                index[etype][v]["file_ids"].add(fid)
                index[etype][v]["bundles"].add(bundle)
        done += 1
        if done % 15 == 0:
            elapsed = time.time() - t0
            print(f"  [{i:>3}/{len(text_files)}] analyzed {done}, "
                  f"errs {err}, elapsed {elapsed:.0f}s")

    elapsed = time.time() - t0
    print(f"[analyze] done: {done} files in {elapsed:.0f}s, {err} errors")

    # ---- Build cross-bundle connection report
    connectors: dict = {}  # entity_type -> list of (value, bundles, file_ids)
    for etype, values in index.items():
        rows = []
        for val, meta in values.items():
            nb = len(meta["bundles"])
            if nb >= args.min_cross_bundle:
                rows.append({
                    "value": val,
                    "n_bundles": nb,
                    "bundles": sorted(meta["bundles"]),
                    "file_ids": sorted(meta["file_ids"]),
                    "n_files": len(meta["file_ids"]),
                })
        rows.sort(key=lambda r: (-r["n_bundles"], -r["n_files"]))
        connectors[etype] = rows

    # Save entity index (serialize sets to sorted lists)
    entity_out = {
        etype: [
            {
                "value": val,
                "n_bundles": len(m["bundles"]),
                "n_files": len(m["file_ids"]),
                "bundles": sorted(m["bundles"]),
                "file_ids": sorted(m["file_ids"]),
            }
            for val, m in sorted(
                vals.items(),
                key=lambda kv: (-len(kv[1]["bundles"]), -len(kv[1]["file_ids"])),
            )
        ]
        for etype, vals in index.items()
    }
    ENTITIES_JSON.write_text(
        json.dumps(entity_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[analyze] wrote {ENTITIES_JSON}")

    # ---- Human-readable cross-bundle report
    md: list = [
        "# Drive cross-bundle connection report",
        "",
        f"- Analyzed: {done} text-bearing files",
        f"- Source: top {len(text_files)} curated files by score",
        f"- Cross-bundle threshold: entity appears in >= "
        f"{args.min_cross_bundle} bundles",
        "",
    ]
    for etype in ("org", "person", "phone", "email",
                   "financial_account", "amount", "id_number", "gov_ref"):
        rows = connectors.get(etype, [])
        md.append(f"## {etype} — {len(rows)} cross-bundle connectors")
        md.append("")
        if not rows:
            md.append("_(none)_\n")
            continue
        md.append("| bundles | files | value |")
        md.append("|---:|---:|---|")
        for r in rows[:30]:
            v = r["value"][:80]
            md.append(f"| {r['n_bundles']} | {r['n_files']} | `{v}` |")
        md.append("")

    # ---- Refined curated list: rescore by connection density
    # Rule: a file's connection bonus = sum over entities in it of
    # (n_bundles - 1) * weight_by_type. Higher = more connective.
    type_weight = {
        "org": 6, "person": 5, "financial_account": 7,
        "email": 4, "phone": 4, "gov_ref": 2,
        "id_number": 3, "amount": 1,
    }
    refined: list = []
    for fid, info in file_entities.items():
        bonus = 0
        conn_details: list = []
        for etype, vals in info["entities"].items():
            for v in vals:
                nb = len(index[etype][v]["bundles"])
                if nb >= 2:
                    bonus += (nb - 1) * type_weight.get(etype, 1)
                    conn_details.append({
                        "type": etype, "value": v, "bundles": nb,
                    })
        # Pull original score from curated list (default 0)
        orig = next(
            (c for c in curated if c["id"] == fid), None)
        base_score = orig.get("score", 0) if orig else 0
        refined.append({
            "id": fid,
            "name": info["name"],
            "mime": info["mime"],
            "bundle": info["bundle"],
            "score": base_score,
            "connection_bonus": bonus,
            "final_score": base_score + bonus,
            "connections": conn_details,
        })
    refined.sort(key=lambda r: -r["final_score"])
    REFINED_JSON.write_text(
        json.dumps(refined, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[analyze] wrote {REFINED_JSON} ({len(refined)} files)")

    md.append("## Top 30 files by connection density")
    md.append("")
    md.append("| final | base | +bonus | bundle | file |")
    md.append("|---:|---:|---:|---|---|")
    for r in refined[:30]:
        md.append(
            f"| {r['final_score']} | {r['score']} | "
            f"+{r['connection_bonus']} | "
            f"`{r['bundle'][:30]}` | `{r['name'][:60]}` |"
        )
    CROSS_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[analyze] wrote {CROSS_MD}")

    # Console summary
    print("\n=== CROSS-BUNDLE SUMMARY ===")
    for etype in ("org", "person", "phone", "email",
                   "financial_account", "gov_ref"):
        rows = connectors.get(etype, [])
        print(f"  {etype:<18s} connectors : {len(rows)}")
        for r in rows[:3]:
            v = r["value"][:60]
            print(f"    ({r['n_bundles']} bundles, "
                  f"{r['n_files']} files) {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
