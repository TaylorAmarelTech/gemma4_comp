#!/usr/bin/env python3
"""Adverse-media / negative-news screening for migration-world entities.

Given an entity (recruitment agency, employer, broker, clinic), this screens
REAL free public sources for negative news and authoritative adverse signals,
classifies what kind of allegation each hit carries, and scores a risk level.
It is the "is this agency in the news for trafficking / wage theft / fraud, or
on a sanctions/debarment list?" layer on top of the entity knowledge base.

Sources (all real, free; keyless where possible):
  * GDELT 2.0 DOC API -- api.gdeltproject.org/api/v2/doc/doc -- a global news
    index, no API key. We co-query the entity name with adverse terms.
  * OpenSanctions -- api.opensanctions.org/search/default -- sanctions, PEPs,
    debarments, and crime entities. Free to query; commercial USE needs a
    licence (we only READ public match metadata here -- see ToS).

Design (matches the pipeline):
  * `fetch` (HTTP) and `classify` (adversity classifier) are INJECTABLE, so the
    query building, hit parsing, classification, and risk scoring are tested
    offline with synthetic GDELT/OpenSanctions payloads -- no network.
  * Deterministic baseline classifier (keyword/allegation taxonomy) always
    works; an optional Gemma classifier (model_fn) can refine it -- the model
    enhances, never gates.
  * Propose-only: writes reports/adverse_media/, never mutates knowledge. A hit
    is a LEAD for human review, not a finding -- adverse=true means "looks
    adverse", not "proven".
  * Polite: paces requests; bounded record counts; UA-identified.

Usage:
    python scripts/adverse_media.py --name "Acme Overseas Manpower" --country PH
    python scripts/adverse_media.py --screen-kb reports/entity_kb/dmw_lra.jsonl --limit 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "duecare-adverse-media/1.0 (+defensive anti-trafficking screening)"

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
OPENSANCTIONS = "https://api.opensanctions.org/search/default"

# Allegation taxonomy -> trigger phrases (lowercase substring match).
_ADVERSE_TERMS = {
    "trafficking": ("trafficking", "human traffic", "trafficked", "traffickers"),
    "forced_labor": ("forced labor", "forced labour", "slavery", "modern slavery",
                     "bonded labor", "bonded labour", "debt bondage", "indentured"),
    "wage_theft": ("wage theft", "unpaid wages", "unpaid salaries", "withheld wages",
                   "salary unpaid", "non-payment of wages", "underpaid"),
    "illegal_recruitment": ("illegal recruit", "unlicensed recruit", "recruitment scam",
                            "fake agency", "bogus recruit", "estafa", "overcharg",
                            "excessive fees", "placement fee"),
    "fraud": ("fraud", "scam", "embezzle", "misappropriat", "deceiv", "swindle"),
    "abuse": ("abuse", "assault", "mistreat", "exploit", "maltreat", "harass", "confiscat passport"),
    "enforcement": ("raid", "charged", "convicted", "sentenced", "arrested", "debarred",
                    "blacklist", "banned", "revoked licen", "lawsuit", "prosecut",
                    "deport", "rescued", "complaint filed", "cease and desist"),
}
_SERIOUS = {"trafficking", "forced_labor"}


@dataclass(frozen=True)
class AdverseHit:
    source: str            # "gdelt" | "opensanctions"
    kind: str              # "news" | "sanction"
    title: str
    url: str = ""
    date: str = ""         # YYYY-MM-DD
    domain: str = ""
    snippet: str = ""
    categories: tuple[str, ...] = ()
    adverse: bool = False
    extra: dict = field(default_factory=dict)


def classify_adverse(text: str) -> tuple[str, ...]:
    """Deterministic allegation classifier: which adverse categories the text hits."""
    t = (text or "").lower()
    cats = [cat for cat, terms in _ADVERSE_TERMS.items() if any(term in t for term in terms)]
    return tuple(cats)


def _http_get(url: str, *, timeout: float = 20.0, retries: int = 2) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    # OpenSanctions' hosted API now requires a key (Authorization: ApiKey <token>);
    # set OPENSANCTIONS_API_KEY to enable it, else the call 401s and degrades to
    # GDELT-only. A self-hosted `yente` URL needs no key.
    if "api.opensanctions.org" in url:
        key = os.environ.get("OPENSANCTIONS_API_KEY", "")
        if key:
            headers["Authorization"] = f"ApiKey {key}"
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(4_000_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 429 and attempt < retries:  # GDELT throttles; back off
                time.sleep(3.0 * (attempt + 1))
                continue
            raise
    raise last_err  # pragma: no cover


def _gdelt_search(name: str, fetch, *, max_news: int = 40, timespan: str = "24m") -> list[AdverseHit]:
    """Query GDELT for the quoted entity name; classify adversity locally.

    The query is intentionally just the quoted name (not a big adverse-OR group):
    GDELT throttles/rejects complex boolean queries, and local classification over
    the returned headlines is both cheaper and avoids the 429."""
    query = f'"{name}"'
    params = {"query": query, "mode": "artlist", "maxrecords": str(max_news),
              "timespan": timespan, "sort": "datedesc", "format": "json"}
    url = f"{GDELT_DOC}?{urllib.parse.urlencode(params)}"
    raw = fetch(url)
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:  # noqa: BLE001
        return []
    hits = []
    for art in (data.get("articles") or []):
        title = art.get("title", "")
        seen = art.get("seendate", "")  # e.g. 20260613T101500Z
        date = f"{seen[0:4]}-{seen[4:6]}-{seen[6:8]}" if len(seen) >= 8 else ""
        cats = classify_adverse(title + " " + art.get("domain", ""))
        hits.append(AdverseHit(source="gdelt", kind="news", title=title,
                               url=art.get("url", ""), date=date,
                               domain=art.get("domain", ""), categories=cats,
                               adverse=bool(cats),
                               extra={"sourcecountry": art.get("sourcecountry", "")}))
    return hits


def _name_match(a: str, b: str) -> float:
    """Crude token-overlap similarity for sanctions caption matching (0..1)."""
    ta = set(re.sub(r"[^a-z0-9 ]", " ", a.lower()).split())
    tb = set(re.sub(r"[^a-z0-9 ]", " ", b.lower()).split())
    ta -= {"inc", "corp", "ltd", "co", "llc", "the", "and"}
    tb -= {"inc", "corp", "ltd", "co", "llc", "the", "and"}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _opensanctions_search(name: str, fetch) -> list[AdverseHit]:
    """Query OpenSanctions for sanctions / PEP / debarment / crime matches."""
    url = f"{OPENSANCTIONS}?{urllib.parse.urlencode({'q': name, 'limit': '10'})}"
    raw = fetch(url)
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:  # noqa: BLE001
        return []
    hits = []
    for res in (data.get("results") or []):
        caption = res.get("caption", "")
        topics = res.get("properties", {}).get("topics", []) or res.get("topics", [])
        datasets = res.get("datasets", []) or []
        sim = _name_match(name, caption)
        if sim < 0.5:  # avoid loose false-positive matches
            continue
        # topics like sanction / debarment / crime / role.pep are adverse
        adverse = any(any(k in str(t) for k in ("sanction", "debar", "crime", "poi", "wanted"))
                      for t in topics) or bool(topics)
        cats = ("enforcement",) if adverse else ()
        hits.append(AdverseHit(source="opensanctions", kind="sanction", title=caption,
                               url=f"https://www.opensanctions.org/entities/{res.get('id','')}/",
                               categories=cats, adverse=adverse,
                               extra={"schema": res.get("schema", ""), "topics": list(topics),
                                      "datasets": datasets[:5], "name_match": round(sim, 2)}))
    return hits


def score_risk(hits: list[AdverseHit]) -> dict:
    """Roll hits into a risk verdict. Sanctions match or serious adverse news = high."""
    news = [h for h in hits if h.kind == "news"]
    adverse_news = [h for h in news if h.adverse]
    sanctions = [h for h in hits if h.kind == "sanction" and h.adverse]
    cats = sorted({c for h in hits for c in h.categories})
    serious = any(c in _SERIOUS for c in cats)
    if sanctions:
        risk = "high"
    elif serious and len(adverse_news) >= 1:
        risk = "high"
    elif len(adverse_news) >= 3:
        risk = "high"
    elif adverse_news:
        risk = "elevated"
    elif news:
        risk = "low"
    else:
        risk = "no_signal"
    return {"risk": risk, "n_news": len(news), "n_adverse": len(adverse_news),
            "n_sanctions": len(sanctions), "categories": cats}


def screen_entity(name: str, *, country: str = "", fetch=None, classify=None,
                  sources=("gdelt", "opensanctions"), max_news: int = 40,
                  timespan: str = "24m", pace: float = 0.0, screened_at: str = "") -> dict:
    """Screen one entity for adverse media + sanctions. Returns a propose-only
    report dict. `fetch` and `classify` are injectable for tests."""
    fetch = fetch or _http_get
    hits: list[AdverseHit] = []
    if "gdelt" in sources:
        try:
            hits += _gdelt_search(name, fetch, max_news=max_news, timespan=timespan)
        except Exception as exc:  # noqa: BLE001
            hits.append(AdverseHit(source="gdelt", kind="news", title=f"[gdelt error: {type(exc).__name__}]"))
        if pace:
            time.sleep(pace)
    if "opensanctions" in sources:
        try:
            hits += _opensanctions_search(name, fetch)
        except Exception as exc:  # noqa: BLE001
            hits.append(AdverseHit(source="opensanctions", kind="sanction",
                                   title=f"[opensanctions error: {type(exc).__name__}]"))
    # optional refinement: an LLM classifier may re-tag news adversity
    if classify is not None:
        hits = [classify(h) or h for h in hits]
    verdict = score_risk(hits)
    return {
        "entity": name, "country": country, "screened_at": screened_at,
        **verdict,
        "hits": [asdict(h) for h in sorted(hits, key=lambda h: (not h.adverse, h.kind))],
    }


# ---- optional Gemma classifier (refines news adversity) --------------------

def make_gemma_classifier(model_fn):
    """Wrap a model_fn(prompt)->text into a per-hit classifier that refines the
    keyword baseline (model enhances, never gates). model_fn is injectable."""
    def classify(hit: AdverseHit) -> AdverseHit:
        if hit.kind != "news" or not hit.title:
            return hit
        prompt = ("Does this news headline allege wrongdoing by a labour-recruitment / "
                  "employer entity (trafficking, forced labour, wage theft, illegal "
                  "recruitment, fraud, abuse, or enforcement action)? Headline: "
                  f"{hit.title!r}. Reply with ONE JSON object "
                  '{"adverse": true/false, "category": "<one of trafficking|forced_labor|'
                  'wage_theft|illegal_recruitment|fraud|abuse|enforcement|none>"}.')
        try:
            text = model_fn(prompt)
            obj = json.loads(text[text.find("{"):text.rfind("}") + 1])
        except Exception:  # noqa: BLE001
            return hit
        adverse = bool(obj.get("adverse"))
        cat = obj.get("category", "none")
        cats = tuple(sorted(set(hit.categories) | ({cat} if adverse and cat != "none" else set())))
        from dataclasses import replace
        return replace(hit, adverse=adverse or hit.adverse, categories=cats)
    return classify


# ---- CLI -------------------------------------------------------------------

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:48] or "entity"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", help="entity name to screen")
    ap.add_argument("--country", default="")
    ap.add_argument("--screen-kb", help="entity_kb JSONL store to screen (bounded by --limit)")
    ap.add_argument("--limit", type=int, default=5, help="max entities to screen from --screen-kb")
    ap.add_argument("--timespan", default="24m", help="GDELT lookback (e.g. 24m, 6m, 1y)")
    ap.add_argument("--sources", default="gdelt,opensanctions")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())

    if args.screen_kb:
        rows = [json.loads(ln) for ln in Path(args.screen_kb).read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")]
        rows = rows[:args.limit]
        reports = []
        for idx, r in enumerate(rows):
            name = r.get("name", "")
            if not name:
                continue
            if idx:
                time.sleep(5.0)  # GDELT throttles hard -- pace entity screens
            print(f"screening: {name}", file=sys.stderr)
            rep = screen_entity(name, country=r.get("jurisdiction", ""), sources=sources,
                                timespan=args.timespan, pace=1.0)
            reports.append(rep)
            print(f"  -> risk={rep['risk']} adverse_news={rep['n_adverse']} "
                  f"sanctions={rep['n_sanctions']} {rep['categories']}", file=sys.stderr)
        out = Path(args.out) if args.out else (_ROOT / "reports" / "adverse_media" / "kb_screen.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"_synthetic": False, "n_screened": len(reports),
                                   "reports": reports}, indent=2, ensure_ascii=False), encoding="utf-8")
        flagged = [r for r in reports if r["risk"] in ("high", "elevated")]
        print(f"\nscreened {len(reports)}; flagged {len(flagged)} -> {out}", file=sys.stderr)
        return 0

    if not args.name:
        ap.error("provide --name or --screen-kb")
    rep = screen_entity(args.name, country=args.country, sources=sources, timespan=args.timespan, pace=1.0)
    out = Path(args.out) if args.out else (_ROOT / "reports" / "adverse_media" / f"{_slug(args.name)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_synthetic": False, **rep}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"risk={rep['risk']} | adverse_news={rep['n_adverse']}/{rep['n_news']} | "
          f"sanctions={rep['n_sanctions']} | categories={rep['categories']}", file=sys.stderr)
    for h in rep["hits"][:8]:
        if h["adverse"]:
            print(f"  [{h['kind']}] {','.join(h['categories']) or '-'}: {h['title'][:90]}", file=sys.stderr)
    print(f"-> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
