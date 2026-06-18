#!/usr/bin/env python3
"""Entity screening engine -- match a name against every collected register.

This is the piece that makes the entity-intelligence pipeline a *tool*: given a
recruiter / employer / lender name off a worker's contract, it fuzzy-matches the
name across every entity record DueCare has pulled (DMW, HK EAA, HK money
lenders, BD OEP, BD MRA, CN MARA, AU AFMA, OFAC SDN, World Bank debarred, ...)
and returns a verdict:

    SANCTIONED  -- matched an OFAC/World-Bank sanctioned entity
    FLAGGED     -- matched, but the licence is cancelled / suspended / expired / delisted
    LICENSED    -- matched an entity currently in good standing on an official register
    NOT_FOUND   -- not on any collected register (verify independently; possibly unlicensed)

Matching is pure-Python (no third-party fuzzy lib -- the runtime here is fragile):
a content-token Jaccard (after stripping legal suffixes + industry-generic words
so "ABC Overseas Recruitment" and "XYZ Overseas Recruitment" do NOT collide on the
generic words) blended with a stdlib difflib sequence ratio. Everything is a pure
function over plain dicts, so it is fully tested offline; the CLI loads the staged
``reports/entity_kb/*.jsonl`` records via entity_kb.

Usage:
    python scripts/entity_screen.py --name "Sunrise Overseas Recruitment" --country PH
    python scripts/entity_screen.py --name "Acme Manpower" --threshold 0.7 --json
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import re
import sys
from pathlib import Path

try:  # optional: C-fast, word-order/transliteration-robust name matching
    from rapidfuzz import fuzz as _rf_fuzz
except ModuleNotFoundError:  # pragma: no cover - stdlib difflib is the fallback
    _rf_fuzz = None

_ROOT = Path(__file__).resolve().parents[1]

#: legal-form suffixes stripped before matching (do not distinguish two firms)
_LEGAL = {
    "ltd", "limited", "inc", "incorporated", "corp", "corporation", "co", "company",
    "pty", "llc", "plc", "pvt", "private", "sdn", "bhd", "gmbh", "ag", "sa", "srl",
    "bv", "nv", "spa", "oy", "as", "llp", "lp", "pte", "fze", "wll", "est", "group",
    "holdings", "holding", "intl",
}
#: industry-generic words removed from the CONTENT token set (kept for the seq ratio)
_GENERIC = {
    "overseas", "recruitment", "recruiting", "manpower", "agency", "agencies",
    "services", "service", "international", "trading", "enterprise", "enterprises",
    "employment", "labour", "labor", "placement", "consultancy", "consultants",
    "global", "worldwide", "human", "resources", "resource", "general", "and", "the",
    "of", "for", "foundation", "credit", "finance", "financial", "microfinance",
    "fishing", "fishery", "fisheries", "marine", "ocean", "seafood", "construction",
}

#: status fragments by risk class (checked as substrings, lower-cased)
_HIGH_RISK = ("cancel", "suspend", "revok", "delist", "expired", "blacklist",
              "locked", "withdrawn", "dismiss", "terminat", "barred", "debarred", "inactiv")
_OK = ("active", "valid", "current", "licensed", "registered", "good standing")


def _norm(name: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (name or "").lower())).strip()


def _tokens(name: str) -> tuple[set[str], set[str]]:
    """(all tokens minus legal suffixes, content tokens also minus generics)."""
    toks = [t for t in _norm(name).split() if t and t not in _LEGAL]
    content = {t for t in toks if t not in _GENERIC and not t.isdigit()}
    return set(toks), content


def _seq_ratio(a: str, b: str) -> float:
    """Sequence similarity in [0,1].

    Uses RapidFuzz ``token_sort_ratio`` when the (optional) wheel is installed --
    it sorts tokens first, so it is word-order invariant ("Sunrise Overseas" ==
    "Overseas Sunrise") and far faster (C-backed); falls back to the stdlib
    ``difflib`` ratio so the pure-stdlib path keeps working unchanged.
    """
    if _rf_fuzz is not None:
        return _rf_fuzz.token_sort_ratio(a, b) / 100.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def match_score(query: str, candidate: str) -> float:
    """Similarity in [0,1]: content-token Jaccard blended with a sequence ratio.

    The content Jaccard drives precision (it ignores legal forms + industry-generic
    words, so only the *distinctive* tokens count); the sequence ratio rescues
    spelling/transliteration variants and names that are all-generic.
    """
    q_all, q_con = _tokens(query)
    c_all, c_con = _tokens(candidate)
    if not q_all or not c_all:
        return 0.0
    seq = _seq_ratio(_norm(query), _norm(candidate))
    pool_q, pool_c = (q_con or q_all), (c_con or c_all)
    jacc = len(pool_q & pool_c) / len(pool_q | pool_c) if (pool_q | pool_c) else 0.0
    return round(0.6 * jacc + 0.4 * seq, 4)


def risk_of(entity: dict) -> str:
    """Classify one entity's standing: CRITICAL / HIGH / LICENSED / UNKNOWN."""
    et = str(entity.get("entity_type", "")).lower()
    st = str(entity.get("status", "")).lower()
    if et == "sanctioned_entity" or "watchlist" in st or "sanction" in st:
        return "CRITICAL"
    if any(h in st for h in _HIGH_RISK):
        return "HIGH"
    if any(o in st for o in _OK):
        return "LICENSED"
    return "UNKNOWN"


_VERDICT = {  # verdict -> (label, ordering rank: higher = more alarming)
    "SANCTIONED": ("SANCTIONED -- matched a sanctioned entity; do not engage", 4),
    "FLAGGED": ("FLAGGED -- matched, but the licence is cancelled/suspended/expired", 3),
    "LICENSED": ("LICENSED -- matched an entity in good standing on an official register", 2),
    "UNVERIFIED": ("UNVERIFIED -- matched a register entry with no clear status", 1),
    "NOT_FOUND": ("NOT FOUND -- not on any collected register; verify independently", 0),
}


def screen(query: str, records, *, country: str | None = None,
           threshold: float = 0.62, strong: float = 0.84, top: int = 12) -> dict:
    """Screen ``query`` against ``records`` (an iterable of entity dicts).

    Returns ``{verdict, verdict_label, found, best_score, n_hits, hits}``. The
    verdict is driven by the most-alarming *strong* match (score >= ``strong``):
    a sanctioned hit -> SANCTIONED, a cancelled/suspended hit -> FLAGGED, an
    active hit -> LICENSED. Weaker matches still appear in ``hits`` for review.
    """
    cc = country.upper() if country else None
    hits = []
    for r in records:
        if cc and str(r.get("jurisdiction", "")).upper() not in ("", cc):
            continue
        s = match_score(query, r.get("name", ""))
        if s >= threshold:
            hits.append({
                "name": r.get("name", ""), "score": s, "risk": risk_of(r),
                "status": r.get("status", ""), "jurisdiction": r.get("jurisdiction", ""),
                "entity_type": r.get("entity_type", ""), "source": r.get("source", ""),
            })
    hits.sort(key=lambda h: -h["score"])

    strong_hits = [h for h in hits if h["score"] >= strong]
    verdict = "NOT_FOUND"
    if strong_hits:
        risks = {h["risk"] for h in strong_hits}
        if "CRITICAL" in risks:
            verdict = "SANCTIONED"
        elif "HIGH" in risks:
            verdict = "FLAGGED"
        elif "LICENSED" in risks:
            verdict = "LICENSED"
        else:
            verdict = "UNVERIFIED"
    elif hits:
        verdict = "UNVERIFIED"
    return {
        "query": query, "country": cc, "verdict": verdict,
        "verdict_label": _VERDICT[verdict][0], "verdict_rank": _VERDICT[verdict][1],
        "found": bool(hits), "best_score": hits[0]["score"] if hits else 0.0,
        "n_hits": len(hits), "hits": hits[:top],
    }


# ---------------------------------------------------------------------------
# CLI: screen against the staged entity records
# ---------------------------------------------------------------------------

def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_screen", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_staged_records() -> list[dict]:
    """Load every staged entity record from reports/entity_kb/*.jsonl as dicts."""
    import dataclasses
    import glob
    ekb = _sibling("entity_kb")
    out: list[dict] = []
    for f in sorted(glob.glob(str(_ROOT / "reports" / "entity_kb" / "*.jsonl"))):
        try:
            out.extend(dataclasses.asdict(r) for r in ekb.load_entities(f))
        except Exception:  # noqa: BLE001
            continue
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="entity name to screen")
    ap.add_argument("--country", help="2-letter ISO to restrict the search")
    ap.add_argument("--threshold", type=float, default=0.62)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    records = load_staged_records()
    res = screen(args.name, records, country=args.country, threshold=args.threshold)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"\nScreening: {args.name!r}" + (f" [{args.country}]" if args.country else ""))
    print(f"  screened against {len(records)} collected entity records")
    print(f"  VERDICT: {res['verdict_label']}")
    if res["hits"]:
        print(f"  {res['n_hits']} match(es):")
        for h in res["hits"]:
            print(f"    {h['score']:.2f} [{h['risk']:8}] {h['name'][:44]:44} "
                  f"{h['jurisdiction']:3} {h['status'][:18]:18} ({h['entity_type']})")
    if not records:
        print("  (no staged records -- run: python scripts/harvest.py --all)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
