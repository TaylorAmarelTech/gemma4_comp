#!/usr/bin/env python3
"""Extract structured agency knowledge-facts from recruitment pages, build a
per-agency dossier, and search over the staged dossiers.

This is the extraction layer of the defensive recruitment pipeline:

    search/seed -> fetch -> EXTRACT FACTS (here) -> screen suspicious language
                -> verify licence -> propose-only dossier

`extract_facts(text)` is a pure, offline, deterministic extractor that pulls
the knowledge-facts a caseworker records about a recruiter: agency name(s),
licence-number claims, phone numbers, emails, office addresses, named medical
clinics, job orders (position / destination / salary), and fee demands.

`build_dossier(items, registry_path)` composes those facts with the GREP
suspicious-language screen (scan_recruitment_text) and the licensed-agency
verification (agency_registry) into a per-page risk dossier.

`search_dossiers(query, dossiers)` is a local search over the staged result
set (full-text + structured filters like risk tier or licence status).

Defensive + propose-only: it analyses content YOU provide or pages YOU are
investigating, writes only to reports/agency_dossier/ (gitignored), mutates no
live knowledge, and treats every signal as advisory. The optional --url mode
uses the scanner's robots-respecting fetch; it is opt-in and capped.

Usage:
    python scripts/extract_agency_facts.py --dir saved_pages/ --registry data/agency_registry/sample_licensed_agencies.json
    python scripts/extract_agency_facts.py --text "Apply at ... 09171234567 ... medical at ABC Clinic"
    python scripts/extract_agency_facts.py --search "unlicensed" --from reports/agency_dossier/dossier_xxx.json
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

MAX_ITEM_CHARS = 40_000

# Destination countries / regions common in migrant-worker job orders.
_COUNTRIES = (
    "Saudi Arabia", "Saudi", "Qatar", "UAE", "United Arab Emirates", "Dubai",
    "Abu Dhabi", "Kuwait", "Bahrain", "Oman", "Lebanon", "Jordan", "Israel",
    "Hong Kong", "Taiwan", "Singapore", "Malaysia", "Japan", "South Korea",
    "Korea", "Brunei", "Canada", "Poland", "Romania", "United Kingdom", "UK",
    "Cyprus", "Maldives", "Australia", "New Zealand", "Russia", "Turkey",
)
_COUNTRY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _COUNTRIES) + r")\b")

_POSITIONS = (
    "domestic worker", "domestic helper", "household service worker", "maid",
    "caregiver", "caretaker", "nurse", "nursing aide", "cleaner", "housekeeper",
    "waiter", "waitress", "cook", "chef", "kitchen helper", "driver",
    "factory worker", "production worker", "welder", "fabricator", "mason",
    "carpenter", "electrician", "plumber", "steel fixer", "scaffolder",
    "fisher", "fisherman", "seafarer", "seaman", "crew", "security guard",
    "sales lady", "saleslady", "cashier", "barista", "beautician",
    "hotel staff", "room attendant", "construction worker", "laborer",
    "labourer", "farm worker", "picker", "packer", "operator",
)
_POSITION_RE = re.compile(r"\b(" + "|".join(re.escape(p) for p in _POSITIONS) + r")s?\b", re.I)

_CURRENCY_RE = re.compile(
    r"\b(?:USD|US\$|SAR|AED|QAR|KWD|BHD|OMR|HKD|SGD|TWD|JPY|KRW|CAD|PHP|P|PLN|"
    r"GBP|ILS|NIS|RM|MYR)\s?\$?\s?[\d,]{3,}(?:\.\d{2})?\b", re.I)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Phone shapes: international (+CC ...), PH mobile (09xx / +639xx), PH landline.
_PHONE_RES = (
    re.compile(r"\+\d{1,3}[\s.\-]?(?:\(?\d{1,4}\)?[\s.\-]?){1,4}\d{2,4}"),
    re.compile(r"\b0?9\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4}\b"),                # PH mobile
    re.compile(r"\(?0?\d{1,2}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{4}\b"),         # landline
    re.compile(r"\b(?:tel|phone|mobile|cell|contact|call|viber|whatsapp)\.?\s*"
               r":?\s*([+()\d][\d\s.\-()]{6,}\d)", re.I),
)

_LICENSE_RE = re.compile(
    r"\b(?:POEA|DMW|DOLE|DOH|GAMCA|MWO)[-/\s]?[A-Z0-9][A-Z0-9\-/]{2,}\b")

_AGENCY_NAME_RE = re.compile(
    r"\b([A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+){0,4}\s+"
    r"(?:Agency|Agencies|Manpower|Recruitment|Placement|Services|Solutions|"
    r"Workforce|Crewing|Enterprises|Corporation|Consultancy|International|"
    r"Overseas|Inc\.?|Corp\.?|Co\.?))\b")

_ADDRESS_RE = re.compile(
    r"((?:Unit|Rm\.?|Room|Suite|Flr\.?|Floor|\d+(?:st|nd|rd|th)?\s*[Ff]l(?:oor)?|"
    r"Bldg\.?|Building|Tower|No\.?)\s*[A-Za-z0-9\-,/ ]{0,60}?"
    r"(?:St\.?|Street|Ave\.?|Avenue|Road|Rd\.?|Blvd\.?|Boulevard|Brgy\.?|"
    r"Barangay|Cor\.?|Corner)[A-Za-z0-9\-,./ ]{0,50})")

# Named clinics: require a strong clinic noun at the end. "Medical" alone is
# too weak (it catches "<City>. Medical"), so it must be "Medical Clinic" /
# "Medical Center". A name token may not start at a sentence boundary.
_CLINIC_RE = re.compile(
    r"\b([A-Z][A-Za-z&\-]+(?:\s+[A-Z][A-Za-z&\-]+){0,4}\s+"
    r"(?:Clinic|Polyclinic|Diagnostics?|Diagnostic\s+Cent(?:er|re)|"
    r"Medical\s+(?:Clinic|Cent(?:er|re)|Services)|Laboratory|Hospital))\b")
_CLINIC_CUE_RE = re.compile(
    r"\b(GAMCA[- ]?accredited|pre[- ]?employment medical|medical exam|"
    r"fit[- ]to[- ]work|drug test)\b", re.I)

_FEE_RE = re.compile(
    r"\b((?:placement|recruitment|training|processing|medical|documentation|"
    r"orientation|membership|service|agency|deployment|visa)\s+fees?)\b", re.I)


def _strip_html(raw: str) -> str:
    no_script = re.sub(r"(?is)<(script|style|head|noscript)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?is)<[^>]+>", " ", no_script)
    return "\n".join(l.strip() for l in _html.unescape(text).splitlines() if l.strip())


def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        k = re.sub(r"\s+", " ", str(x)).strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return out


def _clean_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p)
    return p.strip() if 7 <= len(digits) <= 15 else ""


def _dedupe_phones(phones: list[str]) -> list[str]:
    """Drop fragments: a phone whose digit-string is contained in a longer
    kept one (the overlapping shape regexes produce sub-matches)."""
    uniq = _dedupe(phones)
    uniq.sort(key=lambda p: len(re.sub(r"\D", "", p)), reverse=True)
    kept: list[str] = []
    kept_digits: list[str] = []
    for p in uniq:
        d = re.sub(r"\D", "", p)
        if any(d in kd for kd in kept_digits):
            continue
        kept.append(p)
        kept_digits.append(d)
    # restore reading order (longest-first is fine, but stable by first seen)
    return kept


@dataclass
class AgencyFacts:
    agency_names: list[str] = field(default_factory=list)
    license_nos: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    medical_clinics: list[str] = field(default_factory=list)
    job_orders: list[dict] = field(default_factory=list)
    fee_mentions: list[str] = field(default_factory=list)


def extract_facts(text: str) -> AgencyFacts:
    """Pure, deterministic extraction of agency knowledge-facts from text."""
    t = (text or "")[:MAX_ITEM_CHARS]
    phones = []
    for rx in _PHONE_RES:
        for m in rx.finditer(t):
            cand = m.group(1) if rx.groups else m.group(0)
            cleaned = _clean_phone(cand)
            if cleaned:
                phones.append(cleaned)

    # job orders: parse per segment (a recruitment ad lists one order per
    # line/clause), so a position/salary never bleeds across orders.
    segments = re.split(r"[\n;]|(?<=\d)\.\s|(?<=month)\b|(?<=\))\s", t)
    job_orders = []
    for seg in segments:
        for cm in _COUNTRY_RE.finditer(seg):
            pos = _POSITION_RE.search(seg)
            sal = _CURRENCY_RE.search(seg)
            if pos or sal:
                job_orders.append({
                    "destination": cm.group(1),
                    "position": (pos.group(0) if pos else ""),
                    "salary": (sal.group(0) if sal else ""),
                })
    seen_jo, jo = set(), []
    for o in job_orders:
        key = (o["destination"].lower(), o["position"].lower(), o["salary"].lower())
        if key not in seen_jo:
            seen_jo.add(key)
            jo.append(o)

    clinics = list(_CLINIC_RE.findall(t))
    if not clinics:
        # no NAMED clinic, but a medical-exam requirement is itself a fact
        for cue in _dedupe(m.group(1) for m in _CLINIC_CUE_RE.finditer(t)):
            clinics.append(f"(medical-exam requirement: {cue})")

    return AgencyFacts(
        agency_names=_dedupe(_AGENCY_NAME_RE.findall(t))[:10],
        license_nos=_dedupe(_LICENSE_RE.findall(t))[:10],
        phones=_dedupe_phones(phones)[:15],
        emails=_dedupe(_EMAIL_RE.findall(t))[:15],
        addresses=_dedupe(_ADDRESS_RE.findall(t))[:10],
        medical_clinics=_dedupe(clinics)[:10],
        job_orders=jo[:25],
        fee_mentions=_dedupe(m.group(1) for m in _FEE_RE.finditer(t))[:15],
    )


def _load_module(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, str(_ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # frozen-dataclass exec_module needs this
    spec.loader.exec_module(mod)
    return mod


def build_dossier(items: list[dict], *, registry_path: str = "") -> list[dict]:
    """Per-page dossier: facts + suspicious-language scan + licence verdict."""
    scanmod = _load_module("scripts/scan_recruitment_text.py", "dc_scan_for_dossier")
    scan_result = scanmod.scan(items, registry_path=registry_path)
    rows_by_idx = {r["index"]: r for r in scan_result["items"]}
    dossiers = []
    for idx, item in enumerate(items):
        facts = extract_facts(item["text"])
        row = rows_by_idx.get(idx, {})
        agency_check = row.get("agency_check")
        red_agency = isinstance(agency_check, list) and any(
            c.get("status") in {"not_found", "licensed_red"} for c in agency_check)
        dossiers.append({
            "id": item.get("id", f"item_{idx}"),
            "facts": asdict(facts),
            "screen_status": row.get("status", "unknown"),
            "grep": row.get("grep", {}),
            "why": row.get("why", []),
            "agency_check": agency_check,
            "risk_tier": _risk_tier(row.get("status"), facts, red_agency),
        })
    return dossiers


def _risk_tier(screen_status: str, facts: AgencyFacts, red_agency: bool) -> str:
    if screen_status == "flagged" or red_agency:
        return "high"
    if screen_status == "review" or facts.fee_mentions:
        return "medium"
    return "low"


def search_dossiers(query: str, dossiers: list[dict], *, risk: str = "",
                    status: str = "") -> list[dict]:
    """Local search over staged dossiers: substring query + structured filters."""
    q = (query or "").lower().strip()
    out = []
    for d in dossiers:
        if risk and d.get("risk_tier") != risk:
            continue
        if status and isinstance(d.get("agency_check"), list):
            if not any(c.get("status") == status for c in d["agency_check"]):
                continue
        if q:
            blob = json.dumps(d, ensure_ascii=False).lower()
            if q not in blob:
                continue
        out.append(d)
    return out


def discover_candidates(query: str, *, max_results: int = 10, searcher=None) -> dict:
    """Find candidate recruitment pages to investigate (the 'searching' step).

    Uses the keyless DuckDuckGo WebSearchTool from duecare-llm-research-tools
    (PII-filtered before the query leaves the machine). Returns candidate URLs
    for the operator to REVIEW and then scrape with --url -- it never
    auto-fetches them. ``searcher`` is injectable for offline tests.
    """
    if searcher is None:
        for _src in (_ROOT / "packages").glob("*/src"):
            if str(_src) not in sys.path:
                sys.path.insert(0, str(_src))
        try:
            from duecare.research_tools.web_tools import WebSearchTool
            searcher = WebSearchTool(max_results=max_results)
        except Exception as exc:  # noqa: BLE001 -- discovery is optional
            return {"query": query, "ok": False,
                    "error": f"web search unavailable: {type(exc).__name__}: {exc}"[:200],
                    "candidates": []}
    try:
        res = searcher.search(query, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        return {"query": query, "ok": False,
                "error": f"{type(exc).__name__}: {exc}"[:200], "candidates": []}
    ok = bool(getattr(res, "success", True))
    items = getattr(res, "items", None) or (res.get("items") if isinstance(res, dict) else [])
    candidates = [{"title": it.get("title", ""), "url": it.get("url", ""),
                   "snippet": it.get("snippet", "")}
                  for it in items if it.get("url")]
    return {
        "query": query, "ok": ok,
        "error": getattr(res, "error", "") or "",
        "candidates": candidates,
        "note": ("Candidate URLs to REVIEW then scrape with --url; not "
                 "auto-fetched. Verify relevance + robots before fetching."),
    }


def _read_text_file(p: Path) -> str:
    raw = p.read_text(encoding="utf-8", errors="replace")
    return _strip_html(raw) if p.suffix.lower() in {".html", ".htm"} else raw


def _gather(args) -> list[dict]:
    items = []
    if args.text:
        items.append({"id": "inline", "text": args.text})
    for f in args.file or []:
        p = Path(f)
        if p.exists():
            items.append({"id": p.name, "text": _read_text_file(p)})
    if args.dir:
        d = Path(args.dir)
        for ext in ("*.txt", "*.md", "*.html", "*.htm", "*.json"):
            for p in sorted(d.glob(ext)):
                items.append({"id": str(p.relative_to(d)), "text": _read_text_file(p)})
    if args.url:
        scanmod = _load_module("scripts/scan_recruitment_text.py", "dc_scan_fetch")
        for u in args.url[:scanmod.MAX_URLS]:
            text, err = scanmod._fetch_url(u)
            if err:
                print(f"  skipped {u}: {err}", file=sys.stderr)
                continue
            items.append({"id": u, "text": text})
    return [{"id": it["id"], "text": it["text"]} for it in items if (it["text"] or "").strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text")
    ap.add_argument("--file", action="append")
    ap.add_argument("--dir")
    ap.add_argument("--url", action="append")
    ap.add_argument("--registry", default="", help="licensed-agency registry to verify against")
    ap.add_argument("--search", help="search over an existing dossier file (with --from)")
    ap.add_argument("--discover", help="find candidate pages to investigate via keyless "
                                       "web search (returns URLs to review, never auto-fetches)")
    ap.add_argument("--from", dest="from_file", help="dossier JSON to --search")
    ap.add_argument("--risk", default="", help="filter --search by risk tier (high/medium/low)")
    ap.add_argument("--out", default=str(_ROOT / "reports" / "agency_dossier"))
    args = ap.parse_args(argv)

    if args.discover is not None:
        out = discover_candidates(args.discover)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if out["ok"] else 2

    if args.search is not None:
        if not args.from_file:
            ap.error("--search requires --from <dossier.json>")
        data = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
        dossiers = data.get("dossiers", data) if isinstance(data, dict) else data
        hits = search_dossiers(args.search, dossiers, risk=args.risk)
        print(json.dumps({"query": args.search, "n_hits": len(hits), "hits": hits},
                         indent=2, ensure_ascii=False))
        return 0

    if not any([args.text, args.file, args.dir, args.url]):
        ap.error("provide --text / --file / --dir / --url (or --search --from)")
    items = _gather(args)
    if not items:
        print("no items gathered", file=sys.stderr)
        return 1
    dossiers = build_dossier(items, registry_path=args.registry)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = hashlib.sha256("".join(sorted(d["id"] for d in dossiers)).encode()).hexdigest()[:12]
    payload = {"n_dossiers": len(dossiers),
               "risk_counts": {t: sum(1 for d in dossiers if d["risk_tier"] == t)
                               for t in ("high", "medium", "low")},
               "dossiers": dossiers}
    out = out_dir / f"dossier_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    rc = payload["risk_counts"]
    print(f"built {len(dossiers)} dossier(s): {rc['high']} high / {rc['medium']} medium / "
          f"{rc['low']} low risk", file=sys.stderr)
    print(f"-> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
