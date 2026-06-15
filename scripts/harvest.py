#!/usr/bin/env python3
"""Routine entity-intelligence harvester -- runs every collector, merges, screens.

The one-off scripts (browser_scrape, ingest_kaggle_agencies, the DMW issuances
API, adverse_media) become a SYSTEM here: a single fault-tolerant orchestrator
that runs each collector, merges everything into one entity knowledge base,
optionally screens it for negative news, and writes a timestamped manifest --
so the pipeline can run on a schedule (see .github/workflows/entity-harvest.yml)
and keep the database fresh forever.

Design:
  * Each COLLECTOR is an independent callable returning
    {name, n_records, records:[entity dict], note, error}. One collector failing
    NEVER aborts the harvest -- its error is recorded and the rest continue.
  * Collectors + the merge step are injectable, so the orchestration, fault
    isolation, dedup-merge, and manifest are tested offline with fakes -- no
    browser, no network, no creds.
  * Propose-only: writes reports/entity_kb/combined.jsonl + a manifest under
    reports/harvest/; NEVER mutates the live knowledge layer. A scheduled run
    uploads these as artifacts / opens a review PR; a human promotes.
  * Built-in collectors degrade gracefully: the browser pull needs Playwright,
    Kaggle needs creds, adverse needs network -- each is skipped (recorded) when
    its prerequisite is absent, so a minimal run still works anywhere.

Usage:
    python scripts/harvest.py --collectors dmw_issuances,kaggle,dmw_agencies
    python scripts/harvest.py --all --screen        # everything + adverse screen
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_harvest", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- built-in collectors (each returns a result dict; never raises) --------

def collect_dmw_agencies() -> dict:
    """Live DMW licensed-agency pull via the headless-browser connector."""
    name = "dmw_agencies"
    try:
        bs = _sibling("browser_scrape")
        cfg = bs.PRESETS["dmw_lra"]
        result = bs.render_and_capture(cfg)
        profiles, endpoint = bs.captures_to_profiles(result, source="harvest:dmw_lra")
        recs = [{**p, "entity_type": "recruitment_agency", "jurisdiction": "PH",
                 "source": "DMW master-api (browser)", "source_tier": "official"} for p in profiles]
        return {"name": name, "n_records": len(recs), "records": recs,
                "note": f"endpoint {endpoint}", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_dmw_issuances() -> dict:
    """DMW advisory/issuance feed (keyless Strapi API) -- regulatory adverse signal."""
    name = "dmw_issuances"
    try:
        import urllib.request
        url = "https://wcms.dmw.gov.ph/api/issuances?pagination[pageSize]=100&sort=date_issued:desc"
        req = urllib.request.Request(url, headers={"User-Agent": "duecare-harvest/1.0",
                                                   "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read(4_000_000).decode("utf-8", "replace"))
        items = data.get("data", []) or []
        feed = [{"title": it.get("title", ""), "type": it.get("type", ""),
                 "category": it.get("category", ""), "document_number": it.get("document_number", ""),
                 "date_issued": str(it.get("date_issued", ""))[:10]} for it in items]
        out = _ROOT / "reports" / "harvest" / "dmw_issuances.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"_synthetic": False, "n": len(feed), "issuances": feed},
                                  indent=2, ensure_ascii=False), encoding="utf-8")
        return {"name": name, "n_records": 0, "records": [], "note": f"{len(feed)} issuances -> {out.name}", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_hk_eaa() -> dict:
    """HK EAA licensed-agency list: live result.php (current data) with a PDF
    baseline fallback. Both degrade gracefully."""
    name = "hk_eaa"
    hk = None
    try:
        hk = _sibling("hk_eaa_collector")
        res = hk._playwright_collect_live(max_pages=400)  # current data, needs a browser
        if res.get("records"):
            recs = hk.records_to_entities(res["records"])
            return {"name": name, "n_records": len(recs), "records": recs,
                    "note": f"{len(recs)} HK agencies (live result.php, {res['pages']}pg)", "error": ""}
    except Exception:  # noqa: BLE001 -- fall through to the PDF baseline
        pass
    try:
        hk = hk or _sibling("hk_eaa_collector")
        recs = hk.records_to_entities(hk.parse_pdf_list(hk.pdf_text(hk._download_pdf())))
        return {"name": name, "n_records": len(recs), "records": recs,
                "note": f"{len(recs)} HK agencies (PDF baseline)", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_hk_money_lenders() -> dict:
    """HK Companies Registry licensed money lenders (deterministic PDF, no model)."""
    name = "hk_money_lenders"
    try:
        hk = _sibling("hk_money_lenders")
        recs = hk.records_to_entities(hk.collect())
        return {"name": name, "n_records": len(recs), "records": recs,
                "note": f"{len(recs)} HK money lenders (CR PDF)", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_bd_oep() -> dict:
    """BD OEP/BMET licensed overseas recruiting agencies (deterministic HTML)."""
    name = "bd_oep"
    try:
        bd = _sibling("bd_oep_agencies")
        recs = bd.records_to_entities(bd.collect())
        return {"name": name, "n_records": len(recs), "records": recs,
                "note": f"{len(recs)} BD recruiting agencies (OEP)", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_kaggle() -> dict:
    """Ingest already-downloaded Kaggle agency + job-order CSVs (if present)."""
    name = "kaggle"
    try:
        ik = _sibling("ingest_kaggle_agencies")
        import glob
        ag = sorted(glob.glob(str(_ROOT / "reports" / "kaggle_datasets" / "*" / "*.csv")))
        agencies = [p for p in ag if "job_order" not in p.lower() and "job-order" not in p.lower()]
        jobs = [p for p in ag if "job_order" in p.lower() or "job-order" in p.lower()]
        recs: list[dict] = []
        for p in agencies:
            recs.extend(ik.agency_csv_to_records(p))
        for p in jobs:
            emps, _rel = ik.joborder_csv_to_entities(p)
            recs.extend(emps)
        note = f"{len(agencies)} agency csv + {len(jobs)} job-order csv" if ag else "no Kaggle CSVs present (download first)"
        return {"name": name, "n_records": len(recs), "records": recs, "note": note, "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


def collect_staged() -> dict:
    """Re-load any entity JSONL already staged under reports/entity_kb/ (so a
    harvest folds in prior runs' proposals)."""
    name = "staged"
    try:
        import dataclasses
        import glob
        ekb = _sibling("entity_kb")
        recs = []
        for f in sorted(glob.glob(str(_ROOT / "reports" / "entity_kb" / "*.jsonl"))):
            if Path(f).name in ("combined.jsonl", "_combined_in.jsonl"):
                continue
            recs.extend(dataclasses.asdict(r) for r in ekb.load_entities(f))
        return {"name": name, "n_records": len(recs), "records": recs,
                "note": "prior staged proposals", "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "n_records": 0, "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}


BUILTIN_COLLECTORS = {
    "dmw_agencies": collect_dmw_agencies,
    "dmw_issuances": collect_dmw_issuances,
    "hk_eaa": collect_hk_eaa,
    "hk_money_lenders": collect_hk_money_lenders,
    "bd_oep": collect_bd_oep,
    "kaggle": collect_kaggle,
    "staged": collect_staged,
}


# ---- orchestrator (tested core) -------------------------------------------

def run_harvest(collectors, *, harvested_at: str = "", screen: bool = False,
                screen_source: str = "googlenews", out_dir: Path | None = None) -> dict:
    """Run each collector, merge all entity records, optionally adverse-screen,
    write a combined store + manifest. `collectors` is a list of callables."""
    ekb = _sibling("entity_kb")
    out_dir = out_dir or (_ROOT / "reports" / "entity_kb")
    out_dir.mkdir(parents=True, exist_ok=True)

    results, all_records = [], []
    for c in collectors:
        try:
            r = c()
        except Exception as exc:  # noqa: BLE001 -- belt-and-braces; collectors already guard
            r = {"name": getattr(c, "__name__", "collector"), "n_records": 0,
                 "records": [], "note": "", "error": f"{type(exc).__name__}: {exc}"[:200]}
        results.append({k: r.get(k) for k in ("name", "n_records", "note", "error")})
        all_records.extend(r.get("records", []) or [])

    merged = ekb.merge_entities([ekb.record_from_dict(d) for d in all_records])
    combined = out_dir / "combined.jsonl"
    ekb.save_entities(combined, merged)

    from collections import Counter
    manifest = {
        "_synthetic": False, "harvested_at": harvested_at,
        "collectors": results, "n_entities": len(merged),
        "by_type": dict(Counter(r.entity_type for r in merged)),
        "by_status": dict(Counter(r.status for r in merged)),
        "combined_store": str(combined),
    }

    screened = None
    if screen and merged:
        try:
            am = _sibling("adverse_media")
            rows = [{"name": r.name, "status": r.status, "jurisdiction": r.jurisdiction} for r in merged]
            screened = am.corpus_screen(rows, am._http_get, sources=(screen_source,))
            manifest["adverse_screen"] = {"n_articles": screened["n_articles"],
                                          "n_candidates": screened["n_matches"]}
        except Exception as exc:  # noqa: BLE001
            manifest["adverse_screen"] = {"error": f"{type(exc).__name__}: {exc}"[:160]}

    man_dir = _ROOT / "reports" / "harvest"
    man_dir.mkdir(parents=True, exist_ok=True)
    stamp = (harvested_at or "manifest").replace(":", "").replace(" ", "_")[:32]
    man_path = man_dir / f"manifest_{stamp}.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest["manifest_path"] = str(man_path)
    if screened is not None:
        (man_dir / "adverse_candidates.json").write_text(
            json.dumps({"_synthetic": False, **screened}, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collectors", default="dmw_issuances,kaggle,staged",
                    help=f"comma list of: {','.join(BUILTIN_COLLECTORS)}")
    ap.add_argument("--all", action="store_true", help="run every built-in collector")
    ap.add_argument("--screen", action="store_true", help="adverse-media screen the merged entities")
    ap.add_argument("--screen-source", default="googlenews")
    ap.add_argument("--at", default="", help="harvested_at stamp (YYYY-MM-DDTHH:MM, for reproducible names)")
    args = ap.parse_args(argv)

    names = list(BUILTIN_COLLECTORS) if args.all else [
        s.strip() for s in args.collectors.split(",") if s.strip()]
    collectors = [BUILTIN_COLLECTORS[n] for n in names if n in BUILTIN_COLLECTORS]
    unknown = [n for n in names if n not in BUILTIN_COLLECTORS]
    if unknown:
        print(f"unknown collectors ignored: {unknown}", file=sys.stderr)

    print(f"harvesting from {len(collectors)} collector(s): {[c.__name__ for c in collectors]}",
          file=sys.stderr)
    man = run_harvest(collectors, harvested_at=args.at, screen=args.screen,
                      screen_source=args.screen_source)
    for c in man["collectors"]:
        flag = f"ERROR {c['error']}" if c["error"] else (c["note"] or f"{c['n_records']} records")
        print(f"  [{c['name']:14}] {c['n_records']:>6} records  {flag}", file=sys.stderr)
    print(f"\nmerged -> {man['n_entities']} entities {man['by_type']}", file=sys.stderr)
    if "adverse_screen" in man:
        print(f"adverse screen: {man['adverse_screen']}", file=sys.stderr)
    print(f"manifest -> {man['manifest_path']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
