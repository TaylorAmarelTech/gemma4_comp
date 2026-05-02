#!/usr/bin/env python3
"""Curate a high-quality public test set for the Gemma 4 multimodal
document classifier.

Pipeline (all local; no GPU; single-machine):

  1. Pull candidate filenames from the Wikimedia Commons categories
     used by the deliverable (with one level of subcategory recursion).
     Optionally also walk a list of Google Drive folders.
  2. Download each candidate to a local cache (with polite throttling
     and retries).
  3. Run cheap heuristics on every file: image dimensions, file size,
     OCR text length and language, modern-vs-historical vocabulary
     score, in-domain keyword voting, MRZ presence, regex matches for
     amounts / phones / passport numbers / case numbers.
  4. Score each file. Drop noise (illegible, tiny, historical clutter,
     wrong-modality images). Keep the top N per category to hit a
     budget of `--max-total` files (default 500), distributed across
     `--max-per-category`.
  5. Write `data/curated_test_set.json` in the format the deliverable's
     `MM_FETCH_LIST` env var expects, plus a Markdown summary report.

Usage:

  python scripts/curate_multimodal_test_set.py \
      --cache-dir data/curation_cache \
      --out data/curated_test_set.json \
      --report data/curated_test_set_report.md \
      --max-total 500 \
      --max-per-category 60 \
      --per-category-fetch 25

When the run finishes, the deliverable can use the curated list with:

  MM_FETCH_LIST=data/curated_test_set.json \
  MM_FETCH_CURATED=0 \
  MM_FETCH_PER_CATEGORY=0 \
  python raw_python/gemma4_multimodal_with_rag_grep_v1.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_python"
sys.path.insert(0, str(RAW))

# Reuse helpers + category map from the fetcher module
from multimodal_fetch_public_samples import (  # type: ignore
    CURATED_SOURCES,
    WIKIMEDIA_CATEGORY_MAP,
    _wm,
    _wm_api_category_files,
    _wm_api_search_files,
    _wm_api_file_categories,
    _sanitize_filename,
)


# =============================================================================
#  HEURISTIC SCORING
# =============================================================================
# Words that strongly indicate a HISTORICAL artifact (1700-1900). Files
# whose filename or OCR text matches these are heavily penalized.
_HISTORICAL_WORDS = (
    "16", "17", "18",                        # year prefixes
    "bundesarchiv", "honorowy", "swiadek",   # archival fond names
    "Akte", "akte", "geboorte", "naissance",
    "bapt", "baptism", "Bapt",
    "indenture", "circa",
    "1843", "1850", "1866", "1873", "1875",
    "1899", "1875.03", "1792",
)

# Words that indicate a MODERN, in-domain doc. Big bonus.
_MODERN_INDOMAIN = {
    "passport_page": (
        "passport", "biodata", "biometric", "MRZ",
        "Republic", "Federation",
    ),
    "id_card": (
        "national id", "iqama", "labor card", "work permit",
        "residence", "tazkira", "carnet", "licence", "license",
        "driver",
    ),
    "visa_stamp": (
        "visa", "entry", "exit", "consulate", "embassy",
        "validity", "duration", "single entry", "multiple",
    ),
    "receipt_remittance": (
        "remittance", "MoneyGram", "Western Union", "wire",
        "transfer", "amount sent", "received", "receipt",
        "ATM", "exchange",
    ),
    "receipt_recruitment_fee": (
        "placement", "agency fee", "service charge",
        "recruitment", "POEA", "DMW", "BP2MI",
    ),
    "contract_employment": (
        "contract", "employer", "employee", "salary",
        "wage", "kafala", "domestic worker", "indentured",
    ),
    "contract_recruitment": (
        "recruitment agreement", "manning agency",
    ),
    "pdos_certificate": (
        "PDOS", "pre-departure", "POEA", "DMW", "DOFE",
    ),
    "training_certificate": (
        "certificate", "diploma", "completion", "training",
        "course", "vocational",
    ),
    "complaint_form": (
        "complaint", "grievance", "incident", "case no",
        "respondent", "complainant",
    ),
    "job_posting": (
        "wanted", "hiring", "now hiring", "applicants",
        "salary", "vacancy", "apply",
    ),
    "hotline_poster": (
        "hotline", "report", "trafficking", "victim",
        "1-888", "helpline", "free call",
    ),
    "chat_screenshot": (
        "WhatsApp", "Telegram", "Viber", "online", "typing",
        "delivered", "read",
    ),
}

# Country/corridor names — bonus when present (signals a real intake doc).
_CORRIDOR_WORDS = (
    "Philippines", "Filipino", "Filipina",
    "Indonesia", "Indonesian",
    "Nepal", "Nepali", "Nepalese",
    "Bangladesh", "Bangladeshi",
    "Sri Lanka", "Sri Lankan",
    "Pakistan", "Pakistani",
    "India", "Indian",
    "Saudi Arabia", "Saudi", "KSA",
    "UAE", "Emirates", "Dubai", "Abu Dhabi",
    "Qatar", "Qatari",
    "Kuwait", "Kuwaiti",
    "Oman", "Bahrain", "Hong Kong", "Singapore",
    "Malaysia", "Malaysian",
)

# OWASP-style polite UA + standard timeout.
_UA = (
    "duecare-curate/1.0 "
    "(https://github.com/TaylorAmarelTech/gemma4_comp; "
    "contact: research@duecare.example)"
)


def _sanitize_truncate(name: str, max_stem: int = 100) -> str:
    n = _sanitize_filename(name)
    stem, _, ext = n.rpartition(".")
    if stem and len(stem) > max_stem:
        stem = stem[:max_stem]
    return f"{stem}.{ext}" if ext else n[:max_stem]


def _http_get(url: str, dest: Path, timeout: int = 30,
              polite_delay: float = 0.6,
              max_retries: int = 3) -> Optional[Path]:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "image/*,application/pdf,*/*;q=0.8",
    })
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        time.sleep(polite_delay)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if not data:
                return None
            dest.write_bytes(data)
            return dest
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < max_retries:
                wait = backoff ** attempt
                print(f"    throttled {e.code}, sleeping {wait:.1f}s")
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} {url}")
            return None
        except Exception as e:
            print(f"    FAIL ({type(e).__name__}: {e}) {url}")
            return None
    return None


# =============================================================================
#  Image / OCR analysis (graceful degradation if libs missing)
# =============================================================================
_PIL_AVAILABLE = True
try:
    from PIL import Image  # type: ignore
except Exception:
    _PIL_AVAILABLE = False
    Image = None  # type: ignore

_TESS_AVAILABLE = True
try:
    import pytesseract  # type: ignore
except Exception:
    _TESS_AVAILABLE = False
    pytesseract = None  # type: ignore

_PDFIUM_AVAILABLE = True
try:
    import pypdfium2 as pdfium  # type: ignore
except Exception:
    _PDFIUM_AVAILABLE = False
    pdfium = None  # type: ignore


def _open_first_image(path: Path) -> "Image.Image | None":
    if not _PIL_AVAILABLE:
        return None
    try:
        if path.suffix.lower() == ".pdf":
            if not _PDFIUM_AVAILABLE:
                return None
            doc = pdfium.PdfDocument(str(path))
            if len(doc) == 0:
                return None
            page = doc[0]
            pil = page.render(scale=1.5).to_pil().convert("RGB")
            doc.close()
            return pil
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def _ocr(img: "Image.Image", langs: str = "eng") -> str:
    if not _TESS_AVAILABLE or img is None:
        return ""
    try:
        return pytesseract.image_to_string(
            img, lang=langs, config="--psm 6")[:4000]
    except Exception:
        return ""


@dataclass
class CandidateScore:
    url: str
    category: str
    source: str
    license: str
    attribution: str
    local_path: str
    bytes: int
    width: int = 0
    height: int = 0
    ocr_chars: int = 0
    ocr_text: str = ""
    score: float = 0.0
    rejection: str = ""
    signals: list = None  # type: ignore[assignment]

    def to_manifest_entry(self) -> dict:
        return {
            "url": self.url,
            "category": self.category,
            "source": self.source,
            "license": self.license,
            "attribution": self.attribution,
            "score": round(float(self.score), 1),
            "signals": list(self.signals or []),
        }


def _score(c: CandidateScore) -> CandidateScore:
    sig = []
    score = 0.0

    # Hard filters
    if c.bytes < 5_000:
        c.rejection = "too small (<5KB)"
        c.score = -100
        c.signals = ["tiny"]
        return c
    if c.bytes > 12_000_000:
        c.rejection = "too large (>12MB)"
        c.score = -100
        c.signals = ["huge"]
        return c
    if c.width and (c.width < 280 or c.height < 280):
        c.rejection = f"low res {c.width}x{c.height}"
        c.score = -100
        c.signals = ["low_res"]
        return c

    # OCR + filename combined haystack (case insensitive)
    name = Path(c.local_path).name.lower()
    text_lower = (c.ocr_text or "").lower()
    haystack = name + " " + text_lower

    # Historical / archival penalty
    hits_hist = sum(1 for w in _HISTORICAL_WORDS
                    if w.lower() in haystack)
    if hits_hist:
        score -= 8 * hits_hist
        sig.append(f"historical-{hits_hist}")

    # Modern in-domain keywords (per target category)
    modern_words = _MODERN_INDOMAIN.get(c.category, ())
    hits_mod = sum(1 for w in modern_words
                    if w.lower() in haystack)
    if hits_mod:
        score += 6 * hits_mod
        sig.append(f"in_domain-{hits_mod}")

    # Corridor signals
    hits_corr = sum(1 for w in _CORRIDOR_WORDS
                    if w.lower() in haystack)
    if hits_corr:
        score += 4 * min(hits_corr, 3)
        sig.append(f"corridor-{hits_corr}")

    # OCR readability bonus (signal that the doc has text content)
    if c.ocr_chars >= 200:
        score += 5
        sig.append("ocr_dense")
    elif c.ocr_chars >= 50:
        score += 2
        sig.append("ocr_some")
    else:
        score -= 1
        sig.append("ocr_sparse")

    # MRZ pattern hint (passport/id)
    if "<<" in c.ocr_text and c.category in (
            "passport_page", "id_card", "visa_stamp"):
        score += 8
        sig.append("mrz")

    # Aspect ratio plausibility (most NGO docs are roughly 4:3 to 1:1.5)
    if c.width and c.height:
        ar = c.width / max(1, c.height)
        if 0.5 < ar < 2.5:
            score += 1
        else:
            score -= 2
            sig.append(f"odd_ar-{ar:.2f}")

    # Filename clearly says "test" / "sample" / "blank" / "template"
    for w in ("sample", "template", "blank", "model_contract",
              "specimen"):
        if w in name:
            score += 4
            sig.append(f"sample:{w}")
            break

    c.score = score
    c.signals = sig
    return c


# =============================================================================
#  HARVEST
# =============================================================================
def _wikimedia_candidates(per_category: int) -> list[dict]:
    out: list[dict] = []
    seen_urls: set = set()
    for row in WIKIMEDIA_CATEGORY_MAP:
        if len(row) == 3:
            cat, our_cat, recurse = row
        else:
            cat, our_cat = row  # type: ignore[misc]
            recurse = False
        files = _wm_api_category_files(
            cat, limit=per_category, recurse_subcats=recurse)
        kept = 0
        for fname in files:
            url = _wm(fname)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            out.append({
                "url": url,
                "category": our_cat,
                "source": f"Wikimedia Commons / Category:{cat}",
                "license": "see file page on Wikimedia Commons",
                "attribution": (
                    f"Wikimedia Commons contributors, '{fname}' "
                    f"-- auto-pulled from Category:{cat}"
                ),
            })
            kept += 1
        print(f"  [wm] Category:{cat:<40s} -> +{kept:2d} ({our_cat})")
    return out


def _curated_candidates() -> list[dict]:
    return [
        {
            "url": e["url"],
            "category": e["category"],
            "source": e.get("source", "curated"),
            "license": e.get("license", "?"),
            "attribution": e.get("attribution", ""),
        }
        for e in CURATED_SOURCES
    ]


# Targeted full-text searches against Commons File: namespace. Each tuple
# is (search_query, our_category, max_results). Tuned to fill in the
# under-represented document types from the first curation pass.
_WIKIMEDIA_KEYWORD_SEARCHES: list[tuple[str, str, int]] = [
    # ---- passport pages: corridor-specific biodata pages ----
    ("Philippines passport biodata",        "passport_page",       12),
    ("Indonesia passport biodata",          "passport_page",       12),
    ("Nepal passport biodata",              "passport_page",       12),
    ("Bangladesh passport biodata",         "passport_page",        8),
    ("Sri Lanka passport biodata",          "passport_page",        8),
    ("India passport biodata",              "passport_page",        8),
    ("Pakistan passport biodata",           "passport_page",        8),
    ("biometric passport data page",        "passport_page",       12),
    # ---- visa stamps for destination countries ----
    ("Saudi Arabia work visa stamp",        "visa_stamp",          12),
    ("UAE residence visa stamp",            "visa_stamp",          12),
    ("Qatar visa stamp passport",           "visa_stamp",          10),
    ("Kuwait visa stamp",                   "visa_stamp",           8),
    ("Hong Kong visa stamp",                "visa_stamp",           8),
    ("Singapore work visa",                 "visa_stamp",           8),
    ("Malaysia visa stamp passport",        "visa_stamp",           8),
    # ---- IDs and labor permits ----
    ("Saudi iqama residence permit",        "id_card",             10),
    ("UAE Emirates ID card",                "id_card",             10),
    ("Qatar residence permit",              "id_card",              8),
    ("Kuwait civil ID",                     "id_card",              8),
    ("Philippines OWWA ID card",            "id_card",              6),
    ("Hong Kong identity card",             "id_card",              8),
    # ---- contracts and recruitment paperwork ----
    ("standard employment contract domestic worker",
                                            "contract_employment", 12),
    ("kafala labor contract",               "contract_employment",  8),
    ("POEA standard employment contract",   "contract_employment",  8),
    ("recruitment agency contract migrant", "contract_recruitment",10),
    ("manning agency contract seafarer",    "contract_recruitment", 8),
    # ---- recruitment-fee receipts ----
    ("recruitment agency receipt fee",      "receipt_recruitment_fee", 10),
    ("placement fee receipt migrant worker","receipt_recruitment_fee", 10),
    ("medical exam receipt OFW",            "receipt_recruitment_fee",  6),
    # ---- pre-departure orientation certificates ----
    ("PDOS certificate Philippines",        "pdos_certificate",    10),
    ("DMW pre-departure orientation",       "pdos_certificate",     6),
    ("BP2MI pre-departure",                 "pdos_certificate",     6),
    ("DOFE Nepal pre-departure orientation","pdos_certificate",     6),
    # ---- training / vocational certificates ----
    ("vocational training certificate worker",
                                            "training_certificate",10),
    ("TESDA certificate Philippines",       "training_certificate", 8),
    ("caregiver training certificate",      "training_certificate", 6),
    ("welder certification certificate",    "training_certificate", 6),
    # ---- complaint / grievance forms ----
    ("complaint form labor migrant",        "complaint_form",      10),
    ("grievance form worker",               "complaint_form",       8),
    ("incident report form",                "complaint_form",       6),
    ("affidavit complaint trafficking",     "complaint_form",       6),
    # ---- hotline posters / awareness ----
    ("human trafficking hotline poster",    "hotline_poster",      10),
    ("anti-trafficking awareness poster",   "hotline_poster",      10),
    ("National Human Trafficking Hotline poster",
                                            "hotline_poster",       6),
    ("Polaris Project poster",              "hotline_poster",       4),
    ("modern slavery helpline poster",      "hotline_poster",       6),
    # ---- job postings / classified ads ----
    ("classified ads newspaper job",        "job_posting",         10),
    ("hiring poster recruitment",           "job_posting",          8),
    ("now hiring sign",                     "job_posting",          6),
    ("recruitment poster overseas worker",  "job_posting",          8),
    # ---- remittance / money transfer ----
    ("Western Union receipt customer",      "receipt_remittance",  10),
    ("MoneyGram receipt slip",              "receipt_remittance",   8),
    ("GCash transfer receipt",              "receipt_remittance",   6),
    ("bank wire transfer receipt",          "receipt_remittance",   8),
    # ---- chat / coercion evidence ----
    ("WhatsApp screenshot conversation",    "chat_screenshot",     10),
    ("Telegram chat screenshot",            "chat_screenshot",      8),
    ("SMS text message screenshot",         "chat_screenshot",      8),
    ("Viber chat screenshot",               "chat_screenshot",      6),
    # ---- expanded passport corridor coverage ----
    ("Filipino passport bio page",          "passport_page",       10),
    ("OFW passport biodata",                "passport_page",        8),
    ("Vietnamese passport bio page",        "passport_page",        8),
    ("Myanmar passport biodata",            "passport_page",        8),
    ("Cambodian passport biodata",          "passport_page",        6),
    ("Ethiopian passport biodata",          "passport_page",        6),
    ("Kenyan passport biodata",             "passport_page",        6),
    ("Ugandan passport biodata",            "passport_page",        6),
    ("Ghanaian passport biodata",           "passport_page",        6),
    ("Nigerian passport biodata page",      "passport_page",        8),
    ("biometric passport identity page",    "passport_page",       12),
    ("passport observation page stamps",    "passport_page",        8),
    # ---- expanded visa corridor coverage ----
    ("Bahrain residence visa",              "visa_stamp",           8),
    ("Oman work visa",                      "visa_stamp",           8),
    ("Lebanon work visa",                   "visa_stamp",           6),
    ("Israel work visa",                    "visa_stamp",           6),
    ("Cyprus work visa",                    "visa_stamp",           6),
    ("Korea EPS visa",                      "visa_stamp",           6),
    ("Japan SSW visa",                      "visa_stamp",           6),
    ("Schengen visa sticker",               "visa_stamp",           8),
    ("UK work visa vignette",               "visa_stamp",           6),
    # ---- expanded ID / labor permits ----
    ("Bahrain CPR card",                    "id_card",              6),
    ("Oman resident card",                  "id_card",              6),
    ("Lebanon work permit",                 "id_card",              6),
    ("Singapore work permit S Pass",        "id_card",              8),
    ("Malaysia my kad card",                "id_card",              6),
    ("Thailand work permit",                "id_card",              6),
    ("Korea ARC alien registration card",   "id_card",              6),
    ("Taiwan ARC alien resident",           "id_card",              6),
    ("Israel teudat zehut",                 "id_card",              6),
    ("Lebanese national ID",                "id_card",              6),
    ("Cypriot ID card",                     "id_card",              6),
    ("Brazilian RG identity card",          "id_card",              6),
    ("Mexican INE voting card",             "id_card",              6),
    # ---- expanded contract coverage ----
    ("seafarer employment agreement",       "contract_employment", 10),
    ("MLC seafarer contract",               "contract_employment",  6),
    ("agriculture H-2A contract",           "contract_employment",  6),
    ("hospitality H-2B contract",           "contract_employment",  6),
    ("nanny contract employment",           "contract_employment",  6),
    ("housekeeper contract Saudi",          "contract_employment",  6),
    ("construction worker contract Gulf",   "contract_employment",  8),
    # ---- chat evidence: more apps and languages ----
    ("Messenger Facebook chat screenshot",  "chat_screenshot",      8),
    ("WeChat screenshot conversation",      "chat_screenshot",      6),
    ("Line chat screenshot",                "chat_screenshot",      6),
    ("Signal app screenshot",               "chat_screenshot",      6),
    # ---- remittance: more channels and corridors ----
    ("Remitly receipt remittance",          "receipt_remittance",   6),
    ("Wise transfer receipt",               "receipt_remittance",   6),
    ("Xoom remittance receipt",             "receipt_remittance",   6),
    ("Cebuana Lhuillier remittance",        "receipt_remittance",   6),
    ("Palawan Express remittance",          "receipt_remittance",   6),
    ("LBC remittance",                      "receipt_remittance",   6),
    ("Hawala remittance receipt",           "receipt_remittance",   4),
    ("ATM withdrawal receipt slip",         "receipt_remittance",   6),
    # ---- training / vocational, more sources ----
    ("seafarer training certificate STCW",  "training_certificate", 8),
    ("first aid certificate",               "training_certificate", 6),
    ("food handler certificate",            "training_certificate", 6),
    ("forklift operator certificate",       "training_certificate", 6),
    ("language proficiency certificate",    "training_certificate", 6),
    # ---- complaint / grievance, broaden ----
    ("EEOC complaint form",                 "complaint_form",       6),
    ("OSHA complaint form",                 "complaint_form",       6),
    ("DOL wage hour complaint form",        "complaint_form",       6),
    ("ILO complaint form labor",            "complaint_form",       6),
    ("trafficking victim affidavit",        "complaint_form",       6),
    # ---- hotline / awareness, government issuers ----
    ("Blue Campaign hotline poster",        "hotline_poster",       6),
    ("DHS human trafficking awareness",     "hotline_poster",       6),
    ("Truckers Against Trafficking poster", "hotline_poster",       4),
    ("Salvation Army anti-trafficking",     "hotline_poster",       4),
    # ---- job postings: more variety ----
    ("help wanted sign window",             "job_posting",          8),
    ("recruitment poster overseas labor",   "job_posting",          8),
    ("manpower agency poster",              "job_posting",          6),
    ("housemaid wanted poster",             "job_posting",          6),
    ("nurse hiring poster",                 "job_posting",          6),
]


def _wikimedia_keyword_candidates(
    max_per_query_override: Optional[int] = None,
) -> list[dict]:
    """Run the targeted full-text searches and return candidate
    entries. Dedup-by-filename; per-query throttle pause."""
    out: list[dict] = []
    seen_fnames: set = set()
    for query, our_cat, default_n in _WIKIMEDIA_KEYWORD_SEARCHES:
        n = max_per_query_override or default_n
        try:
            files = _wm_api_search_files(query, limit=n)
        except Exception as e:
            print(f"  [kw] '{query[:48]}' FAIL ({type(e).__name__})")
            files = []
        kept = 0
        for fname in files:
            if fname in seen_fnames:
                continue
            seen_fnames.add(fname)
            out.append({
                "url": _wm(fname),
                "category": our_cat,
                "source": f"Wikimedia Commons / search:{query}",
                "license": "see file page on Wikimedia Commons",
                "attribution": (
                    f"Wikimedia Commons contributors, '{fname}' "
                    f"-- search hit for '{query}'"
                ),
            })
            kept += 1
        time.sleep(0.4)  # be polite to the API
        print(f"  [kw] {query[:48]:<48s} -> +{kept:2d} ({our_cat})")
    return out


# Categories whose siblings we always want to pull together (case
# bundles). When we encounter a hit in one of these patterns we will
# fetch the rest of the file list from that exact category, capped.
_SIBLING_CATEGORY_PATTERNS = (
    "documents of ",          # "Category:Documents of <Person>"
    "passport of ",           # "Category:Passport of <Person>"
    "passports of ",          # "Category:Passports of <Country>"
    "id card of ",
    "identity documents of ",
    "case file ",
    "trial of ",
)


def _is_sibling_pattern(cat_name: str) -> bool:
    low = cat_name.lower()
    return any(low.startswith(p) for p in _SIBLING_CATEGORY_PATTERNS)


def _expand_sibling_folders(seed_candidates: list[dict],
                             max_siblings: int = 8,
                             max_seeds: int = 30) -> list[dict]:
    """For a sample of seed candidates, look up their Commons categories
    and pull sibling files from any category that looks like a
    person/case bundle. Returns NEW candidate entries (not already in
    seed_candidates).
    """
    seen_urls = {e.get("url") for e in seed_candidates}
    out: list[dict] = []
    examined_cats: set = set()
    # Sample uniformly across our_category to get diverse seeds
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for e in seed_candidates:
        by_cat[e["category"]].append(e)
    seeds: list[dict] = []
    while len(seeds) < max_seeds:
        progress = False
        for cat, items in by_cat.items():
            if items:
                seeds.append(items.pop(0))
                progress = True
                if len(seeds) >= max_seeds:
                    break
        if not progress:
            break
    print(f"  [sib] examining {len(seeds)} seeds for case bundles")
    for seed in seeds:
        url = seed["url"]
        # extract bare filename from Special:FilePath URL
        try:
            tail = url.split("/Special:FilePath/")[1]
            fname = urllib.parse.unquote(tail.split("?")[0])
        except Exception:
            continue
        try:
            cats = _wm_api_file_categories(fname)
        except Exception:
            cats = []
        time.sleep(0.3)
        bundle_cats = [c for c in cats if _is_sibling_pattern(c)]
        for bc in bundle_cats:
            if bc in examined_cats:
                continue
            examined_cats.add(bc)
            try:
                siblings = _wm_api_category_files(
                    bc, limit=max_siblings)
            except Exception:
                siblings = []
            time.sleep(0.3)
            kept = 0
            for sf in siblings:
                surl = _wm(sf)
                if surl in seen_urls:
                    continue
                seen_urls.add(surl)
                # heuristic: keep the seed's category for siblings
                out.append({
                    "url": surl,
                    "category": seed["category"],
                    "source": f"Wikimedia Commons / Category:{bc}",
                    "license": "see file page on Wikimedia Commons",
                    "attribution": (
                        f"Wikimedia Commons contributors, '{sf}' "
                        f"-- sibling in Category:{bc}"
                    ),
                })
                kept += 1
            print(f"  [sib] Category:{bc[:50]:<50s} -> +{kept:2d}")
    return out


# =============================================================================
#  GOOGLE DRIVE INGEST
# =============================================================================
# Filename keywords that map a Drive file to one of our doc categories.
# These run AFTER the Drive walk and only label the file -- the score()
# function then judges whether to keep it.
_DRIVE_FILENAME_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("passport", "biodata", "biopage", "bio_page"),  "passport_page"),
    (("visa", "vignette", "stamp"),                    "visa_stamp"),
    (("iqama", "emirates_id", "national_id",
      "id_card", "drivers_license", "drivinglicense",
      "labor_card", "work_permit", "residence"),       "id_card"),
    (("contract", "kafala", "employment_agreement",
      "agreement", "offer_letter"),                    "contract_employment"),
    (("recruitment_contract", "manning"),              "contract_recruitment"),
    (("receipt", "remittance", "moneygram",
      "western_union", "wire", "transfer", "gcash"),   "receipt_remittance"),
    (("placement_fee", "agency_fee",
      "recruitment_fee"),                              "receipt_recruitment_fee"),
    (("pdos", "predeparture", "pre-departure"),        "pdos_certificate"),
    (("training", "certificate", "diploma",
      "completion", "tesda", "stcw"),                  "training_certificate"),
    (("complaint", "grievance", "affidavit",
      "incident_report"),                              "complaint_form"),
    (("hotline", "awareness_poster",
      "anti_trafficking", "antislavery"),              "hotline_poster"),
    (("job_posting", "hiring", "vacancy",
      "help_wanted"),                                  "job_posting"),
    (("whatsapp", "telegram", "viber", "wechat",
      "messenger", "sms_screenshot",
      "chat_screenshot"),                              "chat_screenshot"),
]


def _classify_drive_filename(name: str, default_cat: str) -> str:
    low = name.lower().replace(" ", "_").replace("-", "_")
    for keys, cat in _DRIVE_FILENAME_HINTS:
        if any(k in low for k in keys):
            return cat
    return default_cat


def _drive_walk_to_candidates(folders_csv: str, drive_cache: str,
                                default_cat: str) -> list[dict]:
    """Use the build script's _gdrive_classify + _gdrive_walk_recursive
    to download all public Drive files, then walk drive_cache and emit
    candidate entries (one per local file). The 'url' is recorded as
    a gdrive:// URI so the final manifest tells the consumer the file
    came from a non-HTTP source.
    """
    sys.path.insert(0, str(ROOT / "raw_python"))
    try:
        # Import lazily; build script bootstraps gdown
        from _build_multimodal_with_rag_grep import (  # type: ignore
            _gdrive_classify,
            _gdrive_walk_recursive,
            _safe_basename,
        )
        import gdown  # type: ignore
    except Exception as e:
        print(f"[drive] unavailable: {type(e).__name__}: {e}")
        return []

    drive_root = Path(drive_cache).resolve()
    drive_root.mkdir(parents=True, exist_ok=True)

    raw_items = [s.strip() for s in folders_csv.split(",") if s.strip()]
    print(f"[drive] {len(raw_items)} Drive URL(s) to ingest")
    for idx, raw in enumerate(raw_items):
        kind, gid = _gdrive_classify(raw)
        sub = drive_root / f"item_{idx:02d}_{kind}_{gid[:8]}"
        sub.mkdir(parents=True, exist_ok=True)
        try:
            if kind == "folder":
                n = _gdrive_walk_recursive(gid, str(sub), max_depth=6)
                print(f"  [drive] folder {gid} -> {n} files")
            else:  # file
                out_path = sub / _safe_basename(f"file_{gid}")
                if not out_path.exists():
                    gdown.download(id=gid, output=str(out_path),
                                   quiet=True, fuzzy=True)
                print(f"  [drive] file {gid} -> {sub.name}")
        except Exception as e:
            print(f"  [drive] FAIL {raw[:60]} "
                  f"({type(e).__name__}: {e})")

    # Walk drive_root and emit one candidate per file.
    out: list[dict] = []
    for p in drive_root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp",
                                    ".tif", ".tiff", ".gif", ".pdf"):
            continue
        if p.stat().st_size < 5_000:
            continue
        cat = _classify_drive_filename(p.name, default_cat)
        # Use the local file path as both url and source -- the
        # downloader will see the file already exists in cache and
        # will skip the HTTP fetch.
        out.append({
            "url": p.as_uri(),
            "category": cat,
            "source": f"Google Drive / {p.parent.name}",
            "license": "user-provided (Google Drive)",
            "attribution": (
                f"Google Drive ingestion, '{p.name}' "
                f"from folder '{p.parent.name}'"
            ),
            "_local_path": str(p),  # downloader honors this
        })
    print(f"[drive] discovered {len(out)} files in cache")
    return out


# =============================================================================
#  DRIVER
# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", default="data/curation_cache",
                    help="Local cache for downloaded candidates")
    ap.add_argument("--out", default="data/curated_test_set.json",
                    help="Output JSON manifest (MM_FETCH_LIST format)")
    ap.add_argument("--report", default="data/curated_test_set_report.md",
                    help="Markdown summary report")
    ap.add_argument("--max-total", type=int, default=500,
                    help="Hard cap on output entries (default 500; "
                         "bump to 10000 for max-scale runs)")
    ap.add_argument("--max-per-category", type=int, default=60,
                    help="Cap per category in the final manifest")
    ap.add_argument("--per-category-fetch", type=int, default=25,
                    help="Wikimedia files to fetch per category")
    ap.add_argument("--ocr-langs", default="eng",
                    help="Tesseract language codes for triage OCR. "
                         "Use 'eng' to keep this fast; the deliverable "
                         "does the multilingual pass at run time.")
    ap.add_argument("--skip-curated", action="store_true",
                    help="Skip the 18 hand-curated entries (rare)")
    ap.add_argument("--min-score", type=float, default=0.0,
                    help="drop survivors with score < this value")
    ap.add_argument("--skip-wikimedia", action="store_true",
                    help="Skip the Wikimedia category harvest (rare)")
    ap.add_argument("--skip-keywords", action="store_true",
                    help="Skip the Wikimedia keyword-search harvest")
    ap.add_argument("--skip-siblings", action="store_true",
                    help="Skip the case-bundle (sibling-folder) pull")
    ap.add_argument("--keyword-per-query", type=int, default=0,
                    help="Override per-query keyword cap (0 = use built-in)")
    ap.add_argument("--sibling-seeds", type=int, default=30,
                    help="How many seed files to inspect for case bundles")
    ap.add_argument("--sibling-max", type=int, default=8,
                    help="Max files pulled from each case-bundle category")
    ap.add_argument("--workers", type=int, default=8,
                    help="Concurrent download workers (default 8)")
    ap.add_argument("--max-runtime-min", type=int, default=0,
                    help="Hard wall-clock cap in minutes for the "
                         "download+score phase (0 = unlimited)")
    ap.add_argument("--drive-folders", type=str, default="",
                    help="Comma-separated Google Drive folder URLs/IDs "
                         "or single-file URLs to ingest (uses gdown)")
    ap.add_argument("--drive-cache", type=str,
                    default="data/curation_cache_drive",
                    help="Local cache for Google Drive content")
    ap.add_argument("--drive-default-category", type=str,
                    default="unknown",
                    help="Category label for Drive files when filename "
                         "doesn't match a known doc-type pattern")
    args = ap.parse_args()

    cache = Path(args.cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    print(f"[curate] cache dir : {cache}")
    print(f"[curate] PIL  ok   : {_PIL_AVAILABLE}")
    print(f"[curate] tess ok   : {_TESS_AVAILABLE}")
    print(f"[curate] pdfium ok : {_PDFIUM_AVAILABLE}")

    # 1. Build candidate list
    candidates: list[dict] = []
    seen_urls: set = set()

    def _extend(label: str, batch: list[dict]) -> None:
        added = 0
        for e in batch:
            u = e.get("url")
            if not u or u in seen_urls:
                continue
            seen_urls.add(u)
            candidates.append(e)
            added += 1
        print(f"[curate] {label:<10s}: {added:4d} added "
              f"(of {len(batch):4d}); running total {len(candidates)}")

    if not args.skip_curated:
        _extend("curated", _curated_candidates())
    if not args.skip_wikimedia:
        _extend("wm-cat", _wikimedia_candidates(args.per_category_fetch))
    if not args.skip_keywords:
        print("\n[curate] keyword search pass")
        kw_override = args.keyword_per_query or None
        _extend("wm-kw", _wikimedia_keyword_candidates(kw_override))
    if not args.skip_siblings and candidates:
        print("\n[curate] sibling-folder pass")
        sib = _expand_sibling_folders(
            candidates,
            max_siblings=args.sibling_max,
            max_seeds=args.sibling_seeds,
        )
        _extend("wm-sib", sib)
    if args.drive_folders:
        print("\n[curate] Google Drive ingestion pass")
        drive = _drive_walk_to_candidates(
            args.drive_folders,
            args.drive_cache,
            args.drive_default_category,
        )
        _extend("drive", drive)

    print(f"[curate] total candidates: {len(candidates)}")
    if not candidates:
        print("[curate] no candidates; exiting")
        return 1

    # 2. Download + score (concurrent)
    scored: list[CandidateScore] = []
    by_cat = defaultdict(int)
    t0 = time.time()
    deadline = t0 + args.max_runtime_min * 60.0 \
        if args.max_runtime_min > 0 else None
    checkpoint_path = Path(args.out).resolve().with_suffix(".partial.json")

    def _download_one(entry: dict) -> Optional[CandidateScore]:
        cat = entry["category"]
        url = entry["url"]
        # Drive-ingested entries already point at a local file.
        local_override = entry.get("_local_path")
        if local_override:
            got = Path(local_override)
            if not got.exists() or got.stat().st_size == 0:
                return None
        else:
            fname = _sanitize_truncate(url)
            h = abs(hash(url)) % 0xFFFFFFFF
            local = cache / cat / f"{h:08x}_{fname}"
            # No polite delay inside threads -- pool size is the throttle.
            got = _http_get(url, local, polite_delay=0.0)
            if not got:
                return None
        size = got.stat().st_size
        cs = CandidateScore(
            url=url,
            category=cat,
            source=entry["source"],
            license=entry["license"],
            attribution=entry["attribution"],
            local_path=str(got),
            bytes=size,
        )
        img = _open_first_image(got)
        if img is not None:
            cs.width, cs.height = img.size
            cs.ocr_text = _ocr(img, langs=args.ocr_langs)
            cs.ocr_chars = len(cs.ocr_text)
        return _score(cs)

    workers = max(1, args.workers)
    print(f"[curate] downloading with {workers} workers, "
          f"runtime budget = "
          f"{args.max_runtime_min if args.max_runtime_min>0 else 'unlimited'} min")
    timed_out = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_one, e): i
                   for i, e in enumerate(candidates, 1)}
        completed = 0
        for fut in as_completed(futures):
            completed += 1
            try:
                cs = fut.result()
            except Exception as e:
                cs = None
                print(f"    worker exc: {type(e).__name__}: {e}")
            if cs is not None:
                scored.append(cs)
                by_cat[cs.category] += 1
            if completed % 50 == 0 or completed == len(candidates):
                elapsed = time.time() - t0
                rate = completed / max(1.0, elapsed)
                print(f"  [{completed:5d}/{len(candidates)}] "
                      f"{elapsed/60:.1f} min "
                      f"({rate:.1f}/s), {len(scored)} scored")
                # incremental checkpoint
                try:
                    checkpoint_path.write_text(
                        json.dumps(
                            [c.to_manifest_entry() for c in scored
                             if c.score >= args.min_score],
                            indent=2, ensure_ascii=False),
                        encoding="utf-8")
                except Exception:
                    pass
            if deadline and time.time() > deadline:
                timed_out = True
                print(f"  [curate] runtime budget reached "
                      f"({args.max_runtime_min} min); cancelling")
                for f in futures:
                    f.cancel()
                break
    if timed_out:
        print(f"[curate] processed {len(scored)} of "
              f"{len(candidates)} before timeout")

    # 3. Filter rejected, sort by score per category, apply caps
    survivors: list[CandidateScore] = [
        c for c in scored
        if c.score > -50 and c.score >= args.min_score
    ]
    rejected = len(scored) - len(survivors)
    print(f"\n[curate] downloaded {len(scored)}, "
          f"survivors {len(survivors)}, rejected {rejected}")

    by_cat_scored: dict[str, list[CandidateScore]] = defaultdict(list)
    for c in survivors:
        by_cat_scored[c.category].append(c)
    for cat in by_cat_scored:
        by_cat_scored[cat].sort(key=lambda c: c.score, reverse=True)

    final: list[CandidateScore] = []
    cat_counts: dict[str, int] = defaultdict(int)
    # Round-robin pull from sorted lists until budget exhausted
    while len(final) < args.max_total:
        progress = False
        for cat, items in by_cat_scored.items():
            if cat_counts[cat] >= args.max_per_category:
                continue
            if not items:
                continue
            final.append(items.pop(0))
            cat_counts[cat] += 1
            progress = True
            if len(final) >= args.max_total:
                break
        if not progress:
            break

    print(f"[curate] FINAL: {len(final)} files across "
          f"{len(cat_counts)} categories")
    for cat, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<28s} {n}")

    # 4. Emit manifest + report
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = [c.to_manifest_entry() for c in final]
    out_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\n[curate] manifest -> {out_path}")
    print(f"[curate] use with:  MM_FETCH_LIST={out_path} "
          f"MM_FETCH_CURATED=0 MM_FETCH_PER_CATEGORY=0")

    rep = Path(args.report).resolve()
    lines = [
        "# Duecare multimodal curated test set",
        "",
        f"- Total entries: {len(final)}",
        f"- Categories:    {len(cat_counts)}",
        f"- Cache dir:     `{cache}`",
        "",
        "## Per-category counts",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for cat, n in sorted(cat_counts.items()):
        lines.append(f"| `{cat}` | {n} |")

    lines.extend([
        "",
        "## Top 10 by score",
        "",
        "| Score | Category | Signals | URL |",
        "|---:|---|---|---|",
    ])
    for c in sorted(final, key=lambda x: -x.score)[:10]:
        sigs = ",".join((c.signals or [])[:5])
        lines.append(
            f"| {c.score:+.1f} | `{c.category}` | "
            f"{sigs} | <{c.url}> |")

    lines.extend([
        "",
        "## Bottom 10 (lowest-score survivors)",
        "",
        "| Score | Category | Signals | URL |",
        "|---:|---|---|---|",
    ])
    for c in sorted(final, key=lambda x: x.score)[:10]:
        sigs = ",".join((c.signals or [])[:5])
        lines.append(
            f"| {c.score:+.1f} | `{c.category}` | "
            f"{sigs} | <{c.url}> |")

    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[curate] report   -> {rep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
